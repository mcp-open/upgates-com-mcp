# upgates-com-mcp

MCP konektor pro **Upgates** e-shop API v2. Čtecí přístup k objednávkám,
fakturám, produktům, zákazníkům a konfiguraci e-shopu s pseudonymizací
osobních údajů.

Součást platformy [OpenMCP.cz](https://openmcp.cz).

> **Poznámka k historii:** konektor původně vznikl v TypeScriptu. Od
> `a8f71aa` (7/2026) je implementován v Pythonu nad `openmcp-sdk`; TS strom
> byl odstraněn a je dohledatelný v git historii.

## Rychlý start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ../openmcp-sdk -e .
export OPENMCP_MODE=local-stdio
export UPGATES_API_URL="https://vas-eshop.admin.server.upgates.com/api/v2"
export UPGATES_API_LOGIN="api-login"
export UPGATES_API_KEY="api-klic"
export OPENMCP_PII_SALT="$(openssl rand -hex 32)"
python -m connector
```

API přístup se zakládá v **Upgates Admin → Doplňky → API**.

`OPENMCP_PII_SALT` je povinný — bez něj konektor záměrně nenastartuje. Tichý
fallback na náhodný salt by zrušil stabilitu pseudonymizačních tokenů
a projevilo by se to až po restartu.

## Nástroje (23)

Všechny jsou **pouze ke čtení**; konektor nezapisuje ani nemaže.

| Oblast | Nástroje |
|---|---|
| Objednávky | `list_orders`, `get_order_history`, `list_order_statuses` |
| Faktury | `list_invoices` |
| Produkty | `list_products`, `list_products_simple`, `list_categories`, `list_labels`, `list_availabilities`, `list_manufacturers`, `list_parameters`, `list_pricelists` |
| Zákazníci | `list_customers`, `list_carts` |
| Doprava a platby | `list_shipments`, `list_payments`, `list_vouchers` |
| E-shop | `get_shop_config`, `get_shop_owner`, `get_languages` |
| Webhooky | `list_webhooks`, `list_webhook_events` |
| Diagnostika | `get_api_status` |

Seznam musí odpovídat `display.tools` v `connector.yaml` — z něj platforma
klasifikuje oprávnění nástrojů.

## Osobní údaje

Údaje zákazníků (e-maily, telefony, jména, adresy, IČO/DIČ, bankovní spojení)
se před odesláním do modelu nahradí stabilními tokeny typu
`<EMAIL_3f9c1a2b4d5e>`. Token je jednosměrný HMAC — nedá se rozšifrovat zpět
a nikde nevzniká re-identifikační mapa.

Katalogová data (produkty, kategorie, ceny) se nepseudonymizují. Ochranu
osobních údajů nelze operátorskou konfigurací vypnout.

## Konfigurace

| Klíč | Typ | Popis |
|---|---|---|
| `api_url` | credential | základní URL API v2 e-shopu |
| `api_login` | credential | přihlašovací jméno API klíče |
| `api_key` | credential (secret) | API klíč |

V režimu `local-stdio` se čtou z env jako `UPGATES_<KEY>` velkými písmeny.

## Testy

```bash
python -m pytest tests -q
openmcp-sdk validate connector.yaml
```

## Dokumentace

- [`docs/anonymization.md`](docs/anonymization.md) — pseudonymizace
- [`docs/readonly.md`](docs/readonly.md) — read-only režim
- [`docs/defaults.md`](docs/defaults.md) — výchozí hodnoty a limity
- [`docs/tools.md`](docs/tools.md) — nástroje
- [`dev-docs/upgatesapiv2.apib`](dev-docs/upgatesapiv2.apib) — API specifikace dodavatele
- [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Licence

[CC BY-NC 4.0](LICENSE)
