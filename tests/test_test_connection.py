"""`server.test_connection` — ad-hoc test spojení s Upgates (GET /status)."""

from __future__ import annotations

import pytest

from openmcp_sdk import testing
from openmcp_sdk.envelope import ConnectorError, ErrorCode

from connector import server
from connector.client import UpgatesError

_CFG = {"api_url": "https://acme.admin.upgates.com/api/v2", "api_login": "u"}


class _Fake:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    def get(self, path, params=None):
        if self._error is not None:
            raise self._error
        return self._response

    def close(self):
        pass


def test_connection_success_returns_message_with_shop_url(monkeypatch):
    monkeypatch.setattr(server, "UpgatesClient", lambda **kw: _Fake({"status": "ok"}))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        message = server.test_connection()
    assert _CFG["api_url"] in message
    assert "Připojeno" in message


def test_connection_invalid_credentials_raises_invalid_input(monkeypatch):
    err = UpgatesError("Upgates odmítl přihlášení", status_code=401)
    monkeypatch.setattr(server, "UpgatesClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "bad"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INVALID_INPUT
    assert exc.value.message == "Neplatný API login nebo klíč"


def test_connection_403_also_invalid_input(monkeypatch):
    err = UpgatesError("forbidden", status_code=403)
    monkeypatch.setattr(server, "UpgatesClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INVALID_INPUT


def test_connection_network_error_maps_to_upstream_unavailable(monkeypatch):
    err = UpgatesError("Síťová chyba při GET /status (po 4 pokusech): timeout")
    monkeypatch.setattr(server, "UpgatesClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.UPSTREAM_UNAVAILABLE
    assert exc.value.message == "Nepodařilo se spojit s Upgates — zkus to prosím znovu."


def test_connection_5xx_maps_to_upstream_unavailable_without_leaking_body(monkeypatch):
    err = UpgatesError("HTTP 503 při GET /status: <vendor body>", status_code=503)
    monkeypatch.setattr(server, "UpgatesClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.UPSTREAM_UNAVAILABLE
    assert "503" not in exc.value.message


def test_connection_client_construction_failure_raises_invalid_input(monkeypatch):
    def _boom(**kw):
        raise UpgatesError("Neplatná URL API e-shopu")

    monkeypatch.setattr(server, "UpgatesClient", _boom)
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
