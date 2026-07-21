# Changelog

Všechny významné změny v Upgates MCP Server budou zdokumentovány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
a tento projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Záznamy do verze 0.1.x popisují původní **TypeScript** implementaci.
> Od 0.2.0 je konektor v Pythonu nad `openmcp-sdk`.

## [Unreleased]

### Změněné

- **HTTP klient a PII přesunuty do `openmcp-sdk` 0.4.** `src/connector/client.py`
  (vlastní retry/backoff/`UpgatesError`) a `src/connector/anonymize.py`
  (vlastní tokenizace) jsou nahrazené sdílenými `openmcp_sdk.http.UpstreamClient`
  a `openmcp_sdk.pii` — konektoru zůstává jen `src/connector/pii_fields.py`
  (mapy polí, žádná logika). **Pseudonymizační tokeny jsou bit-identické**
  s předchozí implementací (ověřeno golden-file testem v `test_anonymize.py`)
  — uživatel neuvidí jiné ID pro stejná data.
- `sdk_min_version` zvednuté na `0.4.0`, přidán `runtime.pii_salt: true` do
  `connector.yaml` (chybělo, přestože konektor salt vždy vyžadoval —
  `require_salt()` si dřív volal ručně v `__main__.py`; teď to dělá
  `run_connector` sám).

### Odebrané

- **TypeScript strom** (`src/*.ts`, `package.json`, `tsconfig.json`) —
  nahrazený Python implementací v `src/connector/` (commit `a8f71aa`).
  Dohledatelný v git historii.

### Opravené (dokumentace)

- `README.md` a `docs/tools.md` tvrdily **34 nástrojů včetně zapisovacích**
  (`create_order`, `update_orders`, `delete_orders`). Ty existovaly jen v TS
  verzi; Python konektor registruje **23 čtecích** nástrojů a `egress`
  povoluje výhradně `GET`. Read-only konektor tedy inzeroval zápis.
- `CONTRIBUTING.md` a `dev-docs/project-structure.md` naváděly na soubory,
  které už neexistují.

## [0.1.0] - 2025-10-09

### 🎉 První vydání

První veřejné vydání Upgates MCP Server - Model Context Protocol serveru pro integraci s Upgates e-shop API v2.

### ✨ Přidáno

#### Optimalizace pro LLM (efektivita tokenů)
- **Automatická optimalizace odpovědí** pro všechny list endpointy
- **82-99,8% snížení počtu tokenů** v závislosti na endpointu
  - Objednávky: snížení o 82,2 % (~110k tokenů ušetřeno na 100 objednávek)
  - Produkty: snížení o 99,8 % (~2M tokenů ušetřeno na 50 produktů)
  - Zákazníci: ~80% snížení
  - Faktury: ~85% snížení
  - Košíky: ~75% snížení
- **Filtrování polí** - ponechává jen nezbytná pole
  - Objednávky: 16 polí místo 38
  - Produkty: 13 polí místo 50+
  - Zákazníci: 12 polí místo 30+
- **Deduplikace vícejazyčnosti** - jen první jazyk
- **Zplošťování vnořených objektů** - souhrn produktů místo plných detailů
- **Bez nutnosti konfigurace** - funguje automaticky

#### Základní funkce
- **34 nástrojů** pokrývajících hlavní Upgates API endpointy
  - Objednávky: list, create, update, delete, history (5 nástrojů)
  - Stavy objednávek: list, create (2 nástroje)
  - Produkty: list, list_simple, create, update, delete (5 nástrojů)
  - Zákazníci: list, create (2 nástroje)
  - Kategorie: list, create (2 nástroje)
  - Faktury: list (1 nástroj)
  - Štítky: list (1 nástroj)
  - Dostupnosti: list (1 nástroj)
  - Výrobci: list (1 nástroj)
  - Parametry: list (1 nástroj)
  - Košíky: list (1 nástroj)
  - Slevové kupóny: list, create (2 nástroje)
  - Doprava: list (1 nástroj)
  - Platby: list (1 nástroj)
  - Webhooky: list, create, list_events (3 nástroje)
  - Systém: languages, config, owner, api_status, pricelists (5 nástrojů)

- **5 zdrojů (resources)** s podrobnou dokumentací
  - `upgates://system/info` - schopnosti a funkce serveru
  - `upgates://api/endpoints` - přehled API endpointů
  - `upgates://api/rate-limits` - informace o rate limitingu
  - `upgates://config/settings` - konfigurace serveru
  - `upgates://api/documentation` - odkazy na dokumentaci

#### Bezpečnostní funkce
- **HTTP Basic Authentication** - standardní autentizace dle RFC 7617
- **Readonly režim** - ochrana proti neúmyslným změnám dat
  - Blokuje všechny zapisovací operace (create, update, delete)
  - Povoluje všechny čtecí operace (list, get)
  - Srozumitelné chybové hlášky pro blokované operace
- **GDPR anonymizace dat** - komplexní ochrana PII
  - 40+ citlivých polí anonymizováno
  - E-mail, telefon, jména, adresy
  - Podnikatelské identifikátory (IČO, DIČ, IBAN, SWIFT)
  - Hluboká anonymizace vnořených objektů a polí
  - Rozpoznávání vzorů pro dynamická pole

