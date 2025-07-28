# AgentHub Registry API - Curl Examples

## GET /
Get web UI

```bash
curl -X GET \
  "http://localhost:8000/"
```

## GET /api
Get API information

```bash
curl -X GET \
  "http://localhost:8000/api"
```

## GET /health
Basic health check

```bash
curl -X GET \
  "http://localhost:8000/health"
```

## GET /metrics
Prometheus metrics

```bash
curl -X GET \
  "http://localhost:8000/metrics"
```

## GET /api/v1/auth/github
Initiate GitHub OAuth

```bash
curl -X GET \
  "http://localhost:8000/api/v1/auth/github"
```

## GET /api/v1/auth/github/callback
GitHub OAuth callback

```bash
curl -X GET \
  "http://localhost:8000/api/v1/auth/github/callback"
```

## POST /api/v1/auth/refresh
Refresh access token

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/auth/refresh"
```

## GET /api/v1/auth/me
Get current user

```bash
curl -X GET \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "http://localhost:8000/api/v1/auth/me"
```

## POST /api/v1/auth/logout
Logout

```bash
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/auth/logout"
```

## POST /api/v1/packages/publish
Publish package

```bash
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/packages/publish"
```

## GET /api/v1/packages/{package_name}
Get package details

```bash
curl -X GET \
  "http://localhost:8000/api/v1/packages/test-package"
```

## DELETE /api/v1/packages/{package_name}
Delete package

```bash
curl -X DELETE \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "http://localhost:8000/api/v1/packages/test-package"
```

## GET /api/v1/packages/{package_name}/versions
Get package versions

```bash
curl -X GET \
  "http://localhost:8000/api/v1/packages/test-package/versions"
```

## GET /api/v1/packages/{package_name}/{version}
Get specific version

```bash
curl -X GET \
  "http://localhost:8000/api/v1/packages/test-package/1.0.0"
```

## GET /api/v1/packages/{package_name}/{version}/download
Download package

```bash
curl -X GET \
  "http://localhost:8000/api/v1/packages/test-package/1.0.0/download"
```

## GET /api/v1/packages/{package_name}/stats
Get package statistics

```bash
curl -X GET \
  "http://localhost:8000/api/v1/packages/test-package/stats"
```

## GET /api/v1/search/
Search packages

```bash
curl -X GET \
  "http://localhost:8000/api/v1/search/"
```

## GET /api/v1/search/popular
Get popular packages

```bash
curl -X GET \
  "http://localhost:8000/api/v1/search/popular"
```

## GET /api/v1/search/recent
Get recent packages

```bash
curl -X GET \
  "http://localhost:8000/api/v1/search/recent"
```

## GET /api/v1/search/trending
Get trending packages

```bash
curl -X GET \
  "http://localhost:8000/api/v1/search/trending"
```

## GET /api/v1/users/{username}
Get user profile

```bash
curl -X GET \
  "http://localhost:8000/api/v1/users/testuser"
```

## GET /api/v1/users/{username}/packages
Get user packages

```bash
curl -X GET \
  "http://localhost:8000/api/v1/users/testuser/packages"
```

## GET /api/v1/health/
Basic health check

```bash
curl -X GET \
  "http://localhost:8000/api/v1/health/"
```

## GET /api/v1/health/detailed
Detailed health check

```bash
curl -X GET \
  "http://localhost:8000/api/v1/health/detailed"
```

