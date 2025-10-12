[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/mcp-open-upgates-com-mcp-badge.png)](https://mseep.ai/app/mcp-open-upgates-com-mcp)

# Upgates MCP Server

> **AI asistent pro automatizaci Upgates e-shopů**

Model Context Protocol (MCP) server pro propojení s Upgates e-shop API v2.

[![License](https://img.shields.io/badge/License-CC--BY--NC--4.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)

---

## 🚀 Rychlý start

### 1. Instalace

```bash
git clone https://github.com/LukasOrcik/upgates-com-mcp.git
cd upgates-com-mcp
npm install
npm run build
```

### 2. Konfigurace

Vytvořte API přístup v **Upgates Admin > Doplňky > API** a přidejte do `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "upgates": {
      "command": "node",
      "args": ["/absolute/path/to/upgates-com-mcp/dist/index.js"],
      "env": {
        "UPGATES_API_URL": "https://your-shop.admin.s17.upgates.com/api/v2",
        "UPGATES_API_USERNAME": "your-api-username",
        "UPGATES_API_PASSWORD": "your-api-key",
        "UPGATES_READONLY": "true",
        "UPGATES_ANONYMIZE_DATA": "true"
      }
    }
  }
}
```

Viz [.mcp.example.json](.mcp.example.json) pro template.

### 3. Použití v Claude AI

```
"Kolik máme dnes objednávek?"
"Které produkty jsou vyprodané?"
"Seznam nedokončených košíků za poslední týden"
```

---

## 📦 Dostupné nástroje (34)

| Kategorie | Count | Příklady |
|-----------|-------|----------|
| Objednávky | 5 | list, create, update, delete, history |
| Produkty | 5 | list, list_simple, create, update, delete |
| Zákazníci | 2 | list, create |
| Faktury | 1 | list |
| Košíky | 1 | list |
| Kupóny | 2 | list, create |
| Webhooky | 3 | list, create, events |
| Číselníky | 9 | statuses, labels, payments, shipments... |
| Konfigurace | 4 | languages, config, owner, api_status |

**[Kompletní seznam →](docs/tools.md)**

---

## 🔒 Bezpečnost

### GDPR Anonymizace
```bash
UPGATES_ANONYMIZE_DATA=true  # Anonymizuje 40+ polí
```
**[Více →](docs/anonymization.md)**

### Readonly režim
```bash
UPGATES_READONLY=true  # Blokuje write operace
```
**[Více →](docs/readonly.md)**

---

## 📚 Dokumentace

### Uživatelská
- **[Nástroje](docs/tools.md)** - Seznam všech 34 nástrojů
- **[Smart Defaults](docs/defaults.md)** - Výchozí hodnoty a filtry
- **[Anonymizace](docs/anonymization.md)** - GDPR ochrana

### Provozní
- **[Production](PRODUCTION.md)** - Deployment checklist
- **[Changelog](CHANGELOG.md)** - Historie verzí
- **[Release Notes](RELEASE.md)** - v0.1.0 release

### Vývojářská
- **[Contributing](CONTRIBUTING.md)** - Jak přispět
- **[GitHub Issues](.github/README.md)** - Issue templates

### Externí
- **[Upgates API Docs](https://upgatesapiv2.docs.apiary.io/)**

---

## 📊 Statistiky

- **Kód:** 2,716 řádků TypeScript
- **Testy:** 23/23 passing (100%)
- **Build:** ~2 sekundy
- **Optimalizace:** 82-99.8% token reduction
- **Testováno:** EdgarPower shop (23,794 orders, 87 products)

---

## 🤝 Podpora a komunita

### Máte problém nebo nápad?

- 🐛 **[Nahlásit chybu](https://github.com/LukasOrcik/upgates-com-mcp/issues/new?template=bug_report.yml)**
- ✨ **[Navrhnout funkci](https://github.com/LukasOrcik/upgates-com-mcp/issues/new?template=feature_request.yml)**
- 🚀 **[Navrhnout vylepšení](https://github.com/LukasOrcik/upgates-com-mcp/issues/new?template=improvement.yml)**
- 💬 **[Diskuze](https://github.com/LukasOrcik/upgates-com-mcp/discussions)**

### Komunita

- **[GitHub Discussions](https://github.com/LukasOrcik/upgates-com-mcp/discussions)** - Otázky a tipy

---

## ⚡ Rychlé odkazy

- **[Instalace](#-rychlý-start)** - Jak začít
- **[Konfigurace](#2-konfigurace)** - Nastavení
- **[Nástroje](docs/tools.md)** - Co můžete dělat
- **[Production](PRODUCTION.md)** - Nasazení
- **[Contributing](CONTRIBUTING.md)** - Jak přispět

---

## 📄 Licence

[CC-BY-NC-4.0](LICENSE) - Attribution-NonCommercial 4.0 International

**Pro komerční využití** kontaktujte autora.

---

## 👨‍💻 Autor

**Lukáš Orčík**
Neziskový projekt [OpenMCP](https://openmcp.cz)
Specialista na e-commerce automatizaci a AI integrace

**Repository:** https://github.com/LukasOrcik/upgates-com-mcp

---

<p align="center">
  <strong>Automatizujte svůj Upgates e-shop s AI!</strong> 🚀
</p>
