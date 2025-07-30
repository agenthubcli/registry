"""
Tests for authentication service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, Mock
from jose import jwt

from app.services.auth import AuthService, auth_service
from app.models.user import User
from app.core.config import settings


@pytest.mark.services
@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthService:
    """Test cases for AuthService."""
    
    def test_get_github_oauth_url(self):
        """Test GitHub OAuth URL generation."""
        auth = AuthService()
        
        # Test with default state
        url = auth.get_github_oauth_url()
        
        assert "https://github.com/login/oauth/authorize" in url
        assert f"client_id={settings.GITHUB_CLIENT_ID}" in url
        assert f"redirect_uri={settings.GITHUB_OAUTH_REDIRECT_URI}" in url
        assert "scope=read:user user:email" in url
        assert "state=" in url
        assert "allow_signup=true" in url
    
    def test_get_github_oauth_url_with_custom_state(self):
        """Test GitHub OAuth URL generation with custom state."""
        auth = AuthService()
        custom_state = "custom-state-value"
        
        url = auth.get_github_oauth_url(custom_state)
        
        assert f"state={custom_state}" in url
    
    async def test_exchange_code_for_token_success(self, mock_httpx):
        """Test successful OAuth code exchange."""
        auth = AuthService()
        
        result = await auth.exchange_code_for_token("test_code")
        
        assert result["access_token"] == "gho_test_token"
        assert result["token_type"] == "bearer"
        assert result["scope"] == "read:user user:email"
    
    async def test_exchange_code_for_token_error_response(self):
        """Test OAuth code exchange with error response."""
        auth = AuthService()
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_post.return_value = mock_response
            
            with pytest.raises(ValueError, match="GitHub OAuth error: invalid_grant"):
                await auth.exchange_code_for_token("invalid_code")
    
    async def test_exchange_code_for_token_network_error(self):
        """Test OAuth code exchange with network error."""
        auth = AuthService()
        
        with patch("httpx.AsyncClient.post", side_effect=Exception("Network error")):
            with pytest.raises(ValueError, match="Failed to communicate with GitHub"):
                await auth.exchange_code_for_token("test_code")
    
    async def test_get_github_user_info_success(self, mock_httpx):
        """Test successful GitHub user info retrieval."""
        auth = AuthService()
        
        result = await auth.get_github_user_info("gho_test_token")
        
        assert result["id"] == 12345
        assert result["login"] == "testuser"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["primary_email"] == "test@example.com"
        assert len(result["all_emails"]) == 1
    
    async def test_get_github_user_info_api_error(self):
        """Test GitHub user info retrieval with API error."""
        auth = AuthService()
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_get.return_value = mock_response
            
            with pytest.raises(ValueError, match="Failed to get user info from GitHub"):
                await auth.get_github_user_info("invalid_token")
    
    async def test_create_or_update_user_new_user(self, db_session):
        """Test creating a new user from GitHub data."""
        auth = AuthService()
        
        github_data = {
            "id": 12345,
            "login": "newuser",
            "name": "New User",
            "email": "new@example.com",
            "primary_email": "new@example.com",
            "avatar_url": "https://github.com/avatars/newuser",
            "bio": "New user bio",
            "blog": "https://newuser.dev",
            "location": "New City",
            "company": "New Company",
        }
        
        user = await auth.create_or_update_user(db_session, github_data, "token")
        
        assert user.id is not None
        assert user.github_id == 12345
        assert user.github_username == "newuser"
        assert user.github_email == "new@example.com"
        assert user.display_name == "New User"
        assert user.bio == "New user bio"
        assert user.website == "https://newuser.dev"
        assert user.location == "New City"
        assert user.company == "New Company"
        assert user.is_verified is True  # GitHub users are pre-verified
        assert user.last_login_at is not None
    
    async def test_create_or_update_user_existing_user(self, db_session, test_user):
        """Test updating an existing user from GitHub data."""
        auth = AuthService()
        
        # Updated GitHub data
        github_data = {
            "id": test_user.github_id,
            "login": test_user.github_username,
            "name": "Updated Name",
            "email": "updated@example.com",
            "primary_email": "updated@example.com",
            "avatar_url": "https://github.com/avatars/updated",
            "bio": "Updated bio",
            "blog": "https://updated.dev",
            "location": "Updated City",
            "company": "Updated Company",
        }
        
        original_created_at = test_user.created_at
        updated_user = await auth.create_or_update_user(db_session, github_data, "new_token")
        
        assert updated_user.id == test_user.id  # Same user
        assert updated_user.display_name == "Updated Name"
        assert updated_user.github_email == "updated@example.com"
        assert updated_user.bio == "Updated bio"
        assert updated_user.website == "https://updated.dev"
        assert updated_user.location == "Updated City"
        assert updated_user.company == "Updated Company"
        assert updated_user.created_at == original_created_at  # Should not change
        assert updated_user.last_login_at is not None
    
    def test_create_access_token(self):
        """Test access token creation."""
        auth = AuthService()
        user_id = 123
        
        token = auth.create_access_token(user_id)
        
        assert isinstance(token, str)
        
        # Decode and verify token
        payload = jwt.decode(token, auth.secret_key, algorithms=[auth.algorithm])
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_access_token_with_custom_expiry(self):
        """Test access token creation with custom expiry."""
        auth = AuthService()
        user_id = 123
        custom_expiry = timedelta(minutes=30)
        
        token = auth.create_access_token(user_id, custom_expiry)
        
        payload = jwt.decode(token, auth.secret_key, algorithms=[auth.algorithm])
        
        # Check expiry is approximately 30 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + custom_expiry
        
        # Allow 10 seconds tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 10
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        auth = AuthService()
        user_id = 123
        
        token = auth.create_refresh_token(user_id)
        
        assert isinstance(token, str)
        
        # Decode and verify token
        payload = jwt.decode(token, auth.secret_key, algorithms=[auth.algorithm])
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_token_valid_access_token(self):
        """Test verifying a valid access token."""
        auth = AuthService()
        user_id = 123
        
        token = auth.create_access_token(user_id)
        payload = auth.verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
    
    def test_verify_token_valid_refresh_token(self):
        """Test verifying a valid refresh token."""
        auth = AuthService()
        user_id = 123
        
        token = auth.create_refresh_token(user_id)
        payload = auth.verify_token(token, "refresh")
        
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
    
    def test_verify_token_wrong_type(self):
        """Test verifying token with wrong type."""
        auth = AuthService()
        user_id = 123
        
        access_token = auth.create_access_token(user_id)
        
        # Try to verify as refresh token
        payload = auth.verify_token(access_token, "refresh")
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test verifying an expired token."""
        auth = AuthService()
        user_id = 123
        
        # Create token that expires immediately
        expired_token = auth.create_access_token(user_id, timedelta(seconds=-1))
        
        payload = auth.verify_token(expired_token, "access")
        assert payload is None
    
    def test_verify_token_invalid(self):
        """Test verifying an invalid token."""
        auth = AuthService()
        
        payload = auth.verify_token("invalid.token.here", "access")
        assert payload is None
    
    async def test_get_user_by_token_success(self, db_session, test_user):
        """Test getting user by valid token."""
        auth = AuthService()
        
        token = auth.create_access_token(test_user.id)
        user = await auth.get_user_by_token(db_session, token)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.github_username == test_user.github_username
    
    async def test_get_user_by_token_invalid_token(self, db_session):
        """Test getting user by invalid token."""
        auth = AuthService()
        
        user = await auth.get_user_by_token(db_session, "invalid.token")
        assert user is None
    
    async def test_get_user_by_token_nonexistent_user(self, db_session):
        """Test getting user by token for non-existent user."""
        auth = AuthService()
        
        # Create token for non-existent user
        token = auth.create_access_token(99999)
        user = await auth.get_user_by_token(db_session, token)
        
        assert user is None
    
    async def test_get_user_by_token_inactive_user(self, db_session):
        """Test getting inactive user by token."""
        auth = AuthService()
        
        # Create inactive user
        inactive_user = User(
            github_id=99999,
            github_username="inactiveuser",
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()
        await db_session.refresh(inactive_user)
        
        token = auth.create_access_token(inactive_user.id)
        user = await auth.get_user_by_token(db_session, token)
        
        assert user is None  # Should not return inactive user
    
    async def test_refresh_access_token_success(self, db_session, test_user):
        """Test refreshing access token with valid refresh token."""
        auth = AuthService()
        
        refresh_token = auth.create_refresh_token(test_user.id)
        new_access_token = await auth.refresh_access_token(db_session, refresh_token)
        
        assert new_access_token is not None
        assert isinstance(new_access_token, str)
        
        # Verify new token is valid
        payload = auth.verify_token(new_access_token, "access")
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
    
    async def test_refresh_access_token_invalid_refresh_token(self, db_session):
        """Test refreshing access token with invalid refresh token."""
        auth = AuthService()
        
        new_access_token = await auth.refresh_access_token(db_session, "invalid.token")
        assert new_access_token is None
    
    async def test_refresh_access_token_nonexistent_user(self, db_session):
        """Test refreshing access token for non-existent user."""
        auth = AuthService()
        
        # Create refresh token for non-existent user
        refresh_token = auth.create_refresh_token(99999)
        new_access_token = await auth.refresh_access_token(db_session, refresh_token)
        
        assert new_access_token is None
    
    def test_hash_token(self):
        """Test token hashing."""
        auth = AuthService()
        token = "test_token_to_hash"
        
        hashed = auth.hash_token(token)
        
        assert isinstance(hashed, str)
        assert hashed != token  # Should be different from original
        assert len(hashed) > len(token)  # Hashed version should be longer
    
    def test_verify_hashed_token_success(self):
        """Test verifying hashed token successfully."""
        auth = AuthService()
        token = "test_token_to_verify"
        
        hashed = auth.hash_token(token)
        is_valid = auth.verify_hashed_token(token, hashed)
        
        assert is_valid is True
    
    def test_verify_hashed_token_failure(self):
        """Test verifying hashed token with wrong token."""
        auth = AuthService()
        token = "correct_token"
        wrong_token = "wrong_token"
        
        hashed = auth.hash_token(token)
        is_valid = auth.verify_hashed_token(wrong_token, hashed)
        
        assert is_valid is False
    
    def test_auth_service_singleton(self):
        """Test that auth_service is properly configured."""
        assert auth_service.github_client_id == settings.GITHUB_CLIENT_ID
        assert auth_service.github_client_secret == settings.GITHUB_CLIENT_SECRET
        assert auth_service.redirect_uri == settings.GITHUB_OAUTH_REDIRECT_URI
        assert auth_service.secret_key == settings.SECRET_KEY
        assert auth_service.algorithm == "HS256" 