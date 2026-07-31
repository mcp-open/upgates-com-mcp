"""`server.test_connection` — ad-hoc test spojení s Upgates (GET /status)."""

from __future__ import annotations

import functools

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


def _failing_client(error, **kwargs):
    return _Fake(error=error)


def test_connection_client_is_single_attempt_and_fits_the_platform_budget(monkeypatch):
    """Platforma má na test spojení tvrdý strop 12 s.

    S výchozím retry (4 pokusy) a 30s timeoutem by konektor strop přestřelil
    a uživatel by místo příčiny dostal timeout řídicí roviny.
    """
    captured = {}
    monkeypatch.setattr(
        server, "UpstreamClient", lambda **kw: captured.update(kw) or _Fake({"status": "ok"})
    )
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        server.test_connection()

    assert captured["retry"].max_attempts == 1
    assert captured["timeout"] == 8.0
    assert captured["connect_timeout"] == 3.0
    assert captured["timeout"] + captured["connect_timeout"] < 12.0


def test_connection_success_returns_message_with_shop_url(monkeypatch):
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake({"status": "ok"}))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        message = server.test_connection()
    assert _CFG["api_url"] in message
    assert "Připojeno" in message


@pytest.mark.parametrize("status", [400, 401])
def test_connection_bad_login_or_key_is_credential_invalid(monkeypatch, status):
    """400/401 na bezargumentový `/status` = špatný login nebo klíč.

    `CREDENTIAL_INVALID` projde normalizérem řídicí roviny beze změny; dřív se
    hlásilo `INVALID_INPUT`, které se na `credential_invalid` teprve překládalo.
    """
    err = ConnectorError(ErrorCode.FORBIDDEN, "upstream odmítl přístupové údaje", status=status)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "bad"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.CREDENTIAL_INVALID
    assert exc.value.message == "Neplatný API login nebo klíč"


def test_connection_403_advises_activating_the_api_user_not_adding_read_rights(monkeypatch):
    """`/status` je povolený každému API uživateli.

    403 na něm tedy neznamená chybějící právo na čtení, ale neaktivního nebo
    po pěti neúspěšných pokusech zablokovaného API uživatele. Rada „přidej
    klíči read oprávnění" by uživatele poslala úplně jinam.
    """
    err = ConnectorError(ErrorCode.FORBIDDEN, "upstream odmítl přístup", status=403)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()

    assert exc.value.code == ErrorCode.PROVIDER_PERMISSION_DENIED
    message = exc.value.message
    # Akční rada: aktivovat uživatele, po lockoutu ověřit přihlašovací údaje.
    assert "aktivní" in message
    assert "API" in message
    assert "pokusech" in message
    # A netvrdí, že chybí oprávnění ke čtení.
    assert "oprávnění" not in message
    assert "právo" not in message
    assert "čtení" not in message


@pytest.mark.parametrize("status", [301, 404, 410])
def test_connection_unknown_shop_is_instance_unknown(monkeypatch, status):
    """301/404/410 = špatná `api_url`, ne špatný klíč."""
    err = ConnectorError(ErrorCode.INVALID_INPUT, f"upstream odmítl {status}", status=status)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.INSTANCE_UNKNOWN
    assert exc.value.message != "Neplatný API login nebo klíč"


def test_connection_301_and_404_give_different_actionable_advice(monkeypatch):
    """301 = e-shop se přesunul, 404/410 = e-shop neexistuje.

    Uživatel dělá v každém případě něco jiného: u 301 si načte novou adresu,
    u 404 hledá překlep nebo zrušený účet. Jedna společná hláška to smazala.
    """
    messages = {}
    for status in (301, 404):
        err = ConnectorError(ErrorCode.INVALID_INPUT, "x", status=status)
        monkeypatch.setattr(
            server, "UpstreamClient", functools.partial(_failing_client, err)
        )
        with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
            with pytest.raises(ConnectorError) as exc:
                server.test_connection()
        messages[status] = exc.value.message

    assert messages[301] != messages[404]
    assert "přesunul" in messages[301]
    assert "neexistuje" in messages[404] or "zrušen" in messages[404]


def test_connection_rate_limit_is_not_reported_as_bad_credentials(monkeypatch):
    """429 je dočasné — nesmí uživateli zneplatnit zdravé připojení."""
    err = ConnectorError(ErrorCode.RATE_LIMITED, "upstream odmítl request", status=429)
    monkeypatch.setattr(server, "UpstreamClient", lambda **kw: _Fake(error=err))
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.RATE_LIMITED


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


def test_connection_client_construction_failure_is_credential_invalid(monkeypatch):
    """Vadná `api_url` je problém přihlašovacích údajů, ne runtime.

    `INVALID_INPUT` se v public safe-test větvi normalizéru překlápí na
    `runtime_unavailable` a příčina by se uživateli ztratila;
    `CREDENTIAL_INVALID` projde v obou větvích beze změny.
    """

    def _boom(**kw):
        raise ConnectorError(ErrorCode.INVALID_INPUT, "base_url musí být absolutní http(s) adresa")

    monkeypatch.setattr(server, "UpstreamClient", _boom)
    with testing.with_context({"api_key": "k"}, {**_CFG, "api_url": "bad"}, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.CREDENTIAL_INVALID
    assert "URL API" in exc.value.message
    # Vendor detail z původní výjimky ven nesmí.
    assert "base_url" not in exc.value.message


def test_connection_missing_secret_is_credential_invalid():
    # _client() čte ctx.secrets["api_key"] — chybějící klíč (reálný KeyError)
    # musí být zachycen jako chyba přihlašovacích údajů, ne uniknout jako 500.
    with testing.with_context({}, _CFG, sub="s1"):
        with pytest.raises(ConnectorError) as exc:
            server.test_connection()
    assert exc.value.code == ErrorCode.CREDENTIAL_INVALID
    assert "klíč" in exc.value.message
