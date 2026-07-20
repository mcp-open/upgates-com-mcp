"""Validace vstupů z LLM (port podmnožiny `validators/index.ts` používané handlery).

Selhání vrací `ConnectorError(INVALID_INPUT, …)` — čitelná byznys chyba, na
kterou má uživatel/model šanci zareagovat, ne 500.
"""

from __future__ import annotations

import re

from openmcp_sdk import ConnectorError, ErrorCode

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date_format(value: str, field_name: str = "date") -> None:
    if not _DATE_RE.match(value):
        raise ConnectorError(
            ErrorCode.INVALID_INPUT,
            f"Neplatný formát data u {field_name}. Očekává se YYYY-MM-DD, dostal jsem: {value}",
        )


def validate_date_range(date_from: str | None, date_to: str | None) -> None:
    if date_from:
        validate_date_format(date_from, "creation_time_from")
    if date_to:
        validate_date_format(date_to, "creation_time_to")
    if date_from and date_to and date_from > date_to:
        raise ConnectorError(
            ErrorCode.INVALID_INPUT,
            "creation_time_from musí být před nebo rovno creation_time_to.",
        )


def validate_page(page: int | None) -> None:
    if page is not None and page < 1:
        raise ConnectorError(
            ErrorCode.INVALID_INPUT, f"page musí být >= 1, dostal jsem: {page}"
        )
