# Changelog

All notable changes to Upgates MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Záznamy do verzie 0.1.x popisujú pôvodnú **TypeScript** implementáciu.
> Od 0.2.0 je konektor v Pythone nad `openmcp-sdk`.

## [Unreleased]

### Odstránené

- **TypeScript strom** (`src/*.ts`, `package.json`, `tsconfig.json`) —
  nahradený Python implementáciou v `src/connector/` (commit `a8f71aa`).
  Dohľadateľný v git histórii.

### Opravené (dokumentácia)

- `README.md` a `docs/tools.md` tvrdili **34 nástrojov vrátane zapisovacích**
  (`create_order`, `update_orders`, `delete_orders`). Tie existovali len v TS
  verzii; Python konektor registruje **23 čítacích** nástrojov a `egress`
  povoľuje výhradne `GET`. Read-only konektor teda inzeroval zápis.
- `CONTRIBUTING.md` a `dev-docs/project-structure.md` navádzali na súbory,
  ktoré už neexistujú.

## [0.1.0] - 2025-10-09

### 🎉 Initial Release

First public release of Upgates MCP Server - Model Context Protocol server for Upgates e-shop API v2 integration.

### ✨ Added

#### LLM Optimization (Token Efficiency)
- **Automatic response optimization** for all list endpoints
- **82-99.8% token reduction** depending on endpoint
  - Orders: 82.2% reduction (~110k tokens saved per 100 orders)
  - Products: 99.8% reduction (~2M tokens saved per 50 products)
  - Customers: ~80% reduction
  - Invoices: ~85% reduction
  - Carts: ~75% reduction
- **Field filtering** - keeps only essential fields
  - Orders: 16 fields instead of 38
  - Products: 13 fields instead of 50+
  - Customers: 12 fields instead of 30+
- **Multi-language deduplication** - first language only
- **Nested object flattening** - products summary instead of full details
- **No configuration needed** - works automatically

#### Core Features
- **34 Tools** covering main Upgates API endpoints
  - Orders: list, create, update, delete, history (5 tools)
  - Order Statuses: list, create (2 tools)
  - Products: list, list_simple, create, update, delete (5 tools)
  - Customers: list, create (2 tools)
  - Categories: list, create (2 tools)
  - Invoices: list (1 tool)
  - Labels: list (1 tool)
  - Availabilities: list (1 tool)
  - Manufacturers: list (1 tool)
  - Parameters: list (1 tool)
  - Carts: list (1 tool)
  - Vouchers: list, create (2 tools)
  - Shipments: list (1 tool)
  - Payments: list (1 tool)
  - Webhooks: list, create, list_events (3 tools)
  - System: languages, config, owner, api_status, pricelists (5 tools)

- **5 Resources** with comprehensive documentation
  - `upgates://system/info` - Server capabilities and features
  - `upgates://api/endpoints` - API endpoint overview
  - `upgates://api/rate-limits` - Rate limiting information
  - `upgates://config/settings` - Server configuration
  - `upgates://api/documentation` - Documentation links

#### Security Features
- **HTTP Basic Authentication** - Standard RFC 7617 authentication
- **Readonly Mode** - Protection against accidental data modifications
  - Blocks all write operations (create, update, delete)
  - Allows all read operations (list, get)
  - Clear error messages for blocked operations
- **GDPR Data Anonymization** - Comprehensive PII protection
  - 40+ sensitive fields anonymized
  - Email, phone, names, addresses
  - Business identifiers (IČO, DIČ, IBAN, SWIFT)
  - Deep anonymization for nested objects and arrays
  - Pattern matching for dynamic fields

#### Architecture
- **Clean Architecture** - Modular design with separation of concerns
- **TypeScript** - Full type safety with strict mode (2,716 lines)
- **Error Handling** - 8 custom error classes
  - UpgatesError, ConfigurationError, AuthenticationError
  - ValidationError, NotFoundError, NetworkError
  - RateLimitError, ReadonlyError
- **Validation Layer** - Comprehensive input validation
  - Date format validation (ISO 8601)
  - Pagination validation
  - ID format validation
  - Email validation
- **Rate Limit Handling** - Graceful handling of API limits
  - Response header parsing
  - Retry-After support
  - Clear error messages

#### Testing
- **35 Unit Tests** - 100% pass rate
  - Error classes (10 tests)
  - Tool handlers (2 tests)
  - Validators (11 tests)
  - Anonymization (12 tests)
- **Integration Tests** - Tested against live Upgates API
  - EdgarPower shop (23,789 orders, 87 products)
  - 6 languages (cs, en, hu, sk, de, pl)
  - All read operations verified

#### Documentation
- **README.md** - User-friendly Czech documentation
- **TEST_REPORT.md** - Comprehensive test report
- **CHANGELOG.md** - This file
- Inline code documentation with JSDoc comments
- API endpoint mapping from official Upgates API v2 docs

#### Configuration
- Environment variable based configuration
- Required: UPGATES_API_URL, UPGATES_API_USERNAME, UPGATES_API_PASSWORD
- Optional: UPGATES_TIMEOUT, UPGATES_READONLY, UPGATES_ANONYMIZE_DATA
- Validation on startup with helpful error messages
- Safe config logging (credentials never exposed)

### 🔧 Technical Details

#### Dependencies
- `@modelcontextprotocol/sdk` - MCP protocol implementation
- `axios` - HTTP client for API communication
- `typescript` - Type safety and compilation
- `tsx` - TypeScript test execution

#### Supported Upgates API v2 Groups
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

#### API Limits Supported
- Rate limit tiers (Bronze to Exclusive)
- Concurrent request limiting (max 3)
- Bulk operations (max 100 items)
- Pagination (50-100 items per page)
- Response header parsing for remaining limits

### 📝 Known Limitations

- API user permissions are server-side configured
- Some endpoints require specific permissions to work
- Write operations require `UPGATES_READONLY=false`
- PDF generation endpoints not yet implemented

### 🎯 Future Enhancements

Planned for future releases:
- PDF download support (invoices, orders)
- Additional endpoint groups (Articles, News, Advisor, Files)
- Stock management tools
- Custom field (Metas) support
- Graphics and backup management
- Conversion code management
- More comprehensive integration tests

---

## How to Upgrade

### From scratch to 0.1.0

This is the initial release, so just install:

```bash
git clone https://github.com/LukasOrcik/upgates-com-mcp.git
cd upgates-com-mcp
npm install
npm run build
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
# Clone repository
git clone https://github.com/LukasOrcik/upgates-com-mcp.git
cd upgates-com-mcp

# Install dependencies
npm install

# Run in development mode
npm run dev

# Run tests
npm test
```

---

## Links

- **Homepage**: https://openmcp.cz
- **Repository**: https://github.com/LukasOrcik/upgates-com-mcp
- **Issues**: https://github.com/LukasOrcik/upgates-com-mcp/issues
- **Upgates API Docs**: https://upgatesapiv2.docs.apiary.io/
- **Model Context Protocol**: https://modelcontextprotocol.io/

---

**Note**: This is a community project and is not officially affiliated with Upgates.
