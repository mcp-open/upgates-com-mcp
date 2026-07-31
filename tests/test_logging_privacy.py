"""Filtry nástrojů nesmí protéct do logu.

`list_orders`/`list_customers` berou e-mail a telefon zákazníka jako query
parametry. httpx loguje celou URL požadavku na úrovni INFO, na které konektor
běžně běží — dokud SDK httpx neztišilo, končil zákaznický e-mail i telefon
ve strukturovaném stdout logu konektoru (a tedy ve sběrači logů).
"""

from __future__ import annotations

import io
import logging

import httpx
import pytest

from openmcp_sdk.http import UpstreamClient
from openmcp_sdk.logging import setup


@pytest.fixture
def captured_log():
    setup(level="INFO", component="upgates")
    buffer = io.StringIO()
    handler = logging.getLogger().handlers[0]
    original, handler.stream = handler.stream, buffer
    try:
        yield buffer
    finally:
        handler.stream = original


def test_query_filters_never_reach_the_log(captured_log):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"orders": []}))
    client = UpstreamClient(
        base_url="https://acme.admin.s17.upgates.com/api/v2",
        auth=("login", "key"),
        transport=transport,
    )
    try:
        client.get_json("/orders", {"email": "jan.novak@example.cz", "phone": "+420777123456"})
    finally:
        client.close()

    logged = captured_log.getvalue()
    assert "jan.novak" not in logged
    assert "example.cz" not in logged
    assert "420777123456" not in logged
    # Ani v percent-encoded podobě, ve které je httpx skládá do URL.
    assert "%40" not in logged
    assert "%2B420" not in logged


def test_transport_failures_are_still_logged(captured_log):
    """Ztišení httpx nesmí umlčet diagnostiku selhání."""
    logging.getLogger("httpx").warning("HTTP Request failed")
    assert "HTTP Request failed" in captured_log.getvalue()
