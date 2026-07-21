"""Optimalizace odpovědí Upgates pro kontextové okno LLM.

Věrný port `optimizers/index.ts`: z bohatých objektů Upgates API vybere jen
podstatná pole a omezí počet položek na stránce (``MAX_ITEMS_FOR_MCP``), aby
odpověď nepřekročila token limit MCP. Katalogová i zákaznická data se tvarují
stejně jako v TS; pseudonymizace (`openmcp_sdk.pii` + `connector.pii_fields`) běží až NAD výstupem
těchto funkcí (stejné pořadí jako TS: optimize → anonymize).
"""

from __future__ import annotations

from typing import Any

# Maximální počet položek na stránku ve výstupu (drží odpověď pod ~25k tokeny).
MAX_ITEMS_FOR_MCP = 15


def _first(seq: Any) -> dict[str, Any]:
    """První prvek seznamu jako dict, nebo prázdný dict (bezpečné `?.[0]`)."""
    if isinstance(seq, list) and seq and isinstance(seq[0], dict):
        return seq[0]
    return {}


def optimize_order(order: dict[str, Any]) -> dict[str, Any]:
    order = order or {}
    customer = order.get("customer")
    products = order.get("products") or []
    shipment = order.get("shipment")
    payment = order.get("payment")
    return {
        "order_number": order.get("order_number"),
        "status": order.get("status"),
        "status_id": order.get("status_id"),
        "creation_time": order.get("creation_time"),
        "paid_yn": bool(order.get("paid_date")),
        "paid_date": order.get("paid_date"),
        "order_total": order.get("order_total"),
        "currency_id": order.get("currency_id"),
        "language_id": order.get("language_id"),
        "tracking_code": order.get("tracking_code"),
        "external_order_number": order.get("external_order_number"),
        "customer": {
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "firstname_invoice": customer.get("firstname_invoice"),
            "surname_invoice": customer.get("surname_invoice"),
            "company": customer.get("company"),
            "customer_note": customer.get("customer_note"),
        }
        if isinstance(customer, dict)
        else None,
        "products_count": len(products) if isinstance(products, list) else 0,
        "products_summary": [
            {
                "code": p.get("code"),
                "title": p.get("title"),
                "quantity": p.get("quantity"),
                "price": p.get("price"),
            }
            for p in products
            if isinstance(p, dict)
        ]
        if isinstance(products, list)
        else [],
        "shipment": {
            "name": shipment.get("name"),
            "type": shipment.get("type"),
            "price": shipment.get("price"),
            "affiliate_name": shipment.get("affiliate_name"),
        }
        if isinstance(shipment, dict)
        else None,
        "payment": {
            "name": payment.get("name"),
            "type": payment.get("type"),
            "price": payment.get("price"),
        }
        if isinstance(payment, dict)
        else None,
    }


def optimize_product(product: dict[str, Any]) -> dict[str, Any]:
    product = product or {}
    desc = _first(product.get("descriptions"))
    prices = product.get("prices") or []
    price0 = _first(prices)
    pricelist0 = _first(price0.get("pricelists"))
    categories = product.get("categories") or []
    main_category = None
    if isinstance(categories, list):
        main = next((c for c in categories if isinstance(c, dict) and c.get("main_yn")), None)
        main_category = (main or _first(categories)).get("code")
    variants = product.get("variants") or []
    return {
        "product_id": product.get("product_id"),
        "code": product.get("code"),
        "active_yn": product.get("active_yn"),
        "can_add_to_basket_yn": product.get("can_add_to_basket_yn"),
        "stock": product.get("stock"),
        "availability": product.get("availability"),
        "manufacturer": product.get("manufacturer"),
        "title": desc.get("title"),
        "url": desc.get("url"),
        "price_with_vat": pricelist0.get("price_with_vat"),
        "price_without_vat": pricelist0.get("price_without_vat"),
        "currency": price0.get("currency"),
        "main_category": main_category,
        "variants_count": len(variants) if isinstance(variants, list) else 0,
    }


def optimize_customer(customer: dict[str, Any]) -> dict[str, Any]:
    customer = customer or {}
    company = customer.get("company")
    login = customer.get("login") or {}
    return {
        "customer_id": customer.get("customer_id"),
        "email": customer.get("email"),
        "type": customer.get("type"),
        "firstname": customer.get("firstname"),
        "surname": customer.get("surname"),
        "company": company.get("name") if isinstance(company, dict) else None,
        "active_yn": login.get("active_yn") if isinstance(login, dict) else None,
        "blocked_yn": login.get("blocked_yn") if isinstance(login, dict) else None,
        "language": customer.get("language"),
        "pricelist": customer.get("pricelist"),
        "turnover": customer.get("turnover"),
        "turnover_currency": customer.get("turnover_currency"),
    }