#### Architektura
- **Clean Architecture** - modulární návrh s oddělením odpovědností
- **TypeScript** - plná typová bezpečnost se strict módem (2 716 řádků)
- **Zpracování chyb** - 8 vlastních tříd chyb
  - UpgatesError, ConfigurationError, AuthenticationError
  - ValidationError, NotFoundError, NetworkError
  - RateLimitError, ReadonlyError
- **Validační vrstva** - komplexní validace vstupů
  - Validace formátu data (ISO 8601)
  - Validace stránkování
  - Validace formátu ID
  - Validace e-mailu
- **Zpracování rate limitů** - korektní zvládání limitů API
  - Parsování response hlaviček
  - Podpora Retry-After
  - Srozumitelné chybové hlášky

#### Testování
- **35 unit testů** - 100% úspěšnost
  - Třídy chyb (10 testů)
  - Handlery nástrojů (2 testy)
  - Validátory (11 testů)
  - Anonymizace (12 testů)
- **Integrační testy** - testováno proti živému Upgates API
  - Obchod EdgarPower (23 789 objednávek, 87 produktů)
  - 6 jazyků (cs, en, hu, sk, de, pl)
  - Ověřeny všechny čtecí operace

#### Dokumentace
- **README.md** - uživatelsky přívětivá česká dokumentace
- **TEST_REPORT.md** - podrobná testovací zpráva
- **CHANGELOG.md** - tento soubor
- Inline dokumentace kódu pomocí JSDoc komentářů
- Mapování API endpointů z oficiální dokumentace Upgates API v2

#### Konfigurace
- Konfigurace přes proměnné prostředí
- Povinné: UPGATES_API_URL, UPGATES_API_USERNAME, UPGATES_API_PASSWORD
- Volitelné: UPGATES_TIMEOUT, UPGATES_READONLY, UPGATES_ANONYMIZE_DATA
- Validace při startu s užitečnými chybovými hláškami
- Bezpečné logování konfigurace (credentials nikdy nejsou vystaveny)

### 🔧 Technické detaily

#### Závislosti
- `@modelcontextprotocol/sdk` - implementace MCP protokolu
- `axios` - HTTP klient pro komunikaci s API
- `typescript` - typová bezpečnost a kompilace
- `tsx` - spouštění TypeScript testů

#### Podporované skupiny Upgates API v2
- Objednávky (Orders)
- Stavy objednávky (Order Statuses)
- Faktury (Invoices)
- Produkty (Products)
- Štítky (Labels)
- Dostupnosti (Availabilities)
- Výrobci (Manufacturers)
- Parametry (Parameters)
- Kategorie (Categories)
- Zákazníci (Customers)
- Košíky (Carts)
- Slevové kupóny (Vouchers)
- Doprava (Shipments)
- Platba (Payments)
- Webhooky (Webhooks)
- E-shop konfigurace
- Jazyky (Languages)
- Ceníky (Pricelists)
- Provozovatel (Owner)
- API Status

#### Podporované limity API
- Rate limit tiery (Bronze až Exclusive)
- Omezení souběžných requestů (max 3)
- Hromadné operace (max 100 položek)
- Stránkování (50-100 položek na stránku)
- Parsování response hlaviček pro zbývající limity

### 📝 Známá omezení

- Oprávnění API uživatele se konfigurují na straně serveru
- Některé endpointy vyžadují ke správné funkci specifická oprávnění
- Zapisovací operace vyžadují `UPGATES_READONLY=false`
- PDF generování endpointů zatím není implementováno

### 🎯 Plánovaná vylepšení

Plánováno pro budoucí vydání:
- Podpora stahování PDF (faktury, objednávky)
- Další skupiny endpointů (Articles, News, Advisor, Files)
- Nástroje pro správu skladu
- Podpora vlastních polí (Metas)
- Správa grafiky a záloh
- Správa konverzních kódů
- Rozsáhlejší integrační testy

---

## Jak upgradovat

### Ze začátku na 0.1.0

Toto je první vydání, takže stačí nainstalovat:

```bash
git clone https://github.com/LukasOrcik/upgates-com-mcp.git
cd upgates-com-mcp
npm install
npm run build
```

---

## Přispívání

Příspěvky jsou vítány! Neváhejte poslat Pull Request.

### Nastavení vývojového prostředí

```bash
# Naklonování repozitáře
git clone https://github.com/LukasOrcik/upgates-com-mcp.git
cd upgates-com-mcp

# Instalace závislostí
npm install

# Spuštění ve vývojovém režimu
npm run dev

# Spuštění testů
npm test
```

---

## Odkazy

- **Domovská stránka**: https://openmcp.cz
- **Repozitář**: https://github.com/LukasOrcik/upgates-com-mcp
- **Issues**: https://github.com/LukasOrcik/upgates-com-mcp/issues
- **Dokumentace Upgates API**: https://upgatesapiv2.docs.apiary.io/
- **Model Context Protocol**: https://modelcontextprotocol.io/

---

**Poznámka**: Toto je komunitní projekt a není oficiálně spojen se společností Upgates.
