"""Regresní testy `connector.optimizers`.

Pokrývají dvě třídy chyb, které měl port z TypeScriptu:

* **tichá ztráta dat** — payload, který není stránka seznamu, se měnil na
  prázdnou stránku;
* **nepravdivá poznámka o oříznutí** — `mcp_note` hlásil oříznutí, které se
  nestalo, a počty, které konektor nikdy neviděl;

a dvě nesouhlasící mapování polí proti reálnému schématu Upgates API v2
(cena/měna produktu, e-mail zákazníka).
"""

from __future__ import annotations

import pytest

from connector.optimizers import (
    MAX_ITEMS_FOR_MCP,
    optimize_customer,
    optimize_list_response,
    optimize_product,
)


# --- tichá ztráta dat --------------------------------------------------------
def test_record_detail_payload_survives_untouched():
    """`/orders/{order_number}` vrací jeden záznam, ne stránku seznamu.

    Dřív z něj optimalizace udělala `{"orders": [], "current_page_items": 0}` —
    model tedy na dotaz po konkrétní objednávce dostal „nic tu není".
    """
    detail = {"order_number": "ORD-1", "order_total": 1234, "customer": {"email": "a@b.cz"}}
    assert optimize_list_response(detail, "orders") == detail


def test_non_list_under_the_entity_key_is_not_flattened_to_zero():
    payload = {"orders": {"order_number": "ORD-1"}}
    assert optimize_list_response(payload, "orders") == payload


def test_non_dict_item_is_passed_through_not_dropped():
    """Neslovníková položka se nedá optimalizovat, ale zahodit ji je ztráta dat."""
    page = {"orders": [{"order_number": "1"}, "nečekaný-string"]}
    out = optimize_list_response(page, "orders")
    assert len(out["orders"]) == 2
    assert out["orders"][1] == "nečekaný-string"
    assert out["current_page_items"] == 2


# --- pravdivé hlášení oříznutí ----------------------------------------------
def test_note_does_not_claim_truncation_that_did_not_happen():
    page = {"current_page_items": 3, "orders": [{"order_number": str(i)} for i in range(3)]}
    out = optimize_list_response(page, "orders")
    assert out["current_page_items"] == 3
    assert out["mcp_truncated"] is False
    assert "všech 3" in out["mcp_note"]


def test_note_reports_real_counts_when_truncating():
    page = {"orders": [{"order_number": str(i)} for i in range(20)]}
    out = optimize_list_response(page, "orders")
    assert out["current_page_items"] == MAX_ITEMS_FOR_MCP
    assert out["mcp_truncated"] is True
    assert f"prvních {MAX_ITEMS_FOR_MCP} z 20" in out["mcp_note"]


def test_truncation_note_does_not_promise_page_recovers_the_omitted_items():
    """Ořezává se uvnitř jedné upstream stránky.

    Položky 16..N z téže stránky nejsou na žádné další stránce — `page=2`
    přeskočí na následující upstream stránku. Rada „použij page" tedy modelu
    slibovala data, která tou cestou nezíská; jediná funkční cesta je zúžit
    filtry.
    """
    page = {"current_page": 1, "number_of_pages": 4, "orders": [{"o": i} for i in range(20)]}
    out = optimize_list_response(page, "orders")
    note = out["mcp_note"]
    assert "5 vynechaných" in note
    assert "nezískáš" in note
    assert "filtry" in note
    assert "Další stránku" not in note


def test_next_page_is_offered_only_when_one_exists():
    last = {"current_page": 4, "number_of_pages": 4, "orders": [{"o": 1}]}
    assert "Další stránku" not in optimize_list_response(last, "orders")["mcp_note"]

    more = {"current_page": 1, "number_of_pages": 4, "orders": [{"o": 1}]}
    note = optimize_list_response(more, "orders")["mcp_note"]
    assert "Další stránku (2 z 4)" in note


def test_next_page_not_offered_when_upstream_omits_pagination():
    out = optimize_list_response({"orders": [{"o": 1}]}, "orders")
    assert out["mcp_truncated"] is False
    assert "Další stránku" not in out["mcp_note"]


@pytest.mark.parametrize("entity", ["orders", "products", "customers", "invoices"])
def test_truncated_flag_is_always_present(entity):
    out = optimize_list_response({entity: [{"x": 1}]}, entity)
    assert out["mcp_truncated"] is False


@pytest.mark.parametrize("entity", ["orders", "products", "customers", "invoices"])
def test_note_never_prints_none_when_upstream_omits_the_count(entity):
    """Upstream nemusí poslat `current_page_items` — hláška se o něj neopírá."""
    page = {entity: [{"code": "X"}]}
    out = optimize_list_response(page, entity)
    assert "None" not in out["mcp_note"]


def test_pagination_metadata_from_upstream_is_preserved():
    page = {
        "current_page": 2,
        "number_of_pages": 7,
        "number_of_items": 101,
        "orders": [{"order_number": "1"}],
    }
    out = optimize_list_response(page, "orders")
    assert (out["current_page"], out["number_of_pages"], out["number_of_items"]) == (2, 7, 101)


# --- schéma Upgates v2 -------------------------------------------------------
def test_product_price_uses_the_documented_upgates_schema():
    """`prices[]` a `prices[].pricelists[]` mají jen tahle pole.

    Původní port (věrný TS originálu) četl `price_with_vat`,
    `price_without_vat` a `currency` — ta ve schématu Upgates v2 vůbec nejsou,
    takže cena produktu vycházela vždy `None`.
    """
    out = optimize_product(
        {
            "code": "P1",
            "prices": [
                {
                    "language": "cs",
                    "price_purchase": 60,
                    "price_common": 120,
                    "vat": 21,
                    "recycling_fee": 5,
                    "pricelists": [
                        {
                            "name": "Výchozí",
                            "price_original": 120,
                            "product_discount": 10,
                            "price_sale": 108,
                        }
                    ],
                }
            ],
        }
    )
    assert out["language"] == "cs"
    assert out["price_purchase"] == 60
    assert out["price_common"] == 120
    assert out["vat"] == 21
    assert out["recycling_fee"] == 5
    assert out["pricelist_name"] == "Výchozí"
    assert out["price_original"] == 120
    assert out["product_discount"] == 10
    assert out["price_sale"] == 108


def test_product_output_has_no_invented_price_fields():
    """Nevymýšlet dopočtená pole — `vat` je sazba, ne částka."""
    out = optimize_product({"code": "P1", "prices": [{"price_common": 120, "vat": 21}]})
    for invented in ("price_with_vat", "price_without_vat", "currency"):
        assert invented not in out


def test_product_without_pricelists_still_reports_the_price_entry():
    out = optimize_product({"code": "P1", "prices": [{"price_common": 99, "vat": 21}]})
    assert out["price_common"] == 99
    assert out["vat"] == 21
    assert out["price_sale"] is None


def test_customer_email_is_read_from_the_login_object():
    """E-mail zákazníka je v Upgates v2 přihlašovací údaj (`login.email`).

    Původní port ho četl jen z kořene objektu a vracel `None` u každého
    zákazníka — `list_customers` tedy nikdy neukázal e-mail.
    """
    out = optimize_customer(
        {
            "customer_id": 5,
            "login": {"email": "jan@example.cz", "active_yn": True, "blocked_yn": False},
        }
    )
    assert out["email"] == "jan@example.cz"
    assert out["active_yn"] is True
    assert out["blocked_yn"] is False


def test_customer_email_in_the_root_still_wins():
    out = optimize_customer({"email": "root@example.cz", "login": {"email": "login@example.cz"}})
    assert out["email"] == "root@example.cz"
