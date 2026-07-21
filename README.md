# upgates-com-mcp

MCP konektor pre **Upgates** e-shop API v2. Čítací prístup k objednávkam,
faktúram, produktom, zákazníkom a konfigurácii e-shopu s pseudonymizáciou
osobných údajov.

Súčasť platformy [OpenMCP.cz](https://openmcp.cz).

> **Poznámka k histórii:** konektor pôvodne vznikol v TypeScripte. Od
> `a8f71aa` (7/2026) je implementovaný v Pythone nad `openmcp-sdk`; TS strom
> bol odstránený a je dohľadateľný v git histórii.

## Rýchly štart

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ../openmcp-sdk -e .
export OPENMCP_MODE=local-stdio
export UPGATES_API_URL="https://vas-eshop.admin.upgates.com/api/v2"
export UPGATES_API_LOGIN="api-login"
export UPGATES_API_KEY="api-kluc"
export OPENMCP_PII_SALT="$(openssl rand -hex 32)"
python -m connector
```

API prístup sa zakladá v **Upgates Admin → Doplnky → API**.

`OPENMCP_PII_SALT` je povinný — bez neho konektor zámerne nenaštartuje. Tichý
fallback na náhodný salt by zrušil stabilitu pseudonymizačných tokenov
a prejavilo by sa to až po reštarte.

## Nástroje (23)

Všetky sú **iba na čítanie**; konektor nezapisuje ani nemaže.

| Oblasť | Nástroje |
|---|---|
| Objednávky | `list_orders`, `get_order_history`, `list_order_statuses` |
| Faktúry | `list_invoices` |
| Produkty | `list_products`, `list_products_simple`, `list_categories`, `list_labels`, `list_availabilities`, `list_manufacturers`, `list_parameters`, `list_pricelists` |
| Zákazníci | `list_customers`, `list_carts` |
| Doprava a platby | `list_shipments`, `list_payments`, `list_vouchers` |
| E-shop | `get_shop_config`, `get_shop_owner`, `get_languages` |
| Webhooky | `list_webhooks`, `list_webhook_events` |
| Diagnostika | `get_api_status` |

Zoznam musí sedieť s `display.tools` v `connector.yaml` — z neho platforma
klasifikuje oprávnenia nástrojov.

## Osobné údaje

Údaje zákazníkov (e-maily, telefóny, mená, adresy, IČO/DIČ, bankové spojenie)
sa pred odoslaním do modelu nahradia stabilnými tokenmi typu
`<EMAIL_3f9c1a2b4d5e>`. Token je jednosmerný HMAC — nedá sa rozšifrovať späť
a nikde nevzniká re-identifikačná mapa.

Katalógové dáta (produkty, kategórie, ceny) sa nepseudonymizujú.

Vypnúť sa to dá operátorským prepínačom `anonymize_data`, ale je zapnuté
z dôvodu GDPR a vypínať sa nemá.

## Konfigurácia

| Kľúč | Typ | Popis |
|---|---|---|
| `api_url` | credential | základná URL API v2 e-shopu |
| `api_login` | credential | prihlasovacie meno API kľúča |
| `api_key` | credential (secret) | API kľúč |
| `anonymize_data` | operator | pseudonymizácia osobných údajov (default zapnuté) |

V režime `local-stdio` sa čítajú z env ako `UPGATES_<KEY>` veľkými písmenami.

## Testy

```bash
python -m pytest tests -q
openmcp-sdk validate connector.yaml
```

## Dokumentácia

- [`docs/anonymization.md`](docs/anonymization.md) — pseudonymizácia
- [`docs/readonly.md`](docs/readonly.md) — read-only režim
- [`docs/defaults.md`](docs/defaults.md) — východzie hodnoty a limity
- [`docs/tools.md`](docs/tools.md) — nástroje
- [`dev-docs/upgatesapiv2.apib`](dev-docs/upgatesapiv2.apib) — API špecifikácia dodávateľa
- [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Licencia

[CC BY-NC 4.0](LICENSE)
