"""HTTP klient pro Upgates e-shop API v2 (s retry/backoff a respektem rate-limitu).

Port `upgates-client.ts` na SDK. Autentizace je HTTP Basic (`api_login` jako
login, `api_key` jako heslo) — 1:1 s originálem (axios `auth: {username, password}`).
Jediná skutečná změna oproti TS je vstup do konstruktoru: klient se staví
přímo z `(api_url, api_login, api_key)` z `openmcp_sdk` request kontextu, ne
z `UpgatesConfig` čtené z env proměnných (viz `connector.server._client`).

TS klient neměl retry (spoléhal se na axios interceptor jen na mapování chyb);
retry/backoff jsme přidali podle vzoru raynet-mcp — čtení jsou idempotentní,
takže opakování na 429/5xx je bezpečné a robustnější vůči rate-limitu Upgates.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Přechodné stavy, u nichž má smysl opakovat pokus.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4
_BACKOFF_BASE = 0.5  # s — exponenciálně: 0.5, 1, 2 …
_BACKOFF_CAP = 8.0


class UpgatesError(RuntimeError):
    """Chyba komunikace s Upgates API (včetně HTTP a rate-limit stavů).

    `status_code` nese HTTP stav, pokud ho Upgates vrátil (401/403/429/4xx/5xx) —
    volající (`connector.server.test_connection`) tak může chybu klasifikovat
    strukturovaně místo parsování textu zprávy. `None` = chyba bez HTTP stavu
    (síťová/timeout, neplatná URL v konstruktoru, nevalidní JSON tělo).
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class UpgatesClient:
    def __init__(self, api_url: str, api_login: str, api_key: str, *, timeout: float = 30.0) -> None:
        base_url = (api_url or "").strip()
        if not base_url.lower().startswith(("http://", "https://")):
            raise UpgatesError(
                f"Neplatná URL API e-shopu {api_url!r} — očekává se absolutní https:// adresa."
            )
        # Upgates API používá HTTP Basic Authentication (login:apiKey).
        self._client = httpx.Client(
            base_url=base_url,
            auth=(api_login, api_key),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
        )
        # Poslední hodnoty rate-limit hlaviček (pro diagnostiku).
        self.rate_limit: dict[str, str] = {}

    def close(self) -> None:
        self._client.close()

    def _sleep_for(self, attempt: int, resp: httpx.Response | None) -> float:
        """Doba čekání před dalším pokusem: dle Retry-After, jinak backoff s jitterem."""
        if resp is not None:
            ra = resp.headers.get("Retry-After")
            if ra and ra.isdigit():
                return min(float(ra), _BACKOFF_CAP)
        delay = min(_BACKOFF_BASE * (2 ** (attempt - 1)), _BACKOFF_CAP)
        return delay + random.uniform(0, delay * 0.25)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET požadavek s retry na přechodné chyby. Vrací JSON tělo (dict/list)."""
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            resp: httpx.Response | None = None
            try:
                resp = self._client.get(path, params=clean)
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS:
                    delay = self._sleep_for(attempt, None)
                    logger.warning(
                        "Síťová chyba při GET %s (pokus %d/%d): %s — opakuji za %.1fs",
                        path, attempt, _MAX_ATTEMPTS, exc, delay,
                    )
                    time.sleep(delay)
                    continue
                raise UpgatesError(
                    f"Síťová chyba při GET {path} (po {attempt} pokusech): {exc}"
                ) from exc

            for header in ("Retry-After", "X-Ratelimit-Remaining", "X-Ratelimit-Reset"):
                if header in resp.headers:
                    self.rate_limit[header] = resp.headers[header]

            if resp.status_code in _RETRYABLE_STATUS and attempt < _MAX_ATTEMPTS:
                delay = self._sleep_for(attempt, resp)
                logger.warning(
                    "GET %s → HTTP %d (pokus %d/%d) — opakuji za %.1fs",
                    path, resp.status_code, attempt, _MAX_ATTEMPTS, delay,
                )
                time.sleep(delay)
                continue

            if resp.status_code == 429:
                raise UpgatesError(
                    "Překročen rate limit Upgates API (429) i po opakování.",
                    status_code=429,
                )
            if resp.status_code in (401, 403):
                raise UpgatesError(
                    "Upgates odmítl přihlášení — neplatný API login nebo klíč "
                    "uložený v trezoru klíčů OpenMCP.",
                    status_code=resp.status_code,
                )
            if resp.status_code >= 400:
                body = resp.text[:500]
                raise UpgatesError(
                    f"HTTP {resp.status_code} při GET {path}: {body}",
                    status_code=resp.status_code,
                )

            try:
                return resp.json()
            except ValueError as exc:
                raise UpgatesError(
                    f"Neplatná JSON odpověď z {path}: {resp.text[:200]}",
                    status_code=resp.status_code,
                ) from exc

        # Sem se dostaneme jen když vyčerpáme pokusy na retryable stavu.
        raise UpgatesError(
            f"GET {path} selhal po {_MAX_ATTEMPTS} pokusech "
            f"(poslední chyba: {last_exc or 'přechodný HTTP stav'})."
        )
