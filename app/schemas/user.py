"""
User schemas for AgentHub Registry API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, HttpUrl


class UserBase(BaseModel):
    """Base user schema with common fields."""
    display_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    website: Optional[HttpUrl] = None
    location: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)


class UserCreate(BaseModel):
    """Schema for creating a new user (from OAuth)."""
    github_id: int
    github_username: str = Field(..., max_length=255)
    github_email: Optional[EmailStr] = None
    github_avatar_url: Optional[HttpUrl] = None
    display_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    website: Optional[HttpUrl] = None
    location: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=255)


class UserUpdate(UserBase):
    """Schema for updating user profile."""
    pass


class UserPublic(BaseModel):
    """Public user information schema."""
    id: int
    github_username: str
    display_name: Optional[str] = None
    github_avatar_url: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    total_packages: int = 0
    total_downloads: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class UserPrivate(UserPublic):
    """Private user information schema (for authenticated user)."""
    github_email: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    can_publish: bool = True
    max_package_size_mb: int = 100
    last_login_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True 