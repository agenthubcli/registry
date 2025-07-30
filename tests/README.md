# AgentHub Registry Test Suite

This directory contains a comprehensive test suite for the AgentHub Registry backend, designed to ensure production-grade quality and reliability.

## 🧪 Test Overview

Our test suite covers:

- **Unit Tests**: Individual component testing (models, services, utilities)
- **Integration Tests**: End-to-end workflow testing
- **API Tests**: HTTP endpoint testing with authentication and validation
- **Service Tests**: Business logic and external service integration
- **Model Tests**: Database model validation and relationships

## 📁 Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                    # Pytest configuration
├── README.md                     # This file
├── test_models/                  # Database model tests
│   ├── test_user.py             # User model tests
│   └── test_package.py          # Package/Version model tests
├── test_services/               # Service layer tests
│   ├── test_auth_service.py     # Authentication service tests
│   └── test_storage_service.py  # S3 storage service tests
├── test_api/                    # API endpoint tests
│   ├── test_auth_endpoints.py   # Auth API tests
│   ├── test_package_endpoints.py # Package API tests
│   └── test_search_endpoints.py # Search API tests
└── test_integration/            # Integration tests
    └── test_complete_workflows.py # End-to-end workflows
```

## 🚀 Quick Start

### Prerequisites

Ensure you have all dependencies installed:

```bash
pip install -r requirements.txt
```

### Running Tests

#### Option 1: Using the Test Runner Script (Recommended)

```bash
# Run all tests with coverage
python scripts/run_tests.py --all --coverage

# Run only unit tests
python scripts/run_tests.py --unit --verbose

# Run fast tests (excluding slow marked tests)
python scripts/run_tests.py --fast

# Run full CI pipeline
python scripts/run_tests.py --ci

# Run linting checks
python scripts/run_tests.py --lint
```

#### Option 2: Using pytest directly

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api          # API tests only
pytest -m services     # Service tests only
pytest -m models       # Model tests only

# Run tests in specific files
pytest tests/test_models/test_user.py
pytest tests/test_api/test_auth_endpoints.py

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x
```

## 🏷️ Test Markers

We use pytest markers to categorize tests:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.services` - Service layer tests
- `@pytest.mark.models` - Database model tests
- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.external` - Tests requiring external services

## 🔧 Test Configuration

### Environment Variables

Tests use the following environment variables (automatically set by the test runner):

```bash
ENVIRONMENT=test
DATABASE_URL=sqlite+aiosqlite:///:memory:
REDIS_URL=redis://localhost:6379/15
SECRET_KEY=test-secret-key
GITHUB_CLIENT_ID=test-client-id
GITHUB_CLIENT_SECRET=test-client-secret
AWS_ACCESS_KEY_ID=test-access-key
AWS_SECRET_ACCESS_KEY=test-secret-key
S3_BUCKET_NAME=test-bucket
```

### Test Database

Tests use an in-memory SQLite database by default, which is:

- Fast and isolated
- Created fresh for each test session
- Automatically cleaned up

### Mocked Services

External services are mocked in tests:

- **S3 Storage**: `mock_s3_service` fixture
- **Redis**: `mock_redis` fixture
- **GitHub API**: `mock_httpx` fixture

## 📊 Test Coverage

Our test suite aims for high code coverage:

- **Target**: 85%+ overall coverage
- **Models**: 95%+ coverage
- **Services**: 90%+ coverage
- **API Endpoints**: 90%+ coverage

View coverage reports:

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View in browser
open htmlcov/index.html
```

## 🧩 Key Test Fixtures

### Database Fixtures

- `db_session` - Async database session for tests
- `test_engine` - Test database engine
- `test_user` - Pre-created test user
- `test_user_admin` - Pre-created admin user
- `test_package` - Pre-created test package
- `test_package_version` - Pre-created package version

### Authentication Fixtures

- `auth_headers` - Authorization headers for test user
- `admin_auth_headers` - Authorization headers for admin user
- `mock_httpx` - Mocked HTTP client for external APIs

### Service Fixtures

- `mock_s3_service` - Mocked S3 storage service
- `mock_redis` - Mocked Redis connection
- `test_settings` - Test configuration settings

### Client Fixtures

- `client` - Async HTTP client with dependency overrides
- `sync_client` - Synchronous HTTP client for simple tests

## 📝 Writing New Tests

### Test Structure

Follow this pattern for new tests:

```python
import pytest
from fastapi import status

