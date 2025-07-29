"""
Authentication schemas for request/response serialization.
"""

from pydantic import BaseModel, Field, HttpUrl
from app.schemas.user import UserProfile


class OAuthUrl(BaseModel):
    """OAuth URL response."""
    oauth_url: HttpUrl = Field(..., description="GitHub OAuth authorization URL")

    class Config:
        schema_extra = {
            "example": {
                "oauth_url": "https://github.com/login/oauth/authorize?client_id=..."
            }
        }


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="JWT refresh token")


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class AuthSuccess(TokenResponse):
    """Authentication success response."""
    refresh_token: str = Field(..., description="JWT refresh token")
    user: UserProfile

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": 123,
                    "github_username": "johndoe",
                    "display_name": "John Doe",
                    "github_avatar_url": "https://github.com/avatars/johndoe",
                    "bio": "AI researcher and developer",
                    "website": "https://johndoe.dev",
                    "location": "San Francisco, CA",
                    "company": "AI Company Inc.",
                    "total_packages": 5,
                    "total_downloads": 1234,
                    "created_at": "2023-01-01T00:00:00Z"
                }
            }
        } 