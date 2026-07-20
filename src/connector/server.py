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
- GDPR pseudonymizace (`connector.anonymize.Pseudonymizer`) je gated
  operátorským přepínačem `current_context().config.get("anonymize_data", True)`
  (default zapnuto). Aplikuje se — stejně jako v TS — na nástroje nesoucí
  zákaznická data (objednávky, faktury, zákazníci, košíky, provozovatel).
"""

from __future__ import annotations

import logging
import os as _os
import urllib.parse
from datetime import date, timedelta
from typing import Annotated, Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from openmcp_sdk import ConnectorError, ErrorCode, current_context
from openmcp_sdk.logging import setup as _log_setup

from connector.anonymize import Pseudonymizer, derive_key
from connector.client import UpgatesClient, UpgatesError
from connector.optimizers import optimize_list_response
from connector.validators import validate_date_range, validate_page

logger = logging.getLogger(__name__)

# Štruktúrované JSON logovanie (openmcp_sdk) — centrálny collector ho rozbalí do
# poľa .app. Component z env OPENMCP_COMPONENT (default mcp-upgates).
_log_setup(component=_os.getenv("OPENMCP_COMPONENT", "mcp-upgates"))

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
_D_PAGE = Field(description="Page number (starting from 1)", ge=1)
_D_LANGUAGE = Field(description="Filter by language (ISO 639-1)")
_D_DATE_FROM = Field(description="Filter from this date (YYYY-MM-DD)")
_D_DATE_TO = Field(description="Filter to this date (YYYY-MM-DD)")


# =============================================================================
# Klient + společná cesta požadavku
# =============================================================================
def _client() -> UpgatesClient:
    """Upgates klient z aktuálního request kontextu (SDK identita + creds)."""
    ctx = current_context()
    return UpgatesClient(
        api_url=ctx.config["api_url"],
        api_login=ctx.config["api_login"],
        api_key=ctx.secrets["api_key"],
    )


def _anon_enabled() -> bool:
    return bool(current_context().config.get("anonymize_data", True))


def _pseudonymizer() -> Pseudonymizer:
    return Pseudonymizer(derive_key(current_context().principal.sub))


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
        body = client.get(path, params)
    except UpgatesError as exc:
        raise ConnectorError(ErrorCode.UPSTREAM_ERROR, str(exc)) from exc
    finally:
        client.close()

    data = _unwrap(body)
    if optimize is not None:
        data = optimize_list_response(data, optimize)
    if anonymize and _anon_enabled():
        data = _pseudonymizer().sanitize(data)
    return data


def _query(**kwargs: Any) -> dict[str, Any]:
    """Sestav query z nenulových parametrů (ekvivalent TS buildQueryParams)."""
    return {k: v for k, v in kwargs.items() if v is not None}


# =============================================================================
# Objednávky (Orders)
# =============================================================================
def list_orders(
    order_number: Annotated[str | None, Field(description="Specific order number")] = None,
    creation_time_from: Annotated[str | None, _D_DATE_FROM] = None,
    creation_time_to: Annotated[str | None, _D_DATE_TO] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filter orders updated from this date (YYYY-MM-DD)")] = None,
    paid_yn: Annotated[bool | None, Field(description="Filter by paid status")] = None,
    status: Annotated[str | None, Field(description="Filter by order status name")] = None,
    status_id: Annotated[int | None, Field(description="Filter by order status ID")] = None,
    email: Annotated[str | None, Field(description="Filter by customer email")] = None,
    phone: Annotated[str | None, Field(description="Filter by customer phone (MSISDN format)")] = None,
    external_order_number: Annotated[str | None, Field(description="Filter by external order number")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    page: Annotated[int, _D_PAGE] = 1,
    order_by: Annotated[str, Field(description="Order by field: creation_time | last_update_time")] = "creation_time",
    order_dir: Annotated[str, Field(description="Sort direction: asc | desc")] = "desc",
) -> Any:
    """List orders with filtering and pagination (max 15 items per page).

    Customer data is pseudonymized before it leaves the connector.
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
    order_number: Annotated[str, Field(description="Order number")],
) -> Any:
    """Get history of a specific order. Customer data is pseudonymized."""
    path = f"/orders/{_path_segment(order_number, 'order_number')}/history"
    return _get(path, anonymize=True)


# =============================================================================
# Stavy objednávek (Order statuses)
# =============================================================================
def list_order_statuses(
    id: Annotated[int | None, Field(description="Specific status ID")] = None,
    type: Annotated[str | None, Field(description="Status type: Received | Canceled | Sent | PaymentSuccessful | PaymentFailed | Custom")] = None,
) -> Any:
    """List all order statuses."""
    endpoint = f"/order-statuses/{_path_segment(id, 'id')}" if id else "/order-statuses"
    return _get(endpoint, _query(id=id, type=type))