@pytest.mark.unit  # Add appropriate markers
@pytest.mark.asyncio  # For async tests
class TestMyComponent:
    """Test cases for MyComponent."""

    async def test_success_case(self, fixture_name):
        """Test successful operation."""
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = await some_operation(input_data)

        # Assert
        assert result is not None
        assert result.status == "success"

    async def test_error_case(self, fixture_name):
        """Test error handling."""
        # Test error conditions
        with pytest.raises(ExpectedException):
            await some_operation(invalid_data)
```

### API Test Example

```python
@pytest.mark.api
@pytest.mark.asyncio
async def test_create_resource(client, auth_headers):
    """Test creating a new resource."""
    data = {"name": "test-resource"}

    response = await client.post(
        "/api/v1/resources",
        json=data,
        headers=auth_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["name"] == "test-resource"
```

### Model Test Example

```python
@pytest.mark.models
@pytest.mark.asyncio
async def test_model_creation(db_session):
    """Test model creation and validation."""
    model = MyModel(name="test", value=42)

    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    assert model.id is not None
    assert model.name == "test"
    assert model.created_at is not None
```

### Service Test Example

```python
@pytest.mark.services
@pytest.mark.asyncio
async def test_service_method(mock_external_service):
    """Test service method with mocked dependencies."""
    service = MyService()

    # Configure mock
    mock_external_service.some_method.return_value = "expected_result"

    # Test
    result = await service.do_something()

    # Verify
    assert result == "expected_result"
    mock_external_service.some_method.assert_called_once()
```

## 🔍 Test Best Practices

### 1. Test Naming

- Use descriptive test names: `test_user_creation_with_valid_data`
- Follow pattern: `test_<action>_<condition>_<expected_result>`

### 2. Test Structure

- **Arrange**: Set up test data
- **Act**: Perform the operation
- **Assert**: Verify the results

### 3. Test Isolation

- Each test should be independent
- Use fixtures for shared setup
- Clean up after tests when needed

### 4. Mocking

- Mock external dependencies (APIs, databases, files)
- Use `unittest.mock` for Python mocking
- Prefer dependency injection for easier testing

### 5. Assertions

- Use specific assertions: `assert x == y` not `assert x`
- Test both success and failure cases
- Verify error messages and status codes

### 6. Async Testing

- Use `@pytest.mark.asyncio` for async tests
- Use `await` for async operations
- Use `AsyncClient` for API testing

## 🐛 Debugging Tests

### Running Specific Tests

```bash
# Run a specific test
pytest tests/test_models/test_user.py::TestUserModel::test_create_user_success

# Run tests matching a pattern
pytest -k "test_auth"

# Run tests with print statements
pytest -s
```

### Test Debugging Tips

1. **Use `pytest.set_trace()`** for debugging:

   ```python
   def test_something():
       pytest.set_trace()  # Drops into debugger
       # ... test code
   ```

2. **Print statements in tests**:

   ```python
   def test_debug():
       print(f"Debug info: {variable}")
       # Run with: pytest -s
   ```

3. **Verbose output**:
   ```bash
   pytest -v --tb=short  # Show short traceback
   pytest -v --tb=long   # Show full traceback
   ```

## 📈 Performance Testing

### Running Performance Tests

```bash
# Run only slow tests
pytest -m slow

# Time test execution
pytest --durations=10
```

### Memory Usage

```bash
# Install memory profiler
pip install pytest-memray

# Run with memory profiling
pytest --memray
```

## 🔄 Continuous Integration

### GitHub Actions

Our CI pipeline runs:

1. **Linting**: Black, isort, flake8, mypy
2. **Security**: Bandit security checks
3. **Unit Tests**: Fast, isolated tests
4. **Integration Tests**: End-to-end workflows
5. **Coverage**: Code coverage reporting

### Local CI Simulation

```bash
# Run the full CI pipeline locally
python scripts/run_tests.py --ci
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
- [AsyncIO Testing](https://docs.python.org/3/library/asyncio-dev.html#testing)

## 🆘 Getting Help

If you encounter issues with tests:

1. Check the test output for specific error messages
2. Verify all dependencies are installed: `pip install -r requirements.txt`
3. Ensure Redis is running for integration tests
4. Check environment variables are set correctly
5. Look at similar existing tests for patterns

For questions or issues, please:

- Check existing tests for examples
- Review this documentation
- Ask team members for guidance
- Update tests when fixing bugs or adding features
