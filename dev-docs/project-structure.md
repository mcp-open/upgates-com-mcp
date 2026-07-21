# Štruktúra projektu

Konektor je Python balík nad `openmcp-sdk`. Balík sa volá neutrálne
`connector` — slug žije výhradne v `connector.yaml`, nie v mene balíka.

```
upgates-com-mcp/
├── connector.yaml            manifest — jediný deklaratívny zdroj pravdy
├── Dockerfile                build (kontext je nadradený priečinok, kvôli sdk/)
├── pyproject.toml
├── src/connector/
│   ├── __main__.py           `python -m connector` — ENTRYPOINT
│   ├── server.py             23 čítacích nástrojov + test_connection
│   ├── client.py             Upgates API v2 (Basic auth, retry)
│   ├── anonymize.py          pseudonymizácia osobných údajov
│   ├── optimizers.py         tvarovanie odpovede pre kontextové okno modelu
│   └── validators.py         validácia vstupov → ConnectorError(INVALID_INPUT)
├── tests/
├── docs/                     používateľská dokumentácia
└── dev-docs/
    └── upgatesapiv2.apib     API špecifikácia dodávateľa
```

## Poradie spracovania odpovede

```
upstream → validators → optimizers → anonymize → envelope → model
```

**Najprv tvarovať, potom pseudonymizovať.** Opačné poradie by tokenizovalo
polia, ktoré sa aj tak zahodia.

## Čo rieši SDK, nie tento repozitár

Identita, credentials z Vaultu, tri režimy `OPENMCP_MODE`, read-only filter,
mapovanie HTTP chýb a HTTP transport sú v `openmcp-sdk`. Konektor obsahuje len
to, čo je špecifické pre Upgates API.

## Historická poznámka

Konektor pôvodne vznikol v TypeScripte (`src/*.ts`, `package.json`). Python
implementácia pribudla commitom `a8f71aa` (7/2026) a TS strom bol následne
odstránený — je dohľadateľný v git histórii. `RELEASE.md` popisuje vydanie
pôvodnej TS verzie a je ponechaný ako historický záznam.
