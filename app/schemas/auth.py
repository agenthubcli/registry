"""
Authentication schemas for AgentHub Registry API.
"""

from typing import Optional
from pydantic import BaseModel

from app.schemas.user import UserPublic


class TokenData(BaseModel):
    """JWT token payload data schema."""
    user_id: int
    username: str
    exp: Optional[int] = None  # Expiration timestamp
    iat: Optional[int] = None  # Issued at timestamp
    token_type: str = "access"  # "access" or "refresh"


class TokenResponse(BaseModel):
    """Token response schema for OAuth callbacks and refresh."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None  # Token expiration in seconds
    user: Optional[UserPublic] = None


class OAuthCallback(BaseModel):
    """OAuth callback parameters schema."""
    code: str
    state: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class GitHubOAuthInitiate(BaseModel):
    """GitHub OAuth initiation response schema."""
    oauth_url: str


class LogoutResponse(BaseModel):
    """Logout response schema."""
    message: str = "Logged out successfully" 