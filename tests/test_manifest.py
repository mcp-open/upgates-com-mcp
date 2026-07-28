"""`connector.yaml` musí být platný manifest podle `openmcp_sdk.manifest`
a jeho display.tools se nesmí rozejít s reálně zaregistrovanými nástroji."""

from __future__ import annotations

import asyncio
from pathlib import Path

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


def test_display_tools_match_registered_tools() -> None:
    """`display.tools` je to, co katalog ukazuje — nesmí se rozejít s realitou."""
    from connector import server

    manifest = load_manifest(str(MANIFEST_PATH))
    display_names = {t.name for t in manifest.display.tools}
    registered = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    assert display_names == registered
