"""
Shared test fixtures and configuration for AgentHub Registry tests.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_db, get_redis_connection
from app.main import app
from app.models.user import User
from app.models.package import Package, PackageVersion, PackageType, VersionStatus
from app.services.auth import auth_service
from app.services.storage import storage_service


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with overrides."""
    return Settings(
        ENVIRONMENT="test",
        DEBUG=True,
        LOG_LEVEL="DEBUG",
        SECRET_KEY="test-secret-key-for-testing-only",
        DATABASE_URL=TEST_DATABASE_URL,
        REDIS_URL="redis://localhost:6379/15",  # Use test DB
        AWS_ACCESS_KEY_ID="test-access-key",
        AWS_SECRET_ACCESS_KEY="test-secret-key",
        AWS_REGION="us-east-1",
        S3_BUCKET_NAME="test-bucket",
        GITHUB_CLIENT_ID="test-github-client-id",
        GITHUB_CLIENT_SECRET="test-github-client-secret",
        GITHUB_OAUTH_REDIRECT_URI="http://localhost:8000/api/v1/auth/github/callback",
        ALLOWED_HOSTS=["testserver", "localhost"],
        RATE_LIMIT_PER_MINUTE=1000,  # High limit for tests
        MAX_PACKAGE_SIZE_MB=10,  # Smaller for tests
        ENABLE_PACKAGE_DELETION=True,  # Enable for testing
        ENABLE_VIRUS_SCANNING=False,  # Disable for tests
        ENABLE_VULNERABILITY_SCANNING=False,  # Disable for tests
    )


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.close.return_value = None
    return mock_redis


@pytest.fixture
def mock_s3_service():
    """Mock S3 storage service."""
    mock_s3 = AsyncMock()
    mock_s3.upload_package.return_value = ("test-s3-key", "test-hash", 1024)
    mock_s3.download_package.return_value = b"test package content"
    mock_s3.delete_package.return_value = True
    mock_s3.get_package_info.return_value = {
        "size": 1024,
        "last_modified": "2024-01-01T00:00:00Z",
        "etag": "test-etag",
        "content_type": "application/octet-stream",
        "metadata": {},
    }
    mock_s3.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key"
    mock_s3.get_public_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key"
    return mock_s3


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    return {
        "token_exchange": {
            "access_token": "gho_test_token",
            "token_type": "bearer",
            "scope": "read:user user:email"
        },
        "user_info": {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://github.com/avatars/testuser",
            "bio": "Test user bio",
            "blog": "https://testuser.dev",
            "location": "Test City",
            "company": "Test Company",
            "primary_email": "test@example.com",
            "all_emails": [
                {"email": "test@example.com", "primary": True, "verified": True}
            ]
        }
    }


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        github_id=12345,
        github_username="testuser",
        github_email="test@example.com",
        github_avatar_url="https://github.com/avatars/testuser",
        display_name="Test User",
        bio="Test user bio",
        website="https://testuser.dev",
        location="Test City",
        company="Test Company",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        github_id=99999,
        github_username="adminuser",
        github_email="admin@example.com",
        github_avatar_url="https://github.com/avatars/adminuser",
        display_name="Admin User",
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_package(db_session: AsyncSession, test_user: User) -> Package:
    """Create a test package."""
    package = Package(
        name="test-package",
        normalized_name="test-package",
        description="A test package for unit testing",
        package_type=PackageType.TOOL,
        owner_id=test_user.id,
        latest_version="1.0.0",
        total_downloads=100,
        download_count_last_30_days=50,
        version_count=1,
        keywords=["test", "tool", "automation"],
    )
    db_session.add(package)
    await db_session.commit()
    await db_session.refresh(package)
    return package


