# Přispívání do projektu

Děkujeme za zájem. Konektor je Python balíček nad
[`openmcp-sdk`](https://github.com/mcp-open/openmcp-sdk).

## Nahlášení chyby

Zkontroluj [issues](https://github.com/mcp-open/upgates-com-mcp/issues) a založ
nové s popisem, kroky k reprodukci, očekávaným vs. skutečným chováním
a verzí konektoru. **Do logů v issue nedávej citlivá data** — ani
pseudonymizované tokeny nejsou náhrada za rozvahu.

Bezpečnostní problémy nepatří do veřejných issues: `security@openmcp.cz`.

## Vývojové prostředí

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ../openmcp-sdk -e '.[test]'
export OPENMCP_PII_SALT="$(openssl rand -hex 32)"
```

## Před odesláním změny

```bash
python -m pytest tests -q
openmcp-sdk validate connector.yaml
```

Oba musí projít. `validate` ověřuje i invarianty platformy (egress,
`display.tools`, slug), takže „prošlo" znamená „platforma to přijme".

## Přidání nového nástroje

1. **Funkce v `src/connector/server.py`.** Registruje se přes
   `mcp.tool(fn, annotations=ToolAnnotations(readOnlyHint=True))`.
   Anotace je **bezpečnostní hranice**: při zapnutém read-only režimu SDK
   fail-closed odregistruje vše, co `readOnlyHint=True` nemá — nástroj bez
   ní v produkci tiše zmizí.
2. **Volání přes `_get()` v `src/connector/server.py`.** Endpoint a parametry
   patří do funkce nástroje, HTTP mechaniku (retry, timeout, chyby) řeší
   sdílený `openmcp_sdk.http.UpstreamClient` — nepiš vlastní HTTP kód.
3. **Záznam v `display.tools`** v `connector.yaml`. Bez něj platforma nástroj
   nezaklasifikuje a bude fail-closed zamítnut. Shodu se zaregistrovanými
   nástroji hlídá test.
4. **Test v `tests/`.** Upstream se mockuje, nevolá se doopravdy.
5. **Řádek v `docs/tools.md`.**

## Osobní údaje

Nové pole s osobními údaji patří do tabulek v
`src/connector/pii_fields.py` — nikdy se neřeší ad hoc v kódu nástroje.

Pseudonymizační tokeny jsou **externě viditelný kontrakt**: když se změní jejich
odvození, uživatel uvidí jiné ID pro stejná data. Takovou změnu je třeba
zdůvodnit v `CHANGELOG.md`.

## Konvence

- Výchozí větev je `main`.
- Konektor je **pouze pro čtení**. Zapisovací nástroje by znamenaly změnu
  `capabilities.supports_write`, `egress.methods` a potvrzovací vrstvu —
  to je samostatné rozhodnutí, ne běžný PR.
- Do repozitáře nepatří secrets, `.env` ani produkční logy.

## Historická poznámka

Konektor původně vznikl v TypeScriptu. Od 7/2026 je v Pythonu; TS strom byl
odstraněn a je dohledatelný v git historii. Starší části `CHANGELOG.md`
a `RELEASE.md` popisují TS verzi.
