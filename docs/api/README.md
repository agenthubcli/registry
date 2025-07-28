# AgentHub Registry API Documentation

This directory contains comprehensive API documentation and testing resources for the AgentHub Registry.

## 📁 Files Overview

### API Specification

- **`../../api-spec.yaml`** - Complete OpenAPI 3.0 specification
  - Comprehensive endpoint documentation
  - Request/response schemas
  - Authentication requirements
  - Error handling

### Testing Resources

- **`sample-requests.json`** - Sample API requests for CLI testing
  - Pre-defined test scenarios
  - Expected response codes
  - CLI examples (curl, httpie, agenthub)
  - Response examples

### Generated Documentation

- **`agenthub-registry.postman_collection.json`** - Postman collection

  - Import into Postman for interactive testing
  - Organized by endpoint categories
  - Authentication pre-configured

- **`curl-examples.md`** - Curl command examples
  - Ready-to-use curl commands for each endpoint
  - Copy-paste friendly format
  - Authentication examples

## 🚀 Quick Start

### 1. Validate API Specification

```bash
# Validate the OpenAPI spec
python scripts/validate_api_spec.py

# Generate all documentation
python scripts/validate_api_spec.py --generate-all
```

### 2. Test API Endpoints

```bash
# Test API connectivity (when server is running)
python scripts/validate_api_spec.py --test-api

# Test specific number of endpoints
python scripts/validate_api_spec.py --test-api --max-endpoints 5
```

### 3. Use with CLI Tools

#### Curl Examples

```bash
# Health check
curl http://localhost:8000/health

# Search packages
curl 'http://localhost:8000/api/v1/search/?q=tool&limit=5'

# Get package details
curl http://localhost:8000/api/v1/packages/example-tool

# Authenticated request
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     http://localhost:8000/api/v1/auth/me
```

#### HTTPie Examples

```bash
# Search packages
http GET localhost:8000/api/v1/search/ q==tool limit==5

# Download package
http --download GET localhost:8000/api/v1/packages/example-tool/1.0.0/download

# Authenticated request
http GET localhost:8000/api/v1/auth/me Authorization:"Bearer $ACCESS_TOKEN"
```

#### AgentHub CLI Examples

```bash
# Search for packages
agenthub search tool --limit 5

# Install a package
agenthub install tool:example-tool@1.0.0

# Publish a package (requires auth)
agenthub login
agenthub publish my-package.tar.gz --type tool
```

## 📋 API Endpoints Summary

### Authentication (`/api/v1/auth/`)

- `GET /github` - Initiate GitHub OAuth
- `GET /github/callback` - OAuth callback handler
- `POST /refresh` - Refresh access token
- `GET /me` - Get current user
- `POST /logout` - Logout user

### Package Management (`/api/v1/packages/`)

- `POST /publish` - Publish new package/version
- `GET /{name}` - Get package details
- `GET /{name}/versions` - Get all package versions
- `GET /{name}/{version}` - Get specific version details
- `GET /{name}/{version}/download` - Download package
- `GET /{name}/stats` - Get package statistics
- `DELETE /{name}` - Delete package (admin/owner)

### Search & Discovery (`/api/v1/search/`)

- `GET /` - Search packages
- `GET /popular` - Get popular packages
- `GET /recent` - Get recent packages
- `GET /trending` - Get trending packages

### User Management (`/api/v1/users/`)

- `GET /{username}` - Get user profile
- `GET /{username}/packages` - Get user's packages

### Health & Monitoring

- `GET /health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health check
- `GET /metrics` - Prometheus metrics

## 🔧 Environment Configuration

### Development

```bash
export BASE_URL="http://localhost:8000"
export ACCESS_TOKEN="your-jwt-token-here"
```

### Production

```bash
export BASE_URL="https://registry.agenthubcli.com"
export ACCESS_TOKEN="your-jwt-token-here"
```

## 📊 Testing Scenarios

### 1. Unauthenticated User Flow

- API info → Health check → Search → Package details → Download

### 2. Package Discovery Flow

- Search by query → Filter by type → Browse popular/recent/trending

### 3. Authenticated User Flow

- OAuth login → Get profile → Publish package → Manage packages

### 4. CLI Integration Testing

- Use `sample-requests.json` for systematic testing
- Test all endpoints with expected response codes
- Verify authentication requirements

## 🛠️ CLI Integration

### For AgentHub CLI Development

1. **Load API Specification**:

   ```go
   // Load OpenAPI spec for endpoint validation
   spec, err := loadOpenAPISpec("api-spec.yaml")
   ```

2. **Use Sample Requests**:

   ```go
   // Load test scenarios
   samples, err := loadSampleRequests("docs/api/sample-requests.json")
   ```

3. **Validate Responses**:
   ```go
   // Validate API responses against schema
   err := validateResponse(response, spec)
   ```

### Testing Integration

```bash
# Run CLI tests against the API
go test ./... -tags=integration -api-url=http://localhost:8000

# Test specific CLI commands
agenthub search test --dry-run
agenthub install tool:example@1.0.0 --dry-run
```

## 📚 Additional Resources

- **OpenAPI Specification**: [OpenAPI 3.0](https://swagger.io/specification/)
- **Postman Documentation**: [Postman Collections](https://learning.postman.com/docs/getting-started/creating-the-first-collection/)
- **HTTP Status Codes**: [MDN HTTP Status](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- **JWT Authentication**: [JWT.io](https://jwt.io/)

## 🔄 Regenerating Documentation

To regenerate the API documentation after spec changes:

```bash
# Validate and regenerate all docs
python scripts/validate_api_spec.py --generate-all

# Or generate specific formats
python scripts/validate_api_spec.py --generate-postman docs/api/collection.json
python scripts/validate_api_spec.py --generate-curl docs/api/examples.md
```

## 🆘 Troubleshooting

### Common Issues

1. **Validation Errors**: Check OpenAPI spec syntax in `api-spec.yaml`
2. **Connection Errors**: Ensure the registry server is running on the correct port
3. **Authentication Errors**: Verify JWT token is valid and not expired
4. **Rate Limiting**: Wait before retrying requests

### Getting Help

- Review the OpenAPI specification for endpoint details
- Check sample requests for proper usage patterns
- Use curl examples for quick testing
- Import Postman collection for interactive exploration
