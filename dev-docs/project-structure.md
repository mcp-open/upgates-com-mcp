# Struktura projektu

Konektor je Python balík nad `openmcp-sdk`. Balík se jmenuje neutrálně
`connector` — slug žije výhradně v `connector.yaml`, ne ve jméně balíku.

```
upgates-com-mcp/
├── connector.yaml            manifest — jediný deklarativní zdroj pravdy
├── Dockerfile                build (kontext je nadřazená složka, kvůli sdk/)
├── pyproject.toml
├── src/connector/
│   ├── __main__.py           `python -m connector` — ENTRYPOINT
│   ├── server.py             23 čtecích nástrojů + test_connection
│   ├── client.py             Upgates API v2 (Basic auth, retry)
│   ├── anonymize.py          pseudonymizace osobních údajů
│   ├── optimizers.py         tvarování odpovědi pro kontextové okno modelu
│   └── validators.py         validace vstupů → ConnectorError(INVALID_INPUT)
├── tests/
├── docs/                     uživatelská dokumentace
└── dev-docs/
    └── upgatesapiv2.apib     API specifikace dodavatele
```

## Pořadí zpracování odpovědi

```
upstream → validators → optimizers → anonymize → envelope → model
```

**Nejprve tvarovat, potom pseudonymizovat.** Opačné pořadí by tokenizovalo
pole, která se stejně zahodí.

## Co řeší SDK, ne tento repozitář

Identita, credentials z Vaultu, tři režimy `OPENMCP_MODE`, read-only filtr,
mapování HTTP chyb a HTTP transport jsou v `openmcp-sdk`. Konektor obsahuje jen
to, co je specifické pro Upgates API.

## Historická poznámka

Konektor původně vznikl v TypeScriptu (`src/*.ts`, `package.json`). Python
implementace přibyla commitem `a8f71aa` (7/2026) a TS strom byl následně
odstraněn — je dohledatelný v git historii. `RELEASE.md` popisuje vydání
původní TS verze a je ponechán jako historický záznam.
