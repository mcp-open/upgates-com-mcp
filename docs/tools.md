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

Aby se nezaplnilo kontextové okno modelu, konektor ořezává výpisy na strop
`MAX_ITEMS_FOR_MCP` — viz [`defaults.md`](defaults.md). Týká se to **jen
optimalizovaných entit**:

| Nástroj | |
|---|---|
| `list_orders`, `list_invoices` | objednávky a faktury |
| `list_products`, `list_categories` | produkty a kategorie |
| `list_customers`, `list_carts` | zákazníci a košíky |
| `list_shipments`, `list_payments` | doprava a platby |

Ostatní nástroje (`list_products_simple`, `list_order_statuses`, `list_labels`,
`list_availabilities`, `list_manufacturers`, `list_parameters`,
`list_vouchers`, `list_webhooks`, `list_webhook_events`, `list_pricelists`,
`get_*`) vracejí odpověď tak, jak přišla — neořezávají se a pole
`mcp_truncated`/`mcp_note` v jejich odpovědi nejsou.

U optimalizovaných entit se oříznutí vždy ohlásí, nikdy se nestane tiše:
odpověď nese boolean `mcp_truncated` a slovní `mcp_note`.

**Oříznuté položky `page` nevrátí.** Ořezává se až uvnitř jedné upstream
stránky, takže položky nad strop `MAX_ITEMS_FOR_MCP` nejsou na žádné další
stránce — `page` přeskočí na následující upstream stránku, ne na zbytek té
současné. Když jsou potřeba, je jediná funkční cesta zúžit filtry (datum,
stav, kód, jazyk). Odpověď to říká i modelu přímo v `mcp_note`.
