# Changelog

Všechny významné změny v Upgates MCP Server budou zdokumentovány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
a tento projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Záznamy do verze 0.1.x popisují původní **TypeScript** implementaci.
> Od 0.2.0 je konektor v Pythonu nad `openmcp-sdk`.

## [0.2.1] — 2026-07-31

### Opravené

- **Konektor s lokalizovanou nápovědou k polím vůbec nenaběhl.** Manifest
  používá `display.locales.*.fields[].hint`, ale pin SDK zůstal na verzi, která
  ho odmítá jako `extra_forbidden` — `openmcp-sdk validate` i start konektoru
  padaly na šesti chybách validace. Pin zvednutý na
  `0d36cf1a93c870fe237ecbe3bee7b52b202df18d` (openmcp-sdk 0.4.3),
  `sdk_min_version` na `0.4.3`.
- **Zákaznický e-mail a telefon končily v logu.** `list_orders` a
  `list_customers` je berou jako filtry v query stringu a httpx loguje celou
  URL požadavku na úrovni INFO. SDK 0.4.3 httpx ztišuje na WARNING, takže
  se do strukturovaného stdout logu (a sběrače) dostanou už jen selhání
  přenosu, ne úspěšné URL.
- **Detail jednoho záznamu se vracel jako prázdná stránka.** Odpověď, která
  není stránka seznamu (`/orders/{order_number}`, `/invoices/{n}`,
  `/products/{code}`, `/carts/{id}`), optimalizace přepsala na
  `{"orders": [], "current_page_items": 0}` — model tedy na dotaz po konkrétní
  objednávce dostal „nic tu není". Nerozpoznaný tvar teď projde beze změny.
- **`mcp_note` hlásil oříznutí, které se nestalo, a radil nefunkční postup.**
  Poznámka tvrdila „Zobrazeno prvních 15 z None položek" tam, kde upstream
  `current_page_items` neposlal, a „prvních 15 z 3" tam, kde se neořezávalo
  vůbec. Hlavně ale u skutečného oříznutí radila „použij parametr page" —
  jenže ořezává se **uvnitř** jedné upstream stránky, takže položky 16..N
  z téže stránky `page=2` nevrátí (přeskočí na následující upstream stránku).
  Poznámka teď říká, kolik položek je nedostupných, a doporučuje zúžit filtry;
  další stránku nabízí jen tehdy, když `current_page < number_of_pages`.
  Přibyl strojově čitelný příznak `mcp_truncated`. Neslovníková položka se
  propouští beze změny místo tichého zahození.
- **`list_customers` nikdy neukázal e-mail.** E-mail zákazníka je v Upgates v2
  přihlašovací údaj (`login.email`), optimalizace ho četla jen z kořene objektu
  a vracela `None`. Čte se teď z obou úrovní.
- **Produkt nikdy neměl cenu.** Optimalizace četla `price_with_vat`,
  `price_without_vat` a `currency` — pole, která ve schématu Upgates v2 vůbec
  nejsou, takže vycházela vždy `None`. Nahrazena skutečnými poli: z `prices[]`
  se vrací `language`, `price_common`, `price_purchase`, `vat` a
  `recycling_fee`, z `prices[].pricelists[]` pak `name` (jako `pricelist_name`),
  `price_original`, `product_discount` a `price_sale`. Žádné dopočítávané
  ani vymyšlené hodnoty.
- **Test spojení hlásil špatnou příčinu.** Všechny 4xx padaly do jedné hlášky
  „Neplatný API login nebo klíč". Nově: 400/401 → `credential_invalid`,
  403 → `provider_permission_denied`, 301/404/410 → `instance_unknown`
  s hláškou podle stavu (301 přesunutý e-shop nebo změněná adresa API,
  404/410 neznámý či zrušený e-shop), 429 → `rate_limited`, 5xx a síť →
  `upstream_unavailable`. Nedostupné nebo vadné údaje v kontextu (chybějící
  klíč, neplatná `api_url`) hlásí `credential_invalid` místo `invalid_input` —
  ten se v public safe-test větvi normalizéru překlápí na
  `runtime_unavailable` a příčina by se uživateli ztratila.
- **403 radilo uživateli špatný krok.** Hláška tvrdila, že klíč nemá oprávnění
  ke čtení. `/status` je ale podle dokumentace povolený každému API uživateli,
  takže 403 na něm znamená neaktivního nebo po pěti neúspěšných pokusech
  dočasně zablokovaného API uživatele. Rada teď zní zkontrolovat v administraci
  (Doplňky → API), že je uživatel aktivní, a po lockoutu ověřit login i klíč.
- **Test spojení se nevešel do rozpočtu platformy.** Běžel s výchozími čtyřmi
  pokusy a 30s timeoutem, takže při pomalém upstreamu přestřelil tvrdý strop
  12 s a uživatel místo příčiny dostal timeout řídicí roviny. Staví se teď
  stejnou `_client()` továrnou jako nástroje, jen s vlastní politikou: jeden
  pokus (`NO_RETRY`), 8 s celkem, 3 s na spojení.
- **Rate limit se opakoval proti sobě.** Běžná volání používala výchozí
  `READ_RETRY`, které opakuje i 429 — u tvrdého limitu Upgates to limit jen
  dál pálilo. Nově `SERVER_ERRORS_ONLY`: opakují se jen 5xx, 429 jde ven jako
  `rate_limited`.

### Změněné

- **PII tokeny se odvozují od vlastníka credentials, ne od volajícího.**
  Data tenant je e-shop, ke kterému patří `api_key`, a ten může vlastnit tým:
  odvození z `principal.sub` dávalo každému členovi jiný token pro téhož
  zákazníka. Nově se použije `credential_owner_id` (bez prefixu podle druhu
  vlastníka) s fallbackem na `sub`. Uživatelsky vlastněné připojení má dle
  kontraktu SDK `credential_owner_id == sub`, takže **jeho tokeny se nemění
  ani o bit** — golden test zůstává v platnosti.

## [Unreleased]

### Opravené

- HTTP transport je stateless, takže následné MCP požadavky nevyžadují
  replikačně lokální session ID a fungují za více replikami.
- Cílové URL webhooků se vracejí pouze jako stabilní `<URL_…>` tokeny;
  případné přihlašovací údaje nebo query tokeny se nedostanou do AI klienta.
- Obecná pole `before`, `after` a `value` v historii objednávky se tokenizují
  fail-closed, protože mohou obsahovat libovolné osobní údaje.
- Čisté dot-segmenty `.` a `..` se odmítnou před sestavením URL a nemohou
  změnit cílový Upgates endpoint.
- Veřejná lokální konfigurace a privacy/read-only dokumentace odpovídají
  povinné pseudonymizaci, aktuální doméně API a skutečným L3/L4 možnostem
  Kubernetes NetworkPolicy.

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
- Release používá přesný vendovaný snapshot SDK a zamčené Python závislosti,
  které lze ověřit bez mezirepozitárového přístupového tokenu.

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
