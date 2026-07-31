"""`connector.yaml` musí být platný manifest podle `openmcp_sdk.manifest`
a jeho display.tools se nesmí rozejít s reálně zaregistrovanými nástroji."""

from __future__ import annotations

import asyncio
from pathlib import Path

from packaging.version import Version

from openmcp_sdk._version import __version__ as sdk_version
from openmcp_sdk.manifest import load_manifest

MANIFEST_PATH = Path(__file__).resolve().parent.parent / "connector.yaml"


def test_manifest_loads_and_validates() -> None:
    manifest = load_manifest(str(MANIFEST_PATH))

    assert manifest.slug == "upgates"
    assert manifest.capabilities.default_read_only is True
    assert manifest.capabilities.supports_write is False
    assert manifest.capabilities.supports_test is True

    cred_keys = {f.key for f in manifest.credentials}
    assert cred_keys == {"api_url", "api_login", "api_key"}

    api_key_field = next(f for f in manifest.credentials if f.key == "api_key")
    assert api_key_field.secret is True and api_key_field.required is True
    # URL a login nejsou secret → skončí v ctx.config, ne v ctx.secrets.
    for key in ("api_url", "api_login"):
        assert next(f for f in manifest.credentials if f.key == key).secret is False

    assert manifest.operator_config == []

    assert manifest.egress["port"] == 443
    assert manifest.egress["methods"] == ["GET"]


def test_localized_credential_fields_carry_a_hint() -> None:
    """`display.locales.*.fields[].hint` vyžaduje SDK >= 0.4.3.

    Starší SDK ho odmítne jako `extra_forbidden` a konektor vůbec nenaběhne —
    manifest s hinty a pin na SDK bez podpory se rozešly celý jeden release.
    API lokalizací nápovědu vždy přepíše, takže pole bez překladu zůstane v UI
    úplně bez hintu.
    """
    manifest = load_manifest(str(MANIFEST_PATH))
    cred_keys = {f.key for f in manifest.credentials}

    assert set(manifest.display.locales) == {"cs", "sk"}
    for locale, display in manifest.display.locales.items():
        assert {f.key for f in display.fields} == cred_keys, locale
        for field in display.fields:
            assert field.hint.strip(), (locale, field.key)


#: Kde v administraci Upgates uživatel API přístup i přesnou URL najde.
#: Nápověda je jediné vodítko, které při zapojování konektoru má — špatná
#: cesta ho posílá do menu, kde API vůbec není.
_ADMIN_PATH = {"cs": "Doplňky → API", "sk": "Doplnky → API"}
_WRONG_ADMIN_PATHS = ("Nastavení → API", "Nastavenia → API")


def _all_credential_hints() -> list[tuple[str, str, str]]:
    """`(locale, key, hint)` pro kořenové i lokalizované nápovědy."""
    manifest = load_manifest(str(MANIFEST_PATH))
    hints = [("default", field.key, field.hint) for field in manifest.credentials]
    for locale, display in manifest.display.locales.items():
        hints += [(locale, field.key, field.hint) for field in display.fields]
    return hints


def test_no_credential_hint_points_at_the_settings_menu() -> None:
    """API přístup je v Upgates pod `Doplňky → API`, ne pod `Nastavení`."""
    for locale, key, hint in _all_credential_hints():
        for wrong in _WRONG_ADMIN_PATHS:
            assert wrong not in hint, (locale, key, wrong)


def test_login_and_key_hints_point_at_the_addons_api_screen() -> None:
    for locale, key, hint in _all_credential_hints():
        if key not in {"api_login", "api_key"}:
            continue
        expected = _ADMIN_PATH.get(locale, _ADMIN_PATH["cs"])
        assert expected in hint, (locale, key, hint)


def test_sdk_min_version_covers_the_manifest_features() -> None:
    manifest = load_manifest(str(MANIFEST_PATH))
    assert Version(manifest.sdk_min_version) >= Version("0.4.3")
    assert Version(sdk_version) >= Version(manifest.sdk_min_version)


def test_display_tools_match_registered_tools() -> None:
    """`display.tools` je to, co katalog ukazuje — nesmí se rozejít s realitou."""
    from connector import server

    manifest = load_manifest(str(MANIFEST_PATH))
    display_names = {t.name for t in manifest.display.tools}
    registered = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    assert display_names == registered