# =============================================================================
# Faktury (Invoices)
# =============================================================================
def list_invoices(
    invoice_number: Annotated[str | None, Field(description="Specific invoice number")] = None,
    creation_time_from: Annotated[str | None, _D_DATE_FROM] = None,
    creation_time_to: Annotated[str | None, _D_DATE_TO] = None,
    paid_yn: Annotated[bool | None, Field(description="Filter by paid status")] = None,
    type: Annotated[str | None, Field(description="Invoice type: invoice | creditNote | receipt")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List invoices with filtering and pagination. Customer data is pseudonymized."""
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
    code: Annotated[str | None, Field(description="Product code")] = None,
    product_id: Annotated[int | None, Field(description="Product ID")] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filter products updated from this date (YYYY-MM-DD)")] = None,
    active_yn: Annotated[bool | None, Field(description="Filter by active status (default: true)")] = None,
    archived_yn: Annotated[bool | None, Field(description="Filter by archived status")] = None,
    can_add_to_basket_yn: Annotated[bool | None, Field(description="Filter by can add to basket")] = None,
    in_stock_yn: Annotated[bool | None, Field(description="Filter by in stock status")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    pricelist: Annotated[str | None, Field(description="Filter by pricelist name")] = None,
    variants_yn: Annotated[bool | None, Field(description="Include variants (default: false)")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List products with filtering and pagination (max 15 items per page)."""
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
    code: Annotated[str | None, Field(description="Product code")] = None,
    product_id: Annotated[int | None, Field(description="Product ID")] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filter products updated from this date (YYYY-MM-DD)")] = None,
    active_yn: Annotated[bool | None, Field(description="Filter by active status")] = None,
    in_stock_yn: Annotated[bool | None, Field(description="Filter by in stock status")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List products in simplified format (max 50 items per page)."""
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
    customer_id: Annotated[int | None, Field(description="Specific customer ID")] = None,
    code: Annotated[str | None, Field(description="Customer code")] = None,
    email: Annotated[str | None, Field(description="Customer email")] = None,
    phone: Annotated[str | None, Field(description="Customer phone")] = None,
    active_yn: Annotated[bool | None, Field(description="Filter by active status (default: true)")] = None,
    blocked_yn: Annotated[bool | None, Field(description="Filter by blocked status (default: false)")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    pricelist: Annotated[str | None, Field(description="Filter by pricelist")] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filter customers updated from this date (YYYY-MM-DD)")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List customers with filtering and pagination. Personal data is pseudonymized."""
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
    code: Annotated[str | None, Field(description="Category code")] = None,
    category_id: Annotated[int | None, Field(description="Category ID")] = None,
    parent_id: Annotated[int | None, Field(description="Filter by parent category ID")] = None,
    active_yn: Annotated[bool | None, Field(description="Filter by active status (default: true)")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    last_update_time_from: Annotated[str | None, Field(description="Filter categories updated from this date (YYYY-MM-DD)")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List categories with filtering and pagination (max 15 items per page)."""
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
    id: Annotated[int | None, Field(description="Specific label ID")] = None,
    type: Annotated[str | None, Field(description="Label type: action | new | sale | custom")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List product labels (max 50 items per page)."""
    validate_page(page)
    endpoint = f"/labels/{_path_segment(id, 'id')}" if id else "/labels"
    return _get(endpoint, _query(id=id, type=type, page=page))


def list_availabilities(
    id: Annotated[int | None, Field(description="Specific availability ID")] = None,
    type: Annotated[str | None, Field(description="Availability type: OnRequest | NotAvailable | InStock | Custom")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List product availabilities (max 50 items per page)."""
    validate_page(page)
    endpoint = f"/availabilities/{_path_segment(id, 'id')}" if id else "/availabilities"
    return _get(endpoint, _query(id=id, type=type, page=page))


def list_manufacturers(
    id: Annotated[int | None, Field(description="Specific manufacturer ID")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List manufacturers (max 50 items per page)."""
    validate_page(page)
    endpoint = f"/manufacturers/{_path_segment(id, 'id')}" if id else "/manufacturers"
    return _get(endpoint, _query(id=id, page=page))


def list_parameters(
    id: Annotated[int | None, Field(description="Specific parameter ID")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List product parameters."""
    validate_page(page)
    endpoint = f"/parameters/{_path_segment(id, 'id')}" if id else "/parameters"
    return _get(endpoint, _query(id=id, page=page))


# =============================================================================
# Košíky (Carts)
# =============================================================================
def list_carts(
    id: Annotated[int | None, Field(description="Specific cart ID")] = None,
    creation_time_from: Annotated[str | None, Field(description="Filter carts created from this date (YYYY-MM-DD); default: last 7 days")] = None,
    language: Annotated[str | None, _D_LANGUAGE] = None,
    filled_delivery_info_yn: Annotated[bool | None, Field(description="Filter carts with filled delivery info")] = None,
    customer_logged_in_yn: Annotated[bool | None, Field(description="Filter carts with logged in customers")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List shopping carts (max 15 items per page). Customer data is pseudonymized.

    Defaults to carts from the last 7 days when no date filter or id is given.
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
    voucher_code: Annotated[str | None, Field(description="Specific voucher code")] = None,
    active_yn: Annotated[bool | None, Field(description="Filter by active status (default: true)")] = None,
    global_yn: Annotated[bool | None, Field(description="Filter by reusable status")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List discount vouchers (max 100 items per page)."""
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
    id: Annotated[int | None, Field(description="Specific shipment ID")] = None,
    code: Annotated[str | None, Field(description="Shipment code")] = None,
    type: Annotated[str | None, Field(description="Shipment type: custom | ceskaPosta | slovenskaPosta | zasilkovna | dpd | ppl | gls")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List shipping methods (multi-language descriptions are trimmed)."""
    validate_page(page)
    endpoint = f"/shipments/{_path_segment(id, 'id')}" if id else "/shipments"
    return _get(endpoint, _query(id=id, code=code, type=type, page=page), optimize="shipments")


def list_payments(
    id: Annotated[int | None, Field(description="Specific payment ID")] = None,
    code: Annotated[str | None, Field(description="Payment code")] = None,
    type: Annotated[str | None, Field(description="Payment type: cash | cashOnDelivery | command | paypal | gopay | stripe | custom")] = None,
    page: Annotated[int, _D_PAGE] = 1,
) -> Any:
    """List payment methods (multi-language descriptions are trimmed)."""
    validate_page(page)
    endpoint = f"/payments/{_path_segment(id, 'id')}" if id else "/payments"
    return _get(endpoint, _query(id=id, code=code, type=type, page=page), optimize="payments")


# =============================================================================
# Webhooky (Webhooks)
# =============================================================================
def list_webhooks(
    id: Annotated[int | None, Field(description="Specific webhook ID")] = None,
) -> Any:
    """List configured webhooks."""
    endpoint = f"/webhooks/{_path_segment(id, 'id')}" if id else "/webhooks"
    return _get(endpoint)


def list_webhook_events() -> Any:
    """List available webhook events."""
    return _get("/webhooks/events")


# =============================================================================
# Konfigurace e-shopu (Config, Languages, Owner, Status, Pricelists)
# =============================================================================
def get_languages() -> Any:
    """Get e-shop languages configuration."""
    return _get("/languages")


def get_shop_config() -> Any:
    """Get e-shop configuration and settings."""
    return _get("/config")


def get_shop_owner() -> Any:
    """Get e-shop owner billing information. Business data is pseudonymized."""
    return _get("/owner", anonymize=True)


def get_api_status() -> Any:
    """Get API status and list of allowed endpoints for the current user."""
    return _get("/status")


def list_pricelists() -> Any:
    """List pricelists."""
    return _get("/pricelists")


# =============================================================================
# Test spojení
# =============================================================================
def test_connection() -> str:
    """Ad-hoc test spojení s Upgates (SDK interní `POST /test`).

    `_client()` samotný smí spadnout (`UpgatesError` z neplatné URL, `KeyError`
    z chybějícího pole v kontextu) dřív, než stihne cokoliv zavolat — bez
    vlastního try/except by taková chyba unikla jako 500. Klasifikace chyby
    z `client.get()` je strukturovaná přes `UpgatesError.status_code`: 401/403
    (neplatný login/klíč) → INVALID_INPUT (uživatel to má šanci opravit),
    cokoliv jiného (timeout, 5xx, rate limit) → UPSTREAM_UNAVAILABLE. Zprávě se
    záměrně nepředává syrový `str(exc)` (může nést vendor tělo).
    """
    try:
        client = _client()
    except (UpgatesError, KeyError) as exc:
        raise ConnectorError(ErrorCode.INVALID_INPUT, "Neplatné údaje připojení") from exc

    try:
        client.get("/status")
    except UpgatesError as exc:
        if exc.status_code in (401, 403):
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
