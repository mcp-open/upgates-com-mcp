# Výchozí hodnoty výpisových nástrojů

Výpisové nástroje mají výchozí hodnoty nastavené tak, aby odpověď nezaplnila
kontextové okno modelu.

> Příklady níže jsou **pseudokód volání nástroje**, ne JavaScript — konektor
> je od 7/2026 v Pythonu. Počty položek byly opraveny: strop je
> `MAX_ITEMS_FOR_MCP = 15` v `src/connector/optimizers.py`, ne 100.

## 📋 Přehled defaultů

### `list_orders`

**Defaults:**
- `page: 1` - První stránka
- `order_by: 'creation_time'` - Řazení podle data vytvoření
- `order_dir: 'desc'` - **Nejnovější první** (od nejnovějších k nejstarším)

**Výsledek:**
- Bez parametrů vrátí nejnovější objednávky (strop `MAX_ITEMS_FOR_MCP = 15`)
- Objednávka z dneška bude první
- Ideální pro "Jaké máme nové objednávky?"

**Příklad:**
```text
// Bez parametrů - použijí se defaults
list_orders({})
// Vrátí: nejnovější objednávky (max 15), seřazené od nejnovější

// S vlastními parametry - přepíšou defaults
list_orders({ page: 2, order_dir: 'asc' })
// Vrátí: Stránku 2, seřazenou od nejstarších
```

---

### `list_products`

**Defaults:**
- `page: 1` - První stránka
- `active_yn: true` - **Pouze aktivní produkty** (skryje neaktivní)
- `variants_yn: false` - Bez variant (šetří tokeny)

**Výsledek:**
- Bez parametrů vrátí aktivní produkty (strop `MAX_ITEMS_FOR_MCP = 15`)
- Neaktivní a archivované produkty jsou automaticky vyfiltrované
- Varianty se nezahrnují (ušetří tokeny)

**Příklad:**
```text
// Bez parametrů - jen aktivní produkty
list_products({})
// Vrátí: max 15 aktivních produktů bez variant

// Pokud chcete i neaktivní
list_products({ active_yn: false })

// S variantami
list_products({ variants_yn: true })
```

---

### `list_customers`

**Defaults:**
- `page: 1` - První stránka
- `active_yn: true` - **Pouze aktivní zákazníci**
- `blocked_yn: false` - **Neblokovaní zákazníci**

**Výsledek:**
- Bez parametrů vrátí aktivní, neblokované zákazníky (strop 15)
- Filtruje problémy zákazníky automaticky

**Příklad:**
```text
// Bez parametrů - jen aktivní, neblokovaní
list_customers({})

// Včetně blokovaných
list_customers({ blocked_yn: true })

// Všichni zákazníci
list_customers({ active_yn: undefined, blocked_yn: undefined })
```

---

### `list_carts`

**Defaults:**
- `page: 1` - První stránka
- `creation_time_from: dnes - 7 dní` - **Pouze košíky za poslední týden**

**Výsledek:**
- Automaticky filtruje staré košíky (> 7 dní)
- Zobrazí jen relevantní nedokončené nákupy

**Příklad:**
```text
// Bez parametrů - košíky za 7 dní
list_carts({})
// Vrátí: Košíky vytvořené od 2025-10-02

// Vlastní rozsah
list_carts({ creation_time_from: '2025-09-01' })
// Vrátí: Košíky od září
```

---

### `list_categories`

**Defaults:**
- `page: 1` - První stránka
- `active_yn: true` - **Pouze aktivní kategorie**

**Výsledek:**
- Filtruje neaktivní/skryté kategorie

---

### `list_vouchers`

**Defaults:**
- `page: 1` - První stránka
- `active_yn: true` - **Pouze aktivní kupóny**

**Výsledek:**
- Neukáže expirované nebo deaktivované kupóny

---

### `list_invoices`

**Defaults:**
- `page: 1` - První stránka

**Žádné další filtry** - faktury jsou důležité vždy.

---

### `list_order_statuses`, `list_labels`, `list_availabilities`, atd.

**Defaults:**
- `page: 1` - První stránka

**Žádné filtry** - číselníky jsou malé, zobrazí se všechny.

---

## 🎯 Proč tyto defaults?

### 1. **Relevance**
- Nejnovější objednávky jsou nejdůležitější
- Aktivní produkty jsou v prodeji
- Košíky starší než týden jsou většinou neaktuální

### 2. **Token efektivita**
- Méně položek = méně tokenů
- Filtrované výsledky = rychlejší AI analýza

### 3. **User experience**
- Uživatel většinou chce "aktuální stav"
- Defaults odpovídají běžným use cases

---

## 🔧 Přepsání defaultů

Defaults můžete vždy přepsat explicitními parametry:

```text
// Všechny objednávky (i staré)
list_orders({ order_dir: 'asc' })

// Neaktivní produkty
list_products({ active_yn: false })

// Košíky za celý měsíc
list_carts({ creation_time_from: '2025-09-01' })

// Blokovaní zákazníci
list_customers({ active_yn: false, blocked_yn: true })
```

---

## 📊 Dopad na tokeny

S defaults (max 15 položek) místo full listu (1000+ položek):

- **Orders**: ~24k tokenů místo ~1.3M (98% úspora)
- **Products**: ~4k tokenů místo ~2M (99.8% úspora)
- **Carts**: ~5k tokenů místo ~100k (95% úspora)

**Celková úspora: Desítky až stovky tisíc tokenů na každý request!**

---

## 💡 Best Practices

1. **Nechte defaults** pro běžné dotazy
2. **Specifikujte filtry** jen když potřebujete konkrétní data
3. **Používejte stránkování** pro velké datasety
4. **Kombinujte s anonymizací** pro maximální ochranu

---

**Defaults jsou navržené pro optimální práci s AI - není třeba je měnit!** ✅