def optimize_invoice(invoice: dict[str, Any]) -> dict[str, Any]:
    invoice = invoice or {}
    customer = invoice.get("customer") or {}
    return {
        "invoice_number": invoice.get("invoice_number"),
        "order_number": invoice.get("order_number"),
        "type": invoice.get("type"),
        "date_of_issuance": invoice.get("date_of_issuance"),
        "date_of_expiration": invoice.get("date_of_expiration"),
        "paid_yn": invoice.get("paid_yn"),
        "paid_date": invoice.get("paid_date"),
        "total_with_vat": invoice.get("total_with_vat"),
        "currency_id": invoice.get("currency_id"),
        "variable_symbol": invoice.get("variable_symbol"),
        "customer_email": customer.get("email") if isinstance(customer, dict) else None,
    }


def optimize_category(category: dict[str, Any]) -> dict[str, Any]:
    category = category or {}
    desc = _first(category.get("descriptions"))
    return {
        "category_id": category.get("category_id"),
        "code": category.get("code"),
        "parent_id": category.get("parent_id"),
        "active_yn": category.get("active_yn"),
        "type": category.get("type"),
        "name": desc.get("name"),
        "url": desc.get("url"),
    }


def optimize_cart(cart: dict[str, Any]) -> dict[str, Any]:
    cart = cart or {}
    customer = cart.get("customer") or {}
    products = cart.get("products") or []
    shipment = cart.get("shipment") or {}
    payment = cart.get("payment") or {}
    return {
        "id": cart.get("id"),
        "uuid": cart.get("uuid"),
        "datetime": cart.get("datetime"),
        "language": cart.get("language"),
        "customer_email": customer.get("email") if isinstance(customer, dict) else None,
        "customer_logged_in_yn": customer.get("customer_logged_in_yn")
        if isinstance(customer, dict)
        else None,
        "filled_delivery_info_yn": customer.get("filled_delivery_info_yn")
        if isinstance(customer, dict)
        else None,
        "products_count": len(products) if isinstance(products, list) else 0,
        "products_summary": [
            {"code": p.get("code"), "quantity": p.get("quantity")}
            for p in products
            if isinstance(p, dict)
        ]
        if isinstance(products, list)
        else [],
        "shipment_name": shipment.get("name") if isinstance(shipment, dict) else None,
        "payment_name": payment.get("name") if isinstance(payment, dict) else None,
    }


def optimize_payment(payment: dict[str, Any]) -> dict[str, Any]:
    payment = payment or {}
    desc = _first(payment.get("descriptions"))
    return {
        "id": payment.get("id"),
        "code": payment.get("code"),
        "type": payment.get("type"),
        "active_yn": payment.get("active_yn"),
        "name": desc.get("name"),
        "description": desc.get("description"),
        "price": desc.get("price"),
        "price_type": desc.get("price_type"),
        "free_from": desc.get("free_from"),
    }


def optimize_shipment(shipment: dict[str, Any]) -> dict[str, Any]:
    shipment = shipment or {}
    desc = _first(shipment.get("descriptions"))
    return {
        "id": shipment.get("id"),
        "code": shipment.get("code"),
        "type": shipment.get("type"),
        "active_yn": shipment.get("active_yn"),
        "affiliates": shipment.get("affiliates"),
        "name": desc.get("name"),
        "description": desc.get("description"),
        "price": desc.get("price"),
        "free_from": desc.get("free_from"),
    }


# Mapa typu entity → (klíč seznamu, optimalizační funkce).
_ENTITY_OPTIMIZERS = {
    "orders": ("orders", optimize_order),
    "products": ("products", optimize_product),
    "customers": ("customers", optimize_customer),
    "invoices": ("invoices", optimize_invoice),
    "categories": ("categories", optimize_category),
    "carts": ("carts", optimize_cart),
    "payments": ("payments", optimize_payment),
    "shipments": ("shipments", optimize_shipment),
}


def optimize_list_response(
    data: Any, entity_type: str, max_items: int = MAX_ITEMS_FOR_MCP
) -> Any:
    """Aplikuj entity-specific optimalizaci s omezením počtu položek.

    Pro jednoduché entity (order_statuses, labels, availabilities, …) vrací data
    beze změny — jsou malá a už optimalizovaná (stejné chování jako TS default).
    """
    if not data:
        return data
    mapping = _ENTITY_OPTIMIZERS.get(entity_type)
    if mapping is None or not isinstance(data, dict):
        return data

    list_key, optimizer = mapping
    items = data.get(list_key) or []
    if not isinstance(items, list):
        items = []
    optimized_items = [optimizer(item) for item in items[:max_items] if isinstance(item, dict)]

    return {
        "current_page": data.get("current_page"),
        "number_of_pages": data.get("number_of_pages"),
        "number_of_items": data.get("number_of_items"),
        "mcp_limited_to": max_items,
        "mcp_note": (
            f"Zobrazeno prvních {max_items} z {data.get('current_page_items')} položek na "
            "této stránce. Pro zobrazení dalších použij parametr page."
        ),
        list_key: optimized_items,
        "current_page_items": len(optimized_items),
    }
