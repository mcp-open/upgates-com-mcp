# Project Structure - Example MCP Server

## Refactored Architecture (v1.1.0)

The project has been refactored to follow clean architecture principles with separation of concerns, proper error handling, and modular design.

```
src/
├── index.ts                 # Main entry point - minimal, handles startup
├── server.ts               # MCP Server class - manages server lifecycle
├── flexibee-client.ts      # FlexiBee API client - handles API communication
├── types.ts                # TypeScript type definitions
│
├── config/
│   └── index.ts            # Configuration management and validation
│
├── errors/
│   └── index.ts            # Custom error classes for better error handling
│
├── validators/
│   └── index.ts            # Input validation utilities
│
├── handlers/
│   ├── tools.ts            # Tool request handlers
│   └── resources.ts        # Resource request handlers
│
└── tools/
    └── definitions.ts      # Tool definitions and schemas
```

## Module Responsibilities

### Core Modules

#### `index.ts`
- Application entry point
- Minimal responsibilities: config loading, server creation, error handling
- Sets up shutdown handlers for graceful termination

#### `server.ts`
- `MCPServer` class encapsulates server logic
- Sets up request handlers
- Manages FlexiBee client instance
- Handles server lifecycle

#### `flexibee-client.ts`
- FlexiBee API communication
- Request building and response processing
- Data anonymization when configured
- Error handling for API calls

### Configuration Module

#### `config/index.ts`
- Environment variable validation
- Configuration loading and structure
- Safe config generation (without passwords)
- URL validation

### Error Handling

#### `errors/index.ts`
Custom error classes hierarchy:
- `FlexiBeeError` - Base error class
- `ConfigurationError` - Configuration issues
- `AuthenticationError` - Auth failures
- `ValidationError` - Input validation errors
- `NotFoundError` - Resource not found
- `NetworkError` - Network/API errors

### Validation Module

#### `validators/index.ts`
Input validation functions:
- Date format validation (YYYY-MM-DD)
- Detail level validation
- Payment status validation
- Order direction validation
- Numeric range validation
- Pagination validation

### Handler Modules

#### `handlers/tools.ts`
- Tool request processing
- Parameter validation
- Response formatting
- Dispatches to specific tool handlers

#### `handlers/resources.ts`
- Resource reading logic
- Resource listing
- Dispatches to specific resource handlers

### Tool Definitions

#### `tools/definitions.ts`
- Centralized tool schema definitions
- Input schemas for all tools
- Tool descriptions and metadata

## Key Design Patterns

### 1. Separation of Concerns
Each module has a single, well-defined responsibility. Configuration, validation, error handling, and business logic are separated.

### 2. Dependency Injection
The `MCPServer` class receives configuration and creates its dependencies, making testing easier.

### 3. Error Hierarchy
Custom error classes provide better error handling and more informative error messages.

### 4. Validation Layer
All inputs are validated before processing, with clear error messages for invalid data.

### 5. Configuration Management
Environment variables are validated at startup with helpful error messages.

## Benefits of Refactored Structure

1. **Maintainability**: Clear module boundaries make the code easier to understand and modify
2. **Testability**: Separated modules can be unit tested independently
3. **Error Handling**: Consistent error handling with custom error types
4. **Type Safety**: Strong TypeScript typing throughout
5. **Scalability**: Easy to add new tools, resources, or validators
6. **Debugging**: Better error messages and logging

## Adding New Features

### Adding a New Tool

1. Add tool definition to `tools/definitions.ts`
2. Create handler function in `handlers/tools.ts`
3. Add validation if needed in `validators/index.ts`
4. Update type definitions in `types.ts` if needed

### Adding a New Resource

1. Create handler function in `handlers/resources.ts`
2. Add to resource list in `listResources()` function
3. Add case to `handleResourceRead()` dispatcher

### Adding New Validation

1. Add validation function to `validators/index.ts`
2. Use in appropriate handler in `handlers/tools.ts`

## Environment Variables

Managed through MCP client configuration:
- `FLEXIBEE_URL` - API server URL
- `FLEXIBEE_COMPANY` - Company identifier
- `FLEXIBEE_USERNAME` - API username
- `FLEXIBEE_PASSWORD` - API password
- `FLEXIBEE_ANONYMIZE_DATA` - Enable data anonymization

## Error Handling Flow

1. Input validation errors → `ValidationError`
2. Configuration issues → `ConfigurationError`
3. API errors → `NetworkError` or `AuthenticationError`
4. Unknown resources → `NotFoundError`
5. All errors logged with context
6. User-friendly error messages returned

## Future Improvements

- Add unit tests for each module
- Add integration tests
- Implement caching layer
- Add request/response logging
- Add metrics collection
- Implement retry logic for network errors
- Add more comprehensive input sanitization