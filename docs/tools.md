# Dostupné nástroje (23)

Seznam odpovídá `display.tools` v `connector.yaml` a skutečně zaregistrovaným
nástrojům v `src/connector/server.py` — shodu hlídá test.

**Všechny nástroje jsou pouze pro čtení.** Konektor nezapisuje ani nemaže data;
`egress.methods` v manifestu povoluje výhradně `GET`.

> Předchozí verze tohoto dokumentu popisovala 34 nástrojů včetně
> zapisovacích (`create_order`, `update_orders`, `delete_orders`). Ty
> pocházely z původní TypeScript implementace a v Python konektoru
> **neexistují**.

## Objednávky a faktury

| Nástroj | Popis |
|---|---|
| `list_orders` | Seznam objednávek s filtry a stránkováním — zákaznická data jsou pseudonymizovaná |
| `get_order_history` | Historie konkrétní objednávky |
| `list_order_statuses` | Seznam stavů objednávek |
| `list_invoices` | Seznam faktur — zákaznická data jsou pseudonymizovaná |

## Produkty a katalog

| Nástroj | Popis |
|---|---|
| `list_products` | Seznam produktů s filtry a stránkováním |
| `list_products_simple` | Seznam produktů ve zjednodušeném formátu |
| `list_categories` | Seznam kategorií |
| `list_labels` | Seznam produktových štítků |
| `list_availabilities` | Seznam dostupností produktů |
| `list_manufacturers` | Seznam výrobců |
| `list_parameters` | Seznam produktových parametrů |
| `list_pricelists` | Seznam ceníků |

Katalogová data se **nepseudonymizují** — nejsou to osobní údaje a bez nich by
konektor ztratil smysl.

## Zákazníci a košíky

| Nástroj | Popis |
|---|---|
| `list_customers` | Seznam zákazníků — osobní údaje jsou pseudonymizované |
| `list_carts` | Seznam košíků — zákaznická data jsou pseudonymizovaná |

## Doprava, platby, slevy

| Nástroj | Popis |
|---|---|
| `list_shipments` | Seznam způsobů dopravy |
| `list_payments` | Seznam platebních metod |
| `list_vouchers` | Seznam slevových kupónů |

## E-shop a webhooky

| Nástroj | Popis |
|---|---|
| `get_shop_config` | Konfigurace a nastavení e-shopu |
| `get_shop_owner` | Fakturační údaje provozovatele (pseudonymizované) |
| `get_languages` | Jazyky e-shopu |
| `list_webhooks` | Seznam nakonfigurovaných webhooků |
| `list_webhook_events` | Seznam dostupných webhook událostí |
| `get_api_status` | Stav API a seznam povolených endpointů pro aktuálního uživatele |

## Limity

Odpovědi jsou oříznuté, aby se nezaplnilo kontextové okno modelu — viz
[`defaults.md`](defaults.md). Oříznutí se vždy ohlásí, nikdy se nestane tiše.
