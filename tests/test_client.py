"""Testy HTTP klienta: Basic Auth, retry/backoff a mapování chyb (bez reálné sítě)."""

from __future__ import annotations

import base64

import httpx
import pytest

from connector import client as client_mod
from connector.client import UpgatesClient, UpgatesError


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(client_mod.time, "sleep", lambda *_: None)


class _StubHTTP:
    """Náhrada httpx.Client — vrací předpřipravené odpovědi / výjimky v pořadí."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0
        self.seen: list[dict] = []

    def get(self, path, params=None):
        self.seen.append({"path": path, "params": params})
        result = self._results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


def _make(results):
    c = UpgatesClient(api_url="https://x.admin.upgates.com/api/v2", api_login="u", api_key="k")
    stub = _StubHTTP(results)
    c._client = stub  # type: ignore[assignment]
    return c, stub


def test_invalid_url_raises():
    with pytest.raises(UpgatesError, match="URL"):
        UpgatesClient(api_url="not-a-url", api_login="u", api_key="k")


def test_uses_basic_auth_login_and_api_key():
    """Kontraktní test: reálná konstrukce musí použít HTTP Basic (login, api_key),
    ne Bearer — přesně jako axios `auth: {username, password}` v originále."""
    c = UpgatesClient(
        api_url="https://acme.admin.upgates.com/api/v2",
        api_login="api_user",
        api_key="secret-key",
    )
    try:
        assert isinstance(c._client.auth, httpx.BasicAuth)
        request = c._client.build_request("GET", "/x")
        prepared = next(c._client.auth.auth_flow(request))
        auth_header = prepared.headers["Authorization"]
        assert auth_header.startswith("Basic ")
        assert "Bearer" not in auth_header
        decoded = base64.b64decode(auth_header.removeprefix("Basic ")).decode()
        assert decoded == "api_user:secret-key"
    finally:
        c.close()


def test_success_returns_json():
    c, stub = _make([httpx.Response(200, json={"ok": 1})])
    assert c.get("/x") == {"ok": 1}
    assert stub.calls == 1


def test_retries_on_429_then_succeeds():
    c, stub = _make([
        httpx.Response(429, headers={"Retry-After": "0"}),
        httpx.Response(200, json={"ok": True}),
    ])
    assert c.get("/x") == {"ok": True}
    assert stub.calls == 2


def test_retries_on_network_error_then_succeeds():
    c, stub = _make([httpx.RequestError("boom"), httpx.Response(200, json=[1, 2, 3])])
    assert c.get("/x") == [1, 2, 3]
    assert stub.calls == 2


def test_persistent_5xx_raises_after_max_attempts():
    c, stub = _make([httpx.Response(503) for _ in range(4)])
    with pytest.raises(UpgatesError):
        c.get("/x")
    assert stub.calls == 4


def test_401_raises_without_retry():
    c, stub = _make([httpx.Response(401)])
    with pytest.raises(UpgatesError) as exc:
        c.get("/x")
    assert exc.value.status_code == 401
    assert stub.calls == 1


def test_403_raises_without_retry():
    c, stub = _make([httpx.Response(403)])
    with pytest.raises(UpgatesError) as exc:
        c.get("/x")
    assert exc.value.status_code == 403
    assert stub.calls == 1


def test_4xx_raises_with_body():
    c, stub = _make([httpx.Response(404, text="not found")])
    with pytest.raises(UpgatesError, match="404"):
        c.get("/x")
    assert stub.calls == 1


def test_invalid_json_raises():
    c, _ = _make([httpx.Response(200, text="<html>nope")])
    with pytest.raises(UpgatesError, match="JSON"):
        c.get("/x")


def test_drops_none_params():
    c, stub = _make([httpx.Response(200, json={})])
    c.get("/x", {"a": 1, "b": None})
    assert stub.seen[0]["params"] == {"a": 1}
