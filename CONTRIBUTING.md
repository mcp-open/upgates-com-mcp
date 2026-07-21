# Prispievanie do projektu

Ďakujeme za záujem. Konektor je Python balík nad
[`openmcp-sdk`](https://github.com/mcp-open/openmcp-sdk).

## Nahlásenie chyby

Skontroluj [issues](https://github.com/mcp-open/upgates-com-mcp/issues) a založ
nové s popisom, krokmi na reprodukciu, očakávaným vs. skutočným správaním
a verziou konektora. **Do logov v issue nedávaj citlivé dáta** — ani
pseudonymizované tokeny nie sú náhrada za rozvahu.

Bezpečnostné problémy nepatria do verejných issue: `security@openmcp.cz`.

## Vývojové prostredie

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ../openmcp-sdk -e '.[test]'
export OPENMCP_PII_SALT="$(openssl rand -hex 32)"
```

## Pred odoslaním zmeny

```bash
python -m pytest tests -q
openmcp-sdk validate connector.yaml
```

Obe musia prejsť. `validate` overuje aj invarianty platformy (egress,
`display.tools`, slug), takže „prešlo" znamená „platforma to prijme".

## Pridanie nového nástroja

1. **Funkcia v `src/connector/server.py`.** Registruje sa cez
   `mcp.tool(fn, annotations=ToolAnnotations(readOnlyHint=True))`.
   Anotácia je **bezpečnostná hranica**: pri zapnutom read-only režime SDK
   fail-closed odregistruje všetko, čo `readOnlyHint=True` nemá — nástroj bez
   nej v produkcii ticho zmizne.
2. **Cesta v `src/connector/client.py`.** Nie priamo v nástroji.
3. **Záznam v `display.tools`** v `connector.yaml`. Bez neho platforma nástroj
   nezaklasifikuje a bude fail-closed zamietnutý. Zhodu so zaregistrovanými
   nástrojmi stráži test.
4. **Test v `tests/`.** Upstream sa mockuje, nevolá sa naozaj.
5. **Riadok v `docs/tools.md`.**

## Osobné údaje

Nové pole s osobnými údajmi patrí do tabuliek v
`src/connector/anonymize.py` — nikdy sa nerieši ad hoc v kóde nástroja.

Pseudonymizačné tokeny sú **externe viditeľný kontrakt**: keď sa zmení ich
odvodenie, používateľ uvidí iné ID pre tie isté dáta. Takú zmenu treba
zdôvodniť v `CHANGELOG.md`.

## Konvencie

- Východzia vetva je `main`.
- Konektor je **iba na čítanie**. Zapisovacie nástroje by znamenali zmenu
  `capabilities.supports_write`, `egress.methods` a potvrdzovaciu vrstvu —
  to je samostatné rozhodnutie, nie bežný PR.
- Do repozitára nepatria secrets, `.env` ani produkčné logy.

## Historická poznámka

Konektor pôvodne vznikol v TypeScripte. Od 7/2026 je v Pythone; TS strom bol
odstránený a je dohľadateľný v git histórii. Staršie časti `CHANGELOG.md`
a `RELEASE.md` popisujú TS verziu.
