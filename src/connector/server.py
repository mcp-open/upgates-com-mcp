"""FastMCP server nad Upgates e-shop API v2 (GET) s GDPR pseudonymizací — SDK port.

Port produktového `upgates-com-mcp` (TypeScript: `src/tools/definitions.ts` +
`src/handlers/tools.ts`) na `openmcp_sdk`. Přenáší se **jen čtecí nástroje**
(list_*/get_*) — zapisovací (create_/update_/delete_) hostovaná varianta
záměrně nevystavuje (read-only, stejně jako raynet). Business logika (mapování
nástroj→endpoint, optimalizace, anonymizace) je věrná originálu; mění se jen
zdroj identity/credentials:

- **Identita** (`sub`) a **credentials** (`api_url`/`api_login`/`api_key`) už
  nepřicházejí z env proměnných (`UPGATES_API_*`, standalone režim), ale z
  `openmcp_sdk.current_context()` — transport (stdio i HTTP) je naplní před
  každým voláním nástroje. Secret klíč je v `ctx.secrets["api_key"]`, nesekretní
  URL a login v `ctx.config`.
- Každý nástroj zůstává plain funkcí (ne `@mcp.tool` dekorátor přímo), aby ho
  unit testy mohly zavolat přímo; registrace níže (`mcp.tool(fn, annotations=…)`)
  ho přihlásí jako MCP nástroj s `readOnlyHint=True`.
- GDPR pseudonymizace (`openmcp_sdk.pii.Pseudonymizer` +
  `connector.pii_fields.POLICY`) je povinná bezpečnostní hranice. Aplikuje se
  na nástroje nesoucí zákaznická data (objednávky, faktury, zákazníci, košíky,
  provozovatel) a operátorská konfigurace ji nemůže vypnout.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import date, timedelta
from typing import Annotated, Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from openmcp_sdk import ConnectorError, ErrorCode, current_context
from openmcp_sdk.http import UpstreamClient
from openmcp_sdk.pii import Pseudonymizer, derive_key

from connector.optimizers import optimize_list_response
from connector.pii_fields import POLICY
from connector.validators import validate_date_range, validate_page

logger = logging.getLogger(__name__)

mcp: FastMCP = FastMCP(
    "upgates",
    instructions=(
        "Čtecí přístup k Upgates e-shop API (v2). Osobní data zákazníků "
        "(e-maily, telefony, jména, adresy, IČO/DIČ, bankovní spojení) jsou "
        "v odpovědích pseudonymizována tokeny typu <EMAIL_3f9c1a2b4d5e>, "
        "<PHONE_…>, <NAME_…> — jsou stabilní (stejná hodnota = stejný token), "
        "ale reálné hodnoty nejsou dostupné a token nelze rozklíčovat zpět. "
        "K vyhledání záznamu použij číslo objednávky/faktury nebo kód, ne přímo "
        "e-mail/telefon. Katalogová data (produkty, kategorie, ceny) nejsou "
        "pseudonymizována. Odpovědi jsou stránkované a zkrácené na prvních 15 "
        "položek — víc získáš parametrem page."
    ),
)

# --- Sdílené popisy parametrů (Annotated[…, Field]) — LLM je vidí ve schématu. --
_D_PAGE = Field(description="Číslo stránky (od 1)", ge=1)
_D_LANGUAGE = Field(description="Filtrovat podle jazyka (ISO 639-1)")
_D_DATE_FROM = Field(description="Filtrovat od tohoto data (YYYY-MM-DD)")
_D_DATE_TO = Field(description="Filtrovat do tohoto data (YYYY-MM-DD)")


# =============================================================================
# Klient + společná cesta požadavku
# =============================================================================
_DNS_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_UPGATES_API_HOST = re.compile(
    rf"{_DNS_LABEL}\.admin\.{_DNS_LABEL}\.upgates\.com",
    re.ASCII,
)


def _validated_api_url(raw: object) -> str:
    """Bind Basic credentials to the exact Upgates HTTPS origin family.

    Kubernetes NetworkPolicy cannot enforce FQDNs and therefore permits public
    port 443. Without this application check a customer-controlled ``api_url``
    could exfiltrate the API login/key to an arbitrary host.
    """

    if not isinstance(raw, str) or raw != raw.strip() or any(
        ord(char) < 32 or ord(char) == 127 for char in raw
    ):
        raise ConnectorError(ErrorCode.INVALID_INPUT, "Neplatná URL Upgates API.")
    parsed = urllib.parse.urlsplit(raw)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConnectorError(ErrorCode.INVALID_INPUT, "Neplatná URL Upgates API.") from exc
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or _UPGATES_API_HOST.fullmatch(hostname) is None
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/api/v2"
    ):
        raise ConnectorError(
            ErrorCode.INVALID_INPUT,
            "URL musí být HTTPS adresa e-shopu "
            "<eshop>.admin.<server>.upgates.com s cestou /api/v2.",
        )
    return f"https://{hostname}{f':{port}' if port is not None else ''}/api/v2"


def _client() -> UpstreamClient:
    """Upgates klient z aktuálního request kontextu (SDK identita + creds).

    Retry (429/5xx), timeout a mapování HTTP stavů na `ConnectorError` dělá
    sdílený `openmcp_sdk.http.UpstreamClient` — Upgates API nemá vlastní
    zvláštnost oproti výchozí politice (HTTP Basic je `auth=(login, api_key)`).
    """
    ctx = current_context()
    return UpstreamClient(
        base_url=_validated_api_url(ctx.config["api_url"]),
        auth=(ctx.config["api_login"], ctx.secrets["api_key"]),
    )


def _pseudonymizer() -> Pseudonymizer:
    return Pseudonymizer(derive_key(current_context().principal.sub), POLICY)


def _path_segment(value: int | str, label: str) -> str:
    """Znormalizuj LLM-dodané ID na bezpečný segment cesty (percent-encoding).

    Zneškodní `/`, `?`, `#`, `..` — hodnota nikdy nemůže změnit cílový endpoint
    (path injection).
    """
    text = str(value).strip()
    if not text:
        raise ConnectorError(ErrorCode.INVALID_INPUT, f"{label} nesmí být prázdné.")
    return urllib.parse.quote(text, safe="")


def _unwrap(body: Any) -> Any:
    """Rozbal Upgates obálku {success, data} → data (jinak vrať tělo beze změny).

    TS `formatResponse` zabalí odpovědi bez `success` do {success, data} a handler
    pak čte `.data`; tady sjednocujeme obě varianty na samotný payload.
    """
    if isinstance(body, dict) and "success" in body and "data" in body:
        return body["data"]
    return body


def _get(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    optimize: str | None = None,
    anonymize: bool = False,
) -> Any:
    """GET jednoho endpointu + (volitelně) optimalizace a pseudonymizace.

    Pořadí odpovídá TS handlerům: nejdřív optimalizace (výběr polí + limit
    položek), pak — je-li zapnuto — GDPR pseudonymizace zákaznických dat.
    """
    client = _client()
    try:
        body = client.get_json(path, params)
    finally:
        client.close()

    data = _unwrap(body)
    if optimize is not None:
        data = optimize_list_response(data, optimize)
    if anonymize:
        data = _pseudonymizer().sanitize(data)
    return data


def _query(**kwargs: Any) -> dict[str, Any]:
    """Sestav query z nenulových parametrů (ekvivalent TS buildQueryParams)."""
    return {k: v for k, v in kwargs.items() if v is not None}


# =============================================================================
# Objednávky (Orders)
# =============================================================================
def list_orders(
    order_number: Annotated[str | None, Field(description="Konkrétní číslo objednávky")] = None,
    creation_time_from: Annotated[str | None, _D_DATE_FROM] = None,
    creation_time_to: Annotated[str | None, _D_DATE_TO] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filtrovat objednávky aktualizované od tohoto data (YYYY-MM-DD)")] = None,
    paid_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu zaplacení")] = None,
    status: Annotated[str | None, Field(description="Filtrovat podle názvu stavu objednávky")] = None,
    status_id: Annotated[int | None, Field(description="Filtrovat podle ID stavu objednávky")] = None,
    email: Annotated[str | None, Field(description="Filtrovat podle e-mailu zákazníka")] = None,
    phone: Annotated[str | None, Field(description="Filtrovat podle telefonu zákazníka (formát MSISDN)")] = None,
    external_order_number: Annotated[str | None, Field(description="Filtrovat podle externího čísla objednávky")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    page: Annotated[int, _D_PAGE] = 1,
    order_by: Annotated[str, Field(description="Řadit podle pole: creation_time | last_update_time")] = "creation_time",
    order_dir: Annotated[str, Field(description="Směr řazení: asc | desc")] = "desc",
) -> Any:
    """Seznam objednávek s filtrováním a stránkováním (max 15 položek na stránku).

    Data zákazníka jsou před opuštěním konektoru pseudonymizována.
    """
    validate_page(page)
    validate_date_range(creation_time_from, creation_time_to)
    endpoint = f"/orders/{_path_segment(order_number, 'order_number')}" if order_number else "/orders"
    params = _query(
        order_number=order_number, creation_time_from=creation_time_from,
        creation_time_to=creation_time_to, last_update_time_from=last_update_time_from,
        paid_yn=paid_yn, status=status, status_id=status_id, email=email, phone=phone,
        external_order_number=external_order_number, language=language,
        page=page, order_by=order_by, order_dir=order_dir,
    )
    return _get(endpoint, params, optimize="orders", anonymize=True)


def get_order_history(
    order_number: Annotated[str, Field(description="Číslo objednávky")],
) -> Any:
    """Historie konkrétní objednávky. Data zákazníka jsou pseudonymizována."""
    path = f"/orders/{_path_segment(order_number, 'order_number')}/history"
    return _get(path, anonymize=True)


# =============================================================================
# Stavy objednávek (Order statuses)
# =============================================================================
def list_order_statuses(
    id: Annotated[int | None, Field(description="Konkrétní ID stavu")] = None,
    type: Annotated[str | None, Field(description="Typ stavu: Received | Canceled | Sent | PaymentSuccessful | PaymentFailed | Custom")] = None,
) -> Any:
    """Seznam všech stavů objednávek."""
    endpoint = f"/order-statuses/{_path_segment(id, 'id')}" if id else "/order-statuses"
    return _get(endpoint, _query(id=id, type=type))


# =============================================================================
# Faktury (Invoices)
# =============================================================================
def list_invoices(
    invoice_number: Annotated[str | None, Field(description="Konkrétní číslo faktury")] = None,
    creation_time_from: Annotated[str | None, _D_DATE_FROM] = None,
    creation_time_to: Annotated[str | None, _D_DATE_TO] = None,
    paid_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu zaplacení")] = None,
    type: Annotated[str | None, Field(description="Typ faktury: invoice | creditNote | receipt")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam faktur s filtrováním a stránkováním. Data zákazníka jsou pseudonymizována."""
    validate_page(page)
    validate_date_range(creation_time_from, creation_time_to)
    endpoint = f"/invoices/{_path_segment(invoice_number, 'invoice_number')}" if invoice_number else "/invoices"
    params = _query(
        invoice_number=invoice_number, creation_time_from=creation_time_from,
        creation_time_to=creation_time_to, paid_yn=paid_yn, type=type, page=page,
    )
    return _get(endpoint, params, optimize="invoices", anonymize=True)


