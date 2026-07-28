# Read-only režim

Hostovaná varianta konektoru je výhradně čtecí. Registruje 23 nástrojů typu
`list_*` a `get_*`; žádný nástroj pro vytvoření, změnu nebo smazání dat není
implementovaný.

## Jak je zápis omezen

| Vrstva | Co prosazuje |
|---|---|
| Konektor | implementuje pouze čtecí nástroje a každý označuje `readOnlyHint=true` |
| Manifest | deklaruje `supports_write: false`, výchozí read-only režim a pouze metodu `GET` |
| Runtime | SDK při startu fail-closed odmítne nástroj bez správné read-only anotace |
| Síť | Kubernetes NetworkPolicy omezuje cíle a porty, nikoli HTTP metody |
| Upgates účet | doporučený čtecí účet omezuje škodu i při chybě jiné vrstvy |

`egress.methods: [GET]` je aplikační kontrakt manifestu. Běžná Kubernetes
NetworkPolicy pracuje na L3/L4 a sama nerozlišuje `GET`, `POST` nebo `DELETE`;
proto se ochrana nesmí opírat jen o síťovou politiku.

## Konfigurace

Read-only chování ani pseudonymizace nemají uživatelský vypínač.
Staré proměnné `UPGATES_READONLY`, `UPGATES_READ_ONLY` a
`UPGATES_ANONYMIZE_DATA` nejsou součástí aktuálního kontraktu a nemají se
uvádět v konfiguraci.

Pro lokální `stdio` režim stačí přístupové údaje, provozní mód a povinný salt:

```bash
OPENMCP_MODE=local-stdio
UPGATES_API_URL=https://vas-eshop.admin.s17.upgates.com/api/v2
UPGATES_API_LOGIN=api-login
UPGATES_API_KEY=api-klic
OPENMCP_PII_SALT=…
```
