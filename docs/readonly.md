# Read-only režim

Konektor je **výhradně čtecí**. Nemá jediný zapisovací nástroj a
`egress.methods` v `connector.yaml` povoluje jen `GET`, takže zápis
neprojde ani přes síťovou politiku.

> Předchozí verze tohoto dokumentu popisovala proměnnou `UPGATES_READONLY`
> a blokování nástrojů jako `create_order`. Obojí pocházelo z původní
> TypeScript implementace: ta proměnná **nic nedělá** a ty nástroje
> v Python konektoru neexistují.

## Jak je to vynuceno

Ne „aplikační vrstvou" v kódu konektoru, ale **SDK filtrem při startu**.
Každý nástroj má anotaci `readOnlyHint`; když je read-only režim zapnutý,
`run_connector` fail-closed odregistruje vše, co `readOnlyHint=True` nemá.
Nástroj se tedy k modelu vůbec nedostane — nejde o kontrolu při volání.

Tři nezávislé vrstvy:

| Vrstva | Co brání zápisu |
|---|---|
| Konektor | žádný zapisovací nástroj není implementován |
| SDK | read-only filtr odregistruje neanotované nástroje při startu |
| Síť | `egress.methods: [GET]` → NetworkPolicy jiné metody zablokuje |

Navíc se doporučuje dát API uživateli v Upgates adminu jen čtecí
oprávnění — konektor se na to nespoléhá, ale je to levná čtvrtá vrstva.

## Přepínač

`read_only` **není** v `operator_config`, takže SDK použije fallback na
proměnnou prostředí:

```bash
UPGATES_READ_ONLY=true    # pozor: READ_ONLY s podtržítkem
```

Výchozí hodnota je `true` (`capabilities.default_read_only`). Vypnutí
nemá u tohoto konektoru efekt — žádný zapisovací nástroj neexistuje, takže
filtr nemá co pustit navíc.

## Doporučená konfigurace

```bash
UPGATES_READ_ONLY=true         # ochrana proti změnám
UPGATES_ANONYMIZE_DATA=true    # ochrana zákaznických dat (GDPR)
OPENMCP_PII_SALT=…             # povinné, jinak konektor nenastartuje
```