# =============================================================================
# Produkty (Products)
# =============================================================================
def list_products(
    code: Annotated[str | None, Field(description="Kód produktu")] = None,
    product_id: Annotated[int | None, Field(description="ID produktu")] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filtrovat produkty aktualizované od tohoto data (YYYY-MM-DD)")] = None,
    active_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu aktivní (výchozí: true)")] = None,
    archived_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu archivováno")] = None,
    can_add_to_basket_yn: Annotated[bool | None, Field(description="Filtrovat podle možnosti vložit do košíku")] = None,
    in_stock_yn: Annotated[bool | None, Field(description="Filtrovat podle skladové dostupnosti")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    pricelist: Annotated[str | None, Field(description="Filtrovat podle názvu ceníku")] = None,
    variants_yn: Annotated[bool | None, Field(description="Zahrnout varianty (výchozí: false)")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam produktů s filtrováním a stránkováním (max 15 položek na stránku)."""
    validate_page(page)
    endpoint = f"/products/{_path_segment(code, 'code')}" if code else "/products"
    params = _query(
        code=code, product_id=product_id, last_update_time_from=last_update_time_from,
        active_yn=active_yn if active_yn is not None else True,
        archived_yn=archived_yn, can_add_to_basket_yn=can_add_to_basket_yn,
        in_stock_yn=in_stock_yn, language=language, pricelist=pricelist,
        variants_yn=variants_yn if variants_yn is not None else False,
        page=page,
    )
    return _get(endpoint, params, optimize="products")


def list_products_simple(
    code: Annotated[str | None, Field(description="Kód produktu")] = None,
    product_id: Annotated[int | None, Field(description="ID produktu")] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filtrovat produkty aktualizované od tohoto data (YYYY-MM-DD)")] = None,
    active_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu aktivní")] = None,
    in_stock_yn: Annotated[bool | None, Field(description="Filtrovat podle skladové dostupnosti")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam produktů ve zjednodušeném formátu (max 50 položek na stránku)."""
    validate_page(page)
    endpoint = f"/products/{_path_segment(code, 'code')}/simple" if code else "/products/simple"
    params = _query(
        code=code, product_id=product_id, last_update_time_from=last_update_time_from,
        active_yn=active_yn, in_stock_yn=in_stock_yn, page=page,
    )
    return _get(endpoint, params)


# =============================================================================
# Zákazníci (Customers)
# =============================================================================
def list_customers(
    customer_id: Annotated[int | None, Field(description="Konkrétní ID zákazníka")] = None,
    code: Annotated[str | None, Field(description="Kód zákazníka")] = None,
    email: Annotated[str | None, Field(description="E-mail zákazníka")] = None,
    phone: Annotated[str | None, Field(description="Telefon zákazníka")] = None,
    active_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu aktivní (výchozí: true)")] = None,
    blocked_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu blokován (výchozí: false)")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    pricelist: Annotated[str | None, Field(description="Filtrovat podle ceníku")] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filtrovat zákazníky aktualizované od tohoto data (YYYY-MM-DD)")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam zákazníků s filtrováním a stránkováním. Osobní data jsou pseudonymizována."""
    validate_page(page)
    params = _query(
        customer_id=customer_id, code=code, email=email, phone=phone,
        active_yn=active_yn if active_yn is not None else True,
        blocked_yn=blocked_yn if blocked_yn is not None else False,
        language=language, pricelist=pricelist,
        last_update_time_from=last_update_time_from, page=page,
    )
    return _get("/customers", params, optimize="customers", anonymize=True)


# =============================================================================
# Kategorie (Categories)
# =============================================================================
def list_categories(
    code: Annotated[str | None, Field(description="Kód kategorie")] = None,
    category_id: Annotated[int | None, Field(description="ID kategorie")] = None,
    parent_id: Annotated[int | None, Field(description="Filtrovat podle ID nadřazené kategorie")] = None,
    active_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu aktivní (výchozí: true)")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filtrovat kategorie aktualizované od tohoto data (YYYY-MM-DD)")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam kategorií s filtrováním a stránkováním (max 15 položek na stránku)."""
    validate_page(page)
    params = _query(
        code=code, category_id=category_id, parent_id=parent_id,
        active_yn=active_yn if active_yn is not None else True,
        language=language, last_update_time_from=last_update_time_from, page=page,
    )
    return _get("/categories", params, optimize="categories")


# =============================================================================
# Long-tail číselníky a katalogové zdroje
# =============================================================================
def list_labels(
    id: Annotated[int | None, Field(description="Konkrétní ID štítku")] = None,
    type: Annotated[str | None, Field(description="Typ štítku: action | new | sale | custom")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam štítků produktů (max 50 položek na stránku)."""
    validate_page(page)
    endpoint = f"/labels/{_path_segment(id, 'id')}" if id else "/labels"
    return _get(endpoint, _query(id=id, type=type, page=page))


def list_availabilities(
    id: Annotated[int | None, Field(description="Konkrétní ID dostupnosti")] = None,
    type: Annotated[str | None, Field(description="Typ dostupnosti: OnRequest | NotAvailable | InStock | Custom")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam dostupností produktů (max 50 položek na stránku)."""
    validate_page(page)
    endpoint = f"/availabilities/{_path_segment(id, 'id')}" if id else "/availabilities"
    return _get(endpoint, _query(id=id, type=type, page=page))


def list_manufacturers(
    id: Annotated[int | None, Field(description="Konkrétní ID výrobce")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam výrobců (max 50 položek na stránku)."""
    validate_page(page)
    endpoint = f"/manufacturers/{_path_segment(id, 'id')}" if id else "/manufacturers"
    return _get(endpoint, _query(id=id, page=page))


def list_parameters(
    id: Annotated[int | None, Field(description="Konkrétní ID parametru")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam parametrů produktů."""
    validate_page(page)
    endpoint = f"/parameters/{_path_segment(id, 'id')}" if id else "/parameters"
    return _get(endpoint, _query(id=id, page=page))


# =============================================================================
# Košíky (Carts)
# =============================================================================
def list_carts(
    id: Annotated[int | None, Field(description="Konkrétní ID košíku")] = None,
    creation_time_from: Annotated[str | None, Field(description="Filtrovat košíky vytvořené od tohoto data (YYYY-MM-DD); výchozí: posledních 7 dní")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    filled_delivery_info_yn: Annotated[bool | None, Field(description="Filtrovat košíky s vyplněnými doručovacími údaji")] = None,
    customer_logged_in_yn: Annotated[bool | None, Field(description="Filtrovat košíky s přihlášenými zákazníky")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam nákupních košíků (max 15 položek na stránku). Data zákazníka jsou pseudonymizována.

    Bez filtru data nebo id se výchozí použijí košíky za posledních 7 dní.
    """
    validate_page(page)
    endpoint = f"/carts/{_path_segment(id, 'id')}" if id else "/carts"
    # Default: košíky za posledních 7 dní, pokud není filtr ani konkrétní id.
    if not creation_time_from and id is None:
        creation_time_from = (date.today() - timedelta(days=7)).isoformat()
    params = _query(
        id=id, creation_time_from=creation_time_from, language=language,
        filled_delivery_info_yn=filled_delivery_info_yn,
        customer_logged_in_yn=customer_logged_in_yn, page=page,
    )
    return _get(endpoint, params, optimize="carts", anonymize=True)


# =============================================================================
# Slevové kupóny (Vouchers)
# =============================================================================
def list_vouchers(
    voucher_code: Annotated[str | None, Field(description="Konkrétní kód kupónu")] = None,
    active_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu aktivní (výchozí: true)")] = None,
    global_yn: Annotated[bool | None, Field(description="Filtrovat podle stavu opakovaně použitelný")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam slevových kupónů (max 100 položek na stránku)."""
    validate_page(page)
    endpoint = f"/vouchers/{_path_segment(voucher_code, 'voucher_code')}" if voucher_code else "/vouchers"
    params = _query(
        voucher_code=voucher_code,
        active_yn=active_yn if active_yn is not None else True,
        global_yn=global_yn, page=page,
    )
    return _get(endpoint, params)


# =============================================================================
# Doprava a platby (Shipments, Payments)
# =============================================================================
def list_shipments(
    id: Annotated[int | None, Field(description="Konkrétní ID dopravy")] = None,
    code: Annotated[str | None, Field(description="Kód dopravy")] = None,
    type: Annotated[str | None, Field(description="Typ dopravy: custom | ceskaPosta | slovenskaPosta | zasilkovna | dpd | ppl | gls")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam způsobů dopravy (vícejazyčné popisy jsou zkráceny)."""
    validate_page(page)
    endpoint = f"/shipments/{_path_segment(id, 'id')}" if id else "/shipments"
    return _get(endpoint, _query(id=id, code=code, type=type, page=page), optimize="shipments")


def list_payments(
    id: Annotated[int | None, Field(description="Konkrétní ID platby")] = None,
    code: Annotated[str | None, Field(description="Kód platby")] = None,
    type: Annotated[str | None, Field(description="Typ platby: cash | cashOnDelivery | command | paypal | gopay | stripe | custom")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """Seznam platebních metod (vícejazyčné popisy jsou zkráceny)."""
    validate_page(page)
    endpoint = f"/payments/{_path_segment(id, 'id')}" if id else "/payments"
    return _get(endpoint, _query(id=id, code=code, type=type, page=page), optimize="payments")


# =============================================================================
# Webhooky (Webhooks)
# =============================================================================
def list_webhooks(
    id: Annotated[int | None, Field(description="Konkrétní ID webhooku")] = None,
) -> Any:
    """Seznam nakonfigurovaných webhooků."""
    endpoint = f"/webhooks/{_path_segment(id, 'id')}" if id else "/webhooks"
    return _get(endpoint)


def list_webhook_events() -> Any:
    """Seznam dostupných událostí webhooku."""
    return _get("/webhooks/events")


# =============================================================================
# Konfigurace e-shopu (Config, Languages, Owner, Status, Pricelists)
# =============================================================================
def get_languages() -> Any:
    """Získej konfiguraci jazyků e-shopu."""
    return _get("/languages")


def get_shop_config() -> Any:
    """Získej konfiguraci a nastavení e-shopu."""
    return _get("/config")


def get_shop_owner() -> Any:
    """Získej fakturační údaje provozovatele e-shopu. Firemní data jsou pseudonymizována."""
    return _get("/owner", anonymize=True)


def get_api_status() -> Any:
    """Získej stav API a seznam povolených endpointů pro aktuálního uživatele."""
    return _get("/status")


def list_pricelists() -> Any:
    """Seznam ceníků."""
    return _get("/pricelists")


# =============================================================================
# Test spojení
# =============================================================================
def test_connection() -> str:
    """Ad-hoc test spojení s Upgates (SDK interní `POST /test`).

    `_client()` samotný smí spadnout (`ConnectorError` z neplatné URL, `KeyError`
    z chybějícího pole v kontextu) dřív, než stihne cokoliv zavolat — bez
    vlastního try/except by taková chyba unikla jako 500. Klasifikace chyby
    z `client.get_json()` je strukturovaná přes `ConnectorError.status`: 401/403
    (neplatný login/klíč) → INVALID_INPUT (uživatel to má šanci opravit),
    cokoliv jiného (timeout, 5xx, rate limit) → UPSTREAM_UNAVAILABLE. Zprávě se
    záměrně nepředává syrový `str(exc)` (může nést vendor tělo).
    """
    try:
        client = _client()
    except (ConnectorError, KeyError) as exc:
        raise ConnectorError(ErrorCode.INVALID_INPUT, "Neplatné údaje připojení") from exc

    try:
        client.get_json("/status")
    except ConnectorError as exc:
        if exc.status in (401, 403):
            raise ConnectorError(
                ErrorCode.INVALID_INPUT, "Neplatný API login nebo klíč"
            ) from exc
        raise ConnectorError(
            ErrorCode.UPSTREAM_UNAVAILABLE,
            "Nepodařilo se spojit s Upgates — zkus to prosím znovu.",
        ) from exc
    finally:
        client.close()

    return f"Připojeno k e-shopu {current_context().config['api_url']}"


# =============================================================================
# Registrace nástrojů (všechny read-only → readOnlyHint=True)
# =============================================================================
_READ_ONLY = ToolAnnotations(readOnlyHint=True)

for _tool in (
    list_orders,
    get_order_history,
    list_order_statuses,
    list_invoices,
    list_products,
    list_products_simple,
    list_customers,
    list_categories,
    list_labels,
    list_availabilities,
    list_manufacturers,
    list_parameters,
    list_carts,
    list_vouchers,
    list_shipments,
    list_payments,
    list_webhooks,
    list_webhook_events,
    get_languages,
    get_shop_config,
    get_shop_owner,
    get_api_status,
    list_pricelists,
):
    mcp.tool(_tool, annotations=_READ_ONLY)
