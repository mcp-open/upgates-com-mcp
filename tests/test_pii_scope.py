"""Rozsah izolace PII tokenů — vlastník credentials, ne volající.

Data tenant je Upgates e-shop, ke kterému patří `api_key`. Ten může vlastnit
tým: odvození klíče z `principal.sub` dávalo každému členovi jiný token pro
téhož zákazníka, takže se stejný záznam ve dvou konverzacích nedal spárovat.
"""

from __future__ import annotations

import pytest

from openmcp_sdk import testing
from openmcp_sdk.context import Principal, RequestContext, reset_context, set_context
from openmcp_sdk.pii import derive_key

from connector import server

_CFG = {
    "api_url": "https://acme.admin.server.upgates.com/api/v2",
    "api_login": "u",
}


class _Fake:
    def __init__(self, response):
        self._response = response

    def get_json(self, path, params=None):
        return self._response

    def close(self):
        pass


def _with_principal(principal: Principal):
    return set_context(RequestContext(principal, {"api_key": "k"}, _CFG))


def test_team_owned_credentials_share_one_token_space():
    """Dva členové téhož týmu musí pro stejný e-mail dostat stejný token."""
    team = "1e2d3c4b-5a69-4788-9abc-def012345678"
    tokens = []
    for sub in ("member-1", "member-2"):
        token = _with_principal(
            Principal(
                sub=sub,
                credential_version=3,
                credential_owner_kind="team",
                credential_owner_id=team,
            )
        )
        try:
            tokens.append(server._pseudonymizer().sanitize({"email": "jan@example.cz"})["email"])
        finally:
            reset_context(token)
    assert tokens[0] == tokens[1]
    assert tokens[0].startswith("<EMAIL_")


def test_different_teams_stay_isolated():
    tokens = []
    for team in (
        "1e2d3c4b-5a69-4788-9abc-def012345678",
        "2f3e4d5c-6b7a-4899-8bcd-ef0123456789",
    ):
        token = _with_principal(
            Principal(
                sub="member-1",
                credential_version=3,
                credential_owner_kind="team",
                credential_owner_id=team,
            )
        )
        try:
            tokens.append(server._pseudonymizer().sanitize({"email": "jan@example.cz"})["email"])
        finally:
            reset_context(token)
    assert tokens[0] != tokens[1]


def test_user_owned_credentials_keep_the_historical_token():
    """`kind == "user"` má dle kontraktu SDK `credential_owner_id == sub`.

    Tokeny uživatelsky vlastněného připojení se tedy nesmí hnout ani o bit —
    jinak by uživatel po nasazení viděl jiné ID pro tentýž záznam.
    """
    sub = "3a4b5c6d-7e8f-4900-9abc-def012345678"
    token = _with_principal(
        Principal(
            sub=sub,
            credential_version=3,
            credential_owner_kind="user",
            credential_owner_id=sub,
        )
    )
    try:
        owned = server._pseudonymizer().sanitize({"email": "jan@example.cz"})["email"]
    finally:
        reset_context(token)

    with testing.with_context({"api_key": "k"}, _CFG, sub=sub):
        plain = server._pseudonymizer().sanitize({"email": "jan@example.cz"})["email"]
    assert owned == plain


class _Principal:
    """Principal s libovolným `credential_owner_id`.

    Skutečný `openmcp_sdk.Principal` prázdný ani mezerový owner id nepostaví
    (`__post_init__` na něm volá `UUID(...)`), takže obranná větev `_pii_scope`
    se přes něj otestovat nedá.
    """

    def __init__(self, sub, credential_owner_id):
        self.sub = sub
        self.credential_owner_id = credential_owner_id


@pytest.mark.parametrize("owner", [None, "", "   ", "\t\n"])
def test_missing_or_blank_owner_falls_back_to_sub(owner):
    """`derive_key` prázdnou část rozsahu odmítá — fallback musí být bezpečný.

    Stdio režim a lokální běh `credential_owner_id` vůbec nemají.
    """
    token = set_context(RequestContext(_Principal("s1", owner), {"api_key": "k"}, _CFG))
    try:
        assert server._pii_scope() == "s1"
        assert server._pseudonymizer().sanitize({"email": "a@b.cz"})["email"].startswith("<EMAIL_")
    finally:
        reset_context(token)


def test_blank_owner_token_equals_the_plain_sub_token():
    token = set_context(RequestContext(_Principal("s1", "   "), {"api_key": "k"}, _CFG))
    try:
        blank = server._pseudonymizer().sanitize({"email": "a@b.cz"})["email"]
    finally:
        reset_context(token)
    with testing.with_context({"api_key": "k"}, _CFG, sub="s1"):
        assert blank == server._pseudonymizer().sanitize({"email": "a@b.cz"})["email"]


def test_pii_scope_matches_derive_key_of_the_owner():
    team = "1e2d3c4b-5a69-4788-9abc-def012345678"
    token = _with_principal(
        Principal(
            sub="member-1",
            credential_version=3,
            credential_owner_kind="team",
            credential_owner_id=team,
        )
    )
    try:
        assert server._pii_scope() == team
        # Bez prefixu podle druhu vlastníka — klíč zůstává jednodílný.
        assert derive_key(server._pii_scope()) == derive_key(team)
    finally:
        reset_context(token)


def test_tools_use_the_owner_scope_end_to_end(monkeypatch):
    team = "1e2d3c4b-5a69-4788-9abc-def012345678"
    monkeypatch.setattr(
        server, "UpstreamClient", lambda **kw: _Fake({"orders": [{"customer": {"email": "a@b.cz"}}]})
    )
    tokens = []
    for sub in ("member-1", "member-2"):
        token = _with_principal(
            Principal(
                sub=sub,
                credential_version=3,
                credential_owner_kind="team",
                credential_owner_id=team,
            )
        )
        try:
            tokens.append(server.list_orders()["orders"][0]["customer"]["email"])
        finally:
            reset_context(token)
    assert tokens[0] == tokens[1]
