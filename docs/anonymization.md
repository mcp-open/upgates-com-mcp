# Povinná pseudonymizace zákaznických dat

Konektor chrání osobní a přístupové údaje před každou odpovědí AI klientovi.
Ochrana je povinná a nelze ji vypnout konfiguračním přepínačem.

## Formát a stabilita tokenů

Chráněná hodnota se nahradí stabilním jednosměrným tokenem, například
`<EMAIL_3f9c1a2b4d5e>`, `<PHONE_…>`, `<NAME_…>` nebo `<ADDR_…>`.
Stejná hodnota ve stejném zákaznickém kontextu vytvoří stejný token, takže lze
záznamy porovnávat bez zpřístupnění původní hodnoty. Token nelze dešifrovat a
konektor nevytváří re-identifikační mapu.

`OPENMCP_PII_SALT` je povinné provozní tajemství. Bez něj runtime záměrně
nenastartuje; tichý náhodný fallback by po restartu měnil tokeny.

## Co se chrání

- e-maily, telefony a kontaktní údaje;
- osobní jména a adresy;
- firemní identifikátory IČO/DIČ a bankovní spojení;
- zákaznické kódy a citlivé poznámky;
- jméno uživatele a dynamické hodnoty `before`, `after` a `value` v historii
  objednávky;
- cílové URL webhooků, protože mohou obsahovat uživatelské jméno, heslo nebo
  token v query parametru.

Pole historie mají obecné názvy a mohou obsahovat libovolná zákaznická data.
Proto se dynamické hodnoty tokenizují fail-closed kategorií `<HISTORY_…>`,
i když by konkrétní hodnota mohla být neosobní. Technická pole jako událost,
původ a čas zůstávají čitelná.

## Chráněné nástroje

- `list_orders`
- `get_order_history`
- `list_invoices`
- `list_customers`
- `list_carts`
- `get_shop_owner`
- `list_webhooks`

Volný text se navíc kontroluje na e-mailové adresy, telefonní čísla a URL.
Katalogová data, například kód produktu, cena nebo kategorie, zůstávají
čitelná, pokud nejsou součástí výše uvedené citlivé semistrukturované hodnoty.

## Provozní hranice

Pseudonymizace probíhá uvnitř konektoru před sestavením MCP odpovědi.
Upstream Upgates API přirozeně vrací původní data; do logů ani odpovědi AI
klientovi se nesmí zapisovat v otevřené podobě. Pro další omezení rozsahu
udělte API uživateli v administraci Upgates pouze potřebná čtecí oprávnění.
