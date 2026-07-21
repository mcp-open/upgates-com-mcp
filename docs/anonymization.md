# GDPR Anonymizace zákaznických dat

Server podporuje automatickou anonymizaci citlivých zákaznických údajů pro ochranu soukromí a splnění GDPR.

## Zapnutí anonymizace

```bash
UPGATES_ANONYMIZE_DATA=true
```

## Co se anonymizuje (40+ polí)

### Zákaznické údaje
- E-mail: `email`, `customer_email`
- Telefon: `phone`, `phoneNumber`, `fax`
- Jména: `firstname`, `surname`, `customer_name`, `nickname`
- Fakturační jména: `firstname_invoice`, `surname_invoice`
- Poštovní jména: `firstname_postal`, `surname_postal`
- Společnost: `company`, `company_name`, `company_postal`

### Adresy
- Ulice: `street`, `street_invoice`, `street_postal`
- Město: `city`, `city_invoice`, `city_postal`
- Kraj/stát: `state`, `state_invoice`, `state_postal`
- PSČ: `zip`, `zip_invoice`, `zip_postal`, `zip_code`

### Firemní identifikátory
- České/slovenské identifikátory: `ico`, `dic`
- Mezinárodní: `company_number`, `vat_number`
- Bankovní údaje: `iban`, `swift`, `bank_account`, `account_number`

### Ostatní citlivá data
- Poznámky: `customer_note`, `internal_note`, `note`
- Osobní údaje: `degree`, `salutation`, `declension`
- Symboly: `variable_symbol`, `specific_symbol`
- Kódy: `code`, `customer_code`

Plus jakékoliv pole obsahující: name, email, phone, address, street, city, zip

## Příklad

### Bez anonymizace
```json
{
  "customer": {
    "email": "jan.novak@example.com",
    "phone": "+420123456789",
    "firstname_invoice": "Jan",
    "surname_invoice": "Novák",
    "street_invoice": "Hlavní 123",
    "city_invoice": "Praha",
    "zip_invoice": "12000",
    "company": "Test s.r.o.",
    "ico": "12345678",
    "dic": "CZ12345678"
  }
}
```

### S anonymizací
```json
{
  "customer": {
    "email": "***ANONYMIZED***",
    "phone": "***ANONYMIZED***",
    "firstname_invoice": "***ANONYMIZED***",
    "surname_invoice": "***ANONYMIZED***",
    "street_invoice": "***ANONYMIZED***",
    "city_invoice": "***ANONYMIZED***",
    "zip_invoice": "***ANONYMIZED***",
    "company": "***ANONYMIZED***",
    "ico": "***ANONYMIZED***",
    "dic": "***ANONYMIZED***"
  }
}
```

Necitlivá pole (order_number, product_id, price, status) zůstávají nezměněná.

## Které endpointy anonymizují

- `list_orders` - Zákaznická data v objednávkách
- `get_order_history` - Historie může obsahovat zákaznická data
- `list_invoices` - Fakturační údaje zákazníků
- `list_customers` - Všechna osobní data (PII)
- `list_carts` - Údaje v košících
- `get_shop_owner` - Údaje majitele shopu

## Technické detaily

- **Hloubková anonymizace**: Rekurzivně prochází vnořené objekty a pole
- **Zachování null hodnot**: Zachovává `null`, `undefined` a prázdné řetězce
- **Nedestruktivní**: Vytváří hlubokou kopii, nemění originál
- **Shoda podle vzoru**: Zachytává pole podle jména i klíčových slov

## Případy použití

- **Shoda s GDPR**: Ochrana PII v logách a debugging
- **Vývoj a testování**: Práce s produkčními daty bezpečně
- **Školení a demo**: Použití reálné struktury dat bez obav o soukromí
- **Analytika**: Analýza vzorců bez ukládání osobních dat
- **Sdílená prostředí**: Více vývojářů může přistupovat k datům bezpečně
