"""Mapy PII polí pro Upgates e-shop API — nula logiky.

Tokenizace, scrub volného textu a odvození klíče žijí v ``openmcp_sdk.pii``.
Tenhle soubor nese jen to, co je specifické pro Upgates schéma: která pole
jsou osobní údaj a jaké kategorii odpovídají.

Port `sensitiveFields`/`anonymizeByPattern` z `upgates-client.ts` (viz historie
repa před přechodem na `openmcp_sdk`).
"""

from __future__ import annotations

from types import MappingProxyType

from openmcp_sdk.pii import PiiPolicy

# --- Názvy koncových polí → kategorie tokenu (case-insensitive) ---------------
FIELD_CATEGORY: dict[str, str] = {
    # e-mail
    "email": "EMAIL",
    "customer_email": "EMAIL",
    "vendoremail": "EMAIL",
    # telefon
    "phone": "PHONE",
    "phonenumber": "PHONE",
    "phone_number": "PHONE",
    "fax": "PHONE",
    # jména osob
    "firstname": "NAME",
    "surname": "NAME",
    "firstname_invoice": "NAME",
    "surname_invoice": "NAME",
    "firstname_postal": "NAME",
    "surname_postal": "NAME",
    "customer_name": "NAME",
    "name": "NAME",
    "nickname": "NAME",
    "degree": "NAME",
    "salutation": "NAME",
    "declension": "NAME",
    # firma
    "company": "COMPANY",
    "company_name": "COMPANY",
    "company_postal": "COMPANY",
    # adresa
    "street": "ADDR",
    "street_invoice": "ADDR",
    "street_postal": "ADDR",
    "city": "ADDR",
    "city_invoice": "ADDR",
    "city_postal": "ADDR",
    "state": "ADDR",
    "state_invoice": "ADDR",
    "state_postal": "ADDR",
    "zip": "ADDR",
    "zip_invoice": "ADDR",
    "zip_postal": "ADDR",
    "zip_code": "ADDR",
    "address": "ADDR",
    # firemní identifikátory
    "ico": "REGNUM",
    "company_number": "REGNUM",
    "dic": "TAXNUM",
    "vat_number": "TAXNUM",
    # identifikátor zákazníka
    "customer_code": "CUSTCODE",
    # ostatní kontakt
    "im": "CONTACT",
    # bankovní spojení
    "bank_account": "BANK",
    "account_number": "BANK",
    "iban": "BANK",
    "swift": "BANK",
    "specific_symbol": "BANK",
    "variable_symbol": "BANK",
}

# Volnotextová pole — jen scrub vnořených e-mailů/telefonů/URL, zbytek ponech.
FREETEXT_FIELDS = frozenset({"customer_note", "internal_note", "note"})

# Substringové vzory z `anonymizeByPattern` v upgates-client.ts. Fail-closed
# fallback pro nevyjmenovaná pole (custom fields, *_invoice/*_postal varianty).
PATTERN_CATEGORY: tuple[tuple[str, str], ...] = (
    ("email", "EMAIL"),
    ("phone", "PHONE"),
    ("street", "ADDR"),
    ("address", "ADDR"),
    ("city", "ADDR"),
    ("zip", "ADDR"),
    ("name", "NAME"),
)

# Katalogové `code` (kód produktu/dopravy/platby) se NEtokenizuje — je to
# identifikátor katalogu, ne osobní údaj, a LLM ho potřebuje na odkazování
# produktů v objednávce. `customer_code` (identifikátor zákazníka) v
# FIELD_CATEGORY zůstává a tokenizuje se dál.
POLICY = PiiPolicy(
    field_category=MappingProxyType(FIELD_CATEGORY),
    freetext_fields=FREETEXT_FIELDS,
    pattern_category=PATTERN_CATEGORY,
)