@pytest_asyncio.fixture
async def test_package_version(
    db_session: AsyncSession, test_package: Package, test_user: User
) -> PackageVersion:
    """Create a test package version."""
    version = PackageVersion(
        package_id=test_package.id,
        version="1.0.0",
        description="Test version",
        filename="test-package-1.0.0.tar.gz",
        file_size=1024,
        file_hash_sha256="test-hash-sha256",
        s3_key="packages/test-package/1.0.0/test-package-1.0.0.tar.gz",
        manifest={
            "name": "test-package",
            "version": "1.0.0",
            "type": "tool",
            "description": "Test package",
        },
        status=VersionStatus.PUBLISHED,
        published_by_id=test_user.id,
        download_count=100,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)
    return version


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    token = auth_service.create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_user_admin: User) -> dict:
    """Create authentication headers for admin user."""
    token = auth_service.create_access_token(test_user_admin.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, mock_redis, mock_s3_service) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with dependency overrides."""
    
    async def override_get_db():
        yield db_session
    
    async def override_get_redis():
        return mock_redis
    
    def override_storage_service():
        return mock_s3_service
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_connection] = override_get_redis
    
    # Override storage service
    import app.services.storage
    app.services.storage.storage_service = mock_s3_service
    
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    """Create synchronous test client for simple tests."""
    with TestClient(app) as client:
        yield client


class MockHTTPXResponse:
    """Mock httpx response for testing external API calls."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    
    def json(self):
        return self.json_data


@pytest.fixture
def mock_httpx(monkeypatch):
    """Mock httpx requests for external API calls."""
    async def mock_post(*args, **kwargs):
        # Mock GitHub token exchange
        if "github.com/login/oauth/access_token" in str(args[0]):
            return MockHTTPXResponse({
                "access_token": "gho_test_token",
                "token_type": "bearer",
                "scope": "read:user user:email"
            })
        return MockHTTPXResponse({})
    
    async def mock_get(*args, **kwargs):
        # Mock GitHub user info
        if "api.github.com/user" in str(args[0]):
            return MockHTTPXResponse({
                "id": 12345,
                "login": "testuser",
                "name": "Test User",
                "email": "test@example.com",
                "avatar_url": "https://github.com/avatars/testuser",
                "bio": "Test user bio",
                "blog": "https://testuser.dev",
                "location": "Test City",
                "company": "Test Company",
            })
        # Mock GitHub user emails
        elif "api.github.com/user/emails" in str(args[0]):
            return MockHTTPXResponse([
                {"email": "test@example.com", "primary": True, "verified": True}
            ])
        return MockHTTPXResponse({})
    
    # Patch httpx methods
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)


@pytest.fixture
def sample_package_file():
    """Create a sample package file for upload tests."""
    content = b"Test package content for upload testing"
    return {
        "filename": "test-package-1.0.0.tar.gz",
        "content": content,
        "content_type": "application/gzip",
        "size": len(content)
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    yield
    # Reset any global state or singletons if needed


# Test data generators
class TestDataFactory:
    """Factory for generating test data."""
    
    @staticmethod
    def create_user_data(**overrides):
        """Create user data for testing."""
        default_data = {
            "github_id": 12345,
            "github_username": "testuser",
            "github_email": "test@example.com",
            "github_avatar_url": "https://github.com/avatars/testuser",
            "display_name": "Test User",
            "bio": "Test bio",
            "website": "https://testuser.dev",
            "location": "Test City",
            "company": "Test Company",
            "is_verified": True,
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_package_data(**overrides):
        """Create package data for testing."""
        default_data = {
            "name": "test-package",
            "normalized_name": "test-package",
            "description": "A test package",
            "package_type": PackageType.TOOL,
            "keywords": ["test", "tool"],
        }
        default_data.update(overrides)
        return default_data
    
    @staticmethod
    def create_package_manifest(**overrides):
        """Create package manifest for testing."""
        default_manifest = {
            "name": "test-package",
            "version": "1.0.0",
            "type": "tool",
            "description": "Test package description",
            "author": "test@example.com",
            "license": "MIT",
            "runtime": "python",
            "entry_point": "main.py",
            "tags": ["test", "tool", "automation"],
        }
        default_manifest.update(overrides)
        return default_manifest


@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory 