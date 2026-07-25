"""`server.test_connection` — ad-hoc test spojení s Upgates (GET /status)."""

from __future__ import annotations

import pytest

from openmcp_sdk import testing
from openmcp_sdk.envelope import ConnectorError, ErrorCode

from connector import server

_CFG = {
    "api_url": "https://acme.admin.server.upgates.com/api/v2",
    "api_login": "u",
}


class _Fake:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    def get_json(self, path, params=None):
        if self._error is not None:
            raise self._error
        return self._response

    def close(self):
        pass


def test_connection_success_returns_message_with_shop_url(monkeypatch):
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake({"status": "ok"}))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        message = server.test_connection()
    assert _CFG["api_url"] in message
    assert "Připojeno" in message


def test_connection_invalid_credentials_raises_invalid_input(monkeypatch):
    err = ConnectorError(ErrorCode.FORBIDDEN, "upstream odmítl přístupové údaje", status=401)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "bad"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INVALID_INPUT
    assert exc.value.message == "Neplatný API login nebo klíč"


def test_connection_403_also_invalid_input(monkeypatch):
    err = ConnectorError(ErrorCode.FORBIDDEN, "upstream odmítl přístup", status=403)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INVALID_INPUT


def test_connection_network_error_maps_to_upstream_unavailable(monkeypatch):
    err = ConnectorError(ErrorCode.UPSTREAM_UNAVAILABLE, "upstream je nedostupný")
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.UPSTREAM_UNAVAILABLE
    assert exc.value.message == "Nepodařilo se spojit s Upgates — zkus to prosím znovu."


def test_connection_5xx_maps_to_upstream_unavailable_without_leaking_body(monkeypatch):
    err = ConnectorError(ErrorCode.UPSTREAM_ERROR, "upstream selhal se stavem 503", status=503)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.UPSTREAM_UNAVAILABLE
    assert "503" not in exc.value.message


def test_connection_client_construction_failure_raises_invalid_input(monkeypatch):
    def _boom(**kw):
        raise ConnectorError(ErrorCode.INVALID_INPUT, "base_url musí být absolutní http(s) adresa")

    monkeypatch.setattr(server, "UpstreamClient", _boom)
    with testing.with_context({"api_key": "k"}, {**_CFG, "api_url": "bad"}, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INVALID_INPUT
    assert exc.value.message == "Neplatné údaje připojení"


def test_connection_missing_context_field_raises_invalid_input():
    # _client() čte ctx.secrets["api_key"] — chybějící klíč (reálný KeyError)
    # musí být zachycen jako business chyba, ne uniknout jako 500.
    with testing.with_context({}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INVALID_INPUT
    assert exc.value.message == "Neplatné údaje připojení"
