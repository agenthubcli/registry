"""
Tests for authentication API endpoints.
"""

import pytest
from unittest.mock import patch
from fastapi import status

from app.services.auth import auth_service


@pytest.mark.api
@pytest.mark.auth
@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test cases for authentication endpoints."""
    
    async def test_github_oauth_login_success(self, client):
        """Test GitHub OAuth login initiation."""
        response = await client.get("/api/v1/auth/github")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "oauth_url" in data
        assert "github.com/login/oauth/authorize" in data["oauth_url"]
        assert "client_id=" in data["oauth_url"]
        assert "redirect_uri=" in data["oauth_url"]
        assert "scope=read:user user:email" in data["oauth_url"]
    
    async def test_github_oauth_login_with_redirect(self, client):
        """Test GitHub OAuth login with redirect parameter."""
        redirect_url = "https://example.com/dashboard"
        response = await client.get(f"/api/v1/auth/github?redirect_to={redirect_url}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "oauth_url" in data
        assert "state=" in data["oauth_url"]
    
    async def test_github_oauth_callback_success(self, client, mock_httpx):
        """Test successful GitHub OAuth callback."""
        # Mock successful OAuth flow
        with patch.object(auth_service, "exchange_code_for_token") as mock_exchange, \
             patch.object(auth_service, "get_github_user_info") as mock_user_info, \
             patch.object(auth_service, "create_or_update_user") as mock_create_user:
            
            # Setup mocks
            mock_exchange.return_value = {"access_token": "gho_test_token"}
            mock_user_info.return_value = {
                "id": 12345,
                "login": "testuser",
                "name": "Test User",
                "email": "test@example.com",
                "primary_email": "test@example.com",
                "avatar_url": "https://github.com/avatars/testuser",
            }
            
            # Create a mock user object
            from app.models.user import User
            mock_user = User(
                id=1,
                github_id=12345,
                github_username="testuser",
                github_email="test@example.com",
                is_verified=True,
            )
            mock_create_user.return_value = mock_user
            
            response = await client.get("/api/v1/auth/github/callback?code=test_code&state=test_state")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["github_username"] == "testuser"
    
    async def test_github_oauth_callback_invalid_code(self, client):
        """Test GitHub OAuth callback with invalid code."""
        with patch.object(auth_service, "exchange_code_for_token") as mock_exchange:
            mock_exchange.side_effect = ValueError("Invalid authorization code")
            
            response = await client.get("/api/v1/auth/github/callback?code=invalid_code")
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "OAuth authentication failed" in data["detail"]
    
    async def test_github_oauth_callback_missing_code(self, client):
        """Test GitHub OAuth callback without code parameter."""
        response = await client.get("/api/v1/auth/github/callback")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh."""
        # Create refresh token
        refresh_token = auth_service.create_refresh_token(test_user.id)
        
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify new token is valid
        payload = auth_service.verify_token(data["access_token"], "access")
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
    
    async def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid refresh token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.refresh.token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid refresh token"
    
    async def test_refresh_token_expired(self, client, test_user):
        """Test token refresh with expired refresh token."""
        from datetime import timedelta
        
        # Create expired refresh token
        with patch.object(auth_service, 'refresh_token_expire_minutes', 0):
            expired_token = auth_service.create_refresh_token(test_user.id)
        
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_get_current_user_success(self, client, auth_headers, test_user):
        """Test getting current user info with valid token."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == test_user.id
        assert data["github_username"] == test_user.github_username
        assert data["display_name"] == test_user.display_name
        assert data["github_avatar_url"] == test_user.github_avatar_url
        
        # Ensure private fields are not exposed
        assert "github_access_token" not in data
        assert "github_refresh_token" not in data
        assert "github_id" not in data
    
    async def test_get_current_user_unauthorized(self, client):
        """Test getting current user info without authentication."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Not authenticated"
    
    async def test_get_current_user_invalid_token(self, client):
        """Test getting current user info with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid authentication credentials"
    
    async def test_get_current_user_inactive_user(self, client, db_session):
        """Test getting current user info for inactive user."""
        from app.models.user import User
        
        # Create inactive user
        inactive_user = User(
            github_id=99999,
            github_username="inactiveuser",
            is_active=False,
        )
        db_session.add(inactive_user)
        await db_session.commit()
        await db_session.refresh(inactive_user)
        
        # Create token for inactive user
        token = auth_service.create_access_token(inactive_user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid authentication credentials"
    
    async def test_logout_success(self, client, auth_headers):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Logged out successfully"
    
    async def test_logout_unauthorized(self, client):
        """Test logout without authentication."""
        response = await client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Not authenticated"
    
    async def test_multiple_concurrent_logins(self, client, test_user):
        """Test multiple concurrent login sessions."""
        # Create multiple tokens for the same user
        token1 = auth_service.create_access_token(test_user.id)
        token2 = auth_service.create_access_token(test_user.id)
        
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Both tokens should work
        response1 = await client.get("/api/v1/auth/me", headers=headers1)
        response2 = await client.get("/api/v1/auth/me", headers=headers2)
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["id"] == test_user.id
        assert data2["id"] == test_user.id
    
    async def test_token_expiry_handling(self, client, test_user):
        """Test handling of expired tokens."""
        from datetime import timedelta
        
        # Create token that expires immediately
        expired_token = auth_service.create_access_token(
            test_user.id, 
            expires_delta=timedelta(seconds=-1)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid authentication credentials"
    
    async def test_malformed_authorization_header(self, client):
        """Test handling of malformed authorization headers."""
        test_cases = [
            {"Authorization": "Invalid header format"},
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "Bearer "},  # Empty token
            {"Authorization": "Basic dGVzdA=="},  # Wrong scheme
        ]
        
        for headers in test_cases:
            response = await client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED 