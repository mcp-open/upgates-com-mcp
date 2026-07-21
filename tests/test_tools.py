"""Unit testy pro `upgates` nástroje — přímo, bez běžícího MCP transportu.

`_client()` staví `UpstreamClient` výhradně z `openmcp_sdk.current_context()`
(secrets `api_key`, config `api_url`/`api_login`) — testy proto monkeypatchují
`server.UpstreamClient` místo mockování sítě.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

import pytest

from openmcp_sdk import testing
from openmcp_sdk.envelope import ConnectorError, ErrorCode

from connector import server

_CFG = {"api_url": "https://acme.admin.upgates.com/api/v2", "api_login": "u"}


class _Fake:
    """Stub UpstreamClient — zaznamená path/params, vrací předpřipravenou odpověď."""

    def __init__(self, response=None):
        self._response = response if response is not None else {"ok": True}
        self.calls: list[tuple[str, dict | None]] = []

    def get_json(self, path, params=None):
        self.calls.append((path, params))
        return self._response

    def close(self):
        pass


def _patch(monkeypatch, response=None):
    fake = _Fake(response)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: fake)
    return fake


def test_client_built_from_context(monkeypatch):
    captured = {}
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: captured.update(kw) or _Fake())
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        server.get_api_status()
    assert captured == {"base_url": _CFG["api_url"], "auth": ("u", "k")}


@pytest.mark.parametrize(
    "api_url",
    [
        "http://acme.admin.upgates.com/api/v2",
        "https://attacker.example/api/v2",
        "https://acme.admin.upgates.com.evil.example/api/v2",
        "https://admin.upgates.com/api/v2",
        "https://user:pass@acme.admin.upgates.com/api/v2",
        "https://acme.admin.upgates.com:8443/api/v2",
        "https://acme.admin.upgates.com/api/v2/other",
        "https://acme.admin.upgates.com/api/v2?key=value",
        " https://acme.admin.upgates.com/api/v2",
    ],
)
def test_client_never_sends_basic_credentials_outside_exact_upgates_origin(
    monkeypatch, api_url
):
    called = False

    def capture(**kwargs):
        nonlocal called
        called = True
        return _Fake()

    monkeypatch.setattr(server, "UpstreamClient", capture)
    with testing.with_context(
        {"api_key": "must-not-leave"},
        {**_CFG, "api_url": api_url},
        sub="s1",
    ):
        with pytest.raises(ConnectorError) as exc:
            server._client()
    assert exc.value.code is ErrorCode.INVALID_INPUT
    assert called is False


def test_client_normalizes_allowed_upgates_url_before_attaching_basic_auth(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        server, "UpstreamClient", lambda **kw: captured.update(kw) or _Fake()
    )
    with testing.with_context(
        {"api_key": "k"},
        {**_CFG, "api_url": "https://acme.admin.upgates.com:443/api/v2/"},
        sub="s1",
    ):
        server._client()
    assert captured == {
        "base_url": "https://acme.admin.upgates.com:443/api/v2",
        "auth": ("u", "k"),
    }


def test_list_orders_optimizes_and_anonymizes(monkeypatch):
    page = {
        "current_page": 1,
        "orders": [
            {"order_number": "1", "customer": {"email": "jan@example.cz"}, "order_total": 100},
        ],
    }
    _patch(monkeypatch, page)
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        out = server.list_orders()
    order = out["orders"][0]
    assert order["order_number"] == "1"
    assert order["customer"]["email"].startswith("<EMAIL_")  # anonymizováno
    assert order["order_total"] == 100
    assert out["mcp_limited_to"] == 15  # optimalizace proběhla


def test_anonymize_disabled_passes_customer_data(monkeypatch):
    page = {"orders": [{"order_number": "1", "customer": {"email": "jan@example.cz"}}]}
    _patch(monkeypatch, page)
    with testing.with_context({"api_key": "k"}, {**_CFG, "anonymize_data": False}, sub="s1"):
        out = server.list_orders()
    assert out["orders"][0]["customer"]["email"] == "jan@example.cz"


def test_list_orders_default_query(monkeypatch):
    fake = _patch(monkeypatch, {"orders": []})
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        server.list_orders()
    path, params = fake.calls[0]
    assert path == "/orders"
    assert params["page"] == 1
    assert params["order_by"] == "creation_time"
    assert params["order_dir"] == "desc"


def test_list_orders_single_order_endpoint_encoded(monkeypatch):
    fake = _patch(monkeypatch, {"orders": []})
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        server.list_orders(order_number="A/../secret")
    path, _ = fake.calls[0]
    assert path.startswith("/orders/")
    assert "/secret" not in path  # path injection zneškodněna
    assert "%2F" in path


def test_list_products_not_anonymized_and_optimized(monkeypatch):
    page = {"products": [{"code": "P1", "descriptions": [{"title": "Boty"}], "product_id": 9}]}
    _patch(monkeypatch, page)
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        out = server.list_products()
    prod = out["products"][0]
    assert prod["code"] == "P1"  # kód produktu se netokenizuje
    assert prod["title"] == "Boty"


def test_list_carts_defaults_to_last_7_days(monkeypatch):
    fake = _patch(monkeypatch, {"carts": []})
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        server.list_carts()
    _, params = fake.calls[0]
    expected = (date.today() - timedelta(days=7)).isoformat()
    assert params["creation_time_from"] == expected


def test_invalid_date_range_raises(monkeypatch):
    _patch(monkeypatch, {"orders": []})
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.list_orders(creation_time_from="2026-05-01", creation_time_to="2026-04-01")
    assert exc.value.code == ErrorCode.INVALID_INPUT


def test_invalid_date_format_raises(monkeypatch):
    _patch(monkeypatch, {"invoices": []})
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.list_invoices(creation_time_from="01-05-2026")
    assert exc.value.code == ErrorCode.INVALID_INPUT


def test_upstream_error_maps_to_connector_error(monkeypatch):
    class _Boom:
        def get_json(self, path, params=None):
            raise ConnectorError(ErrorCode.UPSTREAM_ERROR, "upstream selhal se stavem 500", status=500)

        def close(self):
            pass

    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Boom())
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.list_pricelists()
    assert exc.value.code == ErrorCode.UPSTREAM_ERROR


EXPECTED_TOOLS = {
    "list_orders", "get_order_history", "list_order_statuses", "list_invoices",
    "list_products", "list_products_simple", "list_customers", "list_categories",
    "list_labels", "list_availabilities", "list_manufacturers", "list_parameters",
    "list_carts", "list_vouchers", "list_shipments", "list_payments",
    "list_webhooks", "list_webhook_events", "get_languages", "get_shop_config",
    "get_shop_owner", "get_api_status", "list_pricelists",
}


def test_tool_inventory_all_read_only():
    tools = asyncio.run(server.mcp.get_tools())
    assert set(tools) == EXPECTED_TOOLS
    assert len(tools) == 23
    for name, tool in tools.items():
        assert tool.annotations.readOnlyHint is True, name


def test_no_write_or_delete_tools_registered():
    tools = asyncio.run(server.mcp.get_tools())
    forbidden = [n for n in tools if any(w in n for w in ("create", "update", "delete"))]
    assert forbidden == []
