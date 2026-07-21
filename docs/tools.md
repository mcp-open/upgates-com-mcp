# Dostupné nástroje (23)

Zoznam zodpovedá `display.tools` v `connector.yaml` a skutočne zaregistrovaným
nástrojom v `src/connector/server.py` — zhodu stráži test.

**Všetky nástroje sú iba na čítanie.** Konektor nezapisuje ani nemaže dáta;
`egress.methods` v manifeste povoľuje výhradne `GET`.

> Predchádzajúca verzia tohto dokumentu popisovala 34 nástrojov vrátane
> zapisovacích (`create_order`, `update_orders`, `delete_orders`). Tie
> pochádzali z pôvodnej TypeScript implementácie a v Python konektore
> **neexistujú**.

## Objednávky a faktúry

| Nástroj | Popis |
|---|---|
| `list_orders` | Zoznam objednávok s filtrami a stránkovaním — zákaznícke dáta sú pseudonymizované |
| `get_order_history` | História konkrétnej objednávky |
| `list_order_statuses` | Zoznam stavov objednávok |
| `list_invoices` | Zoznam faktúr — zákaznícke dáta sú pseudonymizované |

## Produkty a katalóg

| Nástroj | Popis |
|---|---|
| `list_products` | Zoznam produktov s filtrami a stránkovaním |
| `list_products_simple` | Zoznam produktov v zjednodušenom formáte |
| `list_categories` | Zoznam kategórií |
| `list_labels` | Zoznam produktových štítkov |
| `list_availabilities` | Zoznam dostupností produktov |
| `list_manufacturers` | Zoznam výrobcov |
| `list_parameters` | Zoznam produktových parametrov |
| `list_pricelists` | Zoznam cenníkov |

Katalógové dáta sa **nepseudonymizujú** — nie sú to osobné údaje a bez nich by
konektor stratil zmysel.

## Zákazníci a košíky

| Nástroj | Popis |
|---|---|
| `list_customers` | Zoznam zákazníkov — osobné údaje sú pseudonymizované |
| `list_carts` | Zoznam košíkov — zákaznícke dáta sú pseudonymizované |

## Doprava, platby, zľavy

| Nástroj | Popis |
|---|---|
| `list_shipments` | Zoznam spôsobov dopravy |
| `list_payments` | Zoznam platobných metód |
| `list_vouchers` | Zoznam zľavových kupónov |

## E-shop a webhooky

| Nástroj | Popis |
|---|---|
| `get_shop_config` | Konfigurácia a nastavenia e-shopu |
| `get_shop_owner` | Fakturačné údaje prevádzkovateľa (pseudonymizované) |
| `get_languages` | Jazyky e-shopu |
| `list_webhooks` | Zoznam nakonfigurovaných webhookov |
| `list_webhook_events` | Zoznam dostupných webhook udalostí |
| `get_api_status` | Stav API a zoznam povolených endpointov pre aktuálneho používateľa |

## Limity

Odpovede sú orezané, aby sa nezaplnilo kontextové okno modelu — viď
[`defaults.md`](defaults.md). Orezanie sa vždy ohlási, nikdy sa nestane ticho.
