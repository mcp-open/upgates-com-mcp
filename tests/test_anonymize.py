"""Testy GDPR pseudonymizace — stabilita tokenů, izolace tenantů, pokrytí polí."""

from __future__ import annotations

import pytest

from openmcp_sdk.pii import TOKEN_RE, Pseudonymizer, derive_key, require_salt

from connector.pii_fields import POLICY


def _pseudo(sub: str = "shop-1") -> Pseudonymizer:
    return Pseudonymizer(derive_key(sub), POLICY)


def test_require_salt_missing_raises(monkeypatch):
    monkeypatch.delenv("OPENMCP_PII_SALT", raising=False)
    with pytest.raises(RuntimeError, match="OPENMCP_PII_SALT"):
        require_salt()


def test_email_and_phone_tokenized():
    out = _pseudo().sanitize({"email": "jan@example.cz", "phone": "+420777123456"})
    assert out["email"].startswith("<EMAIL_")
    assert out["phone"].startswith("<PHONE_")
    assert out["email"] != "jan@example.cz"


def test_names_and_address_tokenized():
    out = _pseudo().sanitize(
        {"firstname": "Jan", "surname": "Novák", "city": "Praha", "street": "Dlouhá 5", "zip": "11000"}
    )
    assert out["firstname"].startswith("<NAME_")
    assert out["surname"].startswith("<NAME_")
    assert out["city"].startswith("<ADDR_")
    assert out["street"].startswith("<ADDR_")
    assert out["zip"].startswith("<ADDR_")


def test_business_ids_and_bank_tokenized():
    out = _pseudo().sanitize(
        {"ico": "12345678", "dic": "CZ12345678", "iban": "CZ65", "variable_symbol": "2024001"}
    )
    assert out["ico"].startswith("<REGNUM_")
    assert out["dic"].startswith("<TAXNUM_")
    assert out["iban"].startswith("<BANK_")
    assert out["variable_symbol"].startswith("<BANK_")


def test_pattern_fallback_for_unknown_field():
    # `delivery_name` není v explicitní mapě, ale substring "name" ho chytí.
    out = _pseudo().sanitize({"delivery_name": "Jan Novák", "affiliate_name": "PPL depo"})
    assert out["delivery_name"].startswith("<NAME_")
    assert out["affiliate_name"].startswith("<NAME_")


def test_catalog_code_not_tokenized():
    # Katalogový `code` (kód produktu) se NEtokenizuje — LLM ho potřebuje.
    out = _pseudo().sanitize({"code": "PROD-123", "customer_code": "CUST-9"})
    assert out["code"] == "PROD-123"
    assert out["customer_code"].startswith("<CUSTCODE_")


def test_freetext_note_scrubbed_not_fully_masked():
    out = _pseudo().sanitize({"customer_note": "Volejte na +420777123456, dík. Doručit v pátek."})
    assert "+420777123456" not in out["customer_note"]
    assert "Doručit v pátek" in out["customer_note"]  # obchodní kontext zůstane


def test_stable_tokens_same_value_same_token():
    p = _pseudo()
    a = p.sanitize({"email": "jan@example.cz"})["email"]
    b = p.sanitize({"customer_email": "jan@example.cz"})["customer_email"]
    assert a == b  # stejná hodnota → stejný token napříč poli


def test_tenant_isolation_different_sub_different_token():
    a = _pseudo("shop-1").sanitize({"email": "jan@example.cz"})["email"]
    b = _pseudo("shop-2").sanitize({"email": "jan@example.cz"})["email"]
    assert a != b


def test_nested_and_list_structures():
    data = {
        "orders": [
            {"customer": {"email": "a@b.cz", "firstname_invoice": "Eva"}, "order_total": 100},
        ]
    }
    out = _pseudo().sanitize(data)
    cust = out["orders"][0]["customer"]
    assert cust["email"].startswith("<EMAIL_")
    assert cust["firstname_invoice"].startswith("<NAME_")
    assert out["orders"][0]["order_total"] == 100  # nesenzitivní projde


def test_token_shape_matches_regex():
    out = _pseudo().sanitize({"email": "jan@example.cz"})
    assert TOKEN_RE.fullmatch(out["email"])


def test_bool_and_none_pass_through():
    out = _pseudo().sanitize({"active_yn": True, "name": None, "phone": ""})
    assert out["active_yn"] is True
    assert out["name"] is None
    assert out["phone"] == ""


def test_golden_tokens_bit_identical_to_pre_sdk_migration(monkeypatch):
    """Zafixované tokeny spočítané starým `connector.anonymize` (před přechodem
    na `openmcp_sdk.pii`) se saltem ``test-golden-salt`` a ``sub="shop-1"``.

    Token je externě viditelný, dlouhodobě stabilní kontrakt — migrace na
    sdílený SDK modul ho nesmí změnit ani o bit, jinak uživatel uvidí najednou
    jiné ID pro stejný záznam.
    """
    monkeypatch.setenv("OPENMCP_PII_SALT", "test-golden-salt")
    sample = {
        "email": "jan@example.cz",
        "firstname": "Jan",
        "surname": "Novák",
        "city": "Praha",
        "street": "Dlouhá 5",
        "zip": "11000",
        "ico": "12345678",
        "dic": "CZ12345678",
        "iban": "CZ65",
        "variable_symbol": "2024001",
        "delivery_name": "Jan Novák",
        "code": "PROD-123",
        "customer_code": "CUST-9",
        "customer_note": "Volejte na +420777123456, dík. Doručit v pátek.",
        "phone": "+420777123456",
    }
    out = Pseudonymizer(derive_key("shop-1"), POLICY).sanitize(sample)
    assert out == {
        "email": "<EMAIL_ca7217dca4cb>",
        "firstname": "<NAME_e3c4b2a245be>",
        "surname": "<NAME_9b4f81cdcad1>",
        "city": "<ADDR_490961abb91c>",
        "street": "<ADDR_e771b466b42b>",
        "zip": "<ADDR_af66925845bb>",
        "ico": "<REGNUM_48a4bfe88473>",
        "dic": "<TAXNUM_c879d42c666b>",
        "iban": "<BANK_c38bfdc3ce93>",
        "variable_symbol": "<BANK_441db0044338>",
        "delivery_name": "<NAME_172b9e8db6f3>",
        "code": "PROD-123",
        "customer_code": "<CUSTCODE_4cc820d3186a>",
        "customer_note": "Volejte na <PHONE_5d7d27642430>, dík. Doručit v pátek.",
        "phone": "<PHONE_5d7d27642430>",
    }
