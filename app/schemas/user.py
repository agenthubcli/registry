"""
User schemas for request/response serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class UserProfile(BaseModel):
    """User profile response model."""
    id: int = Field(..., description="User ID")
    github_username: str = Field(..., description="GitHub username")
    display_name: Optional[str] = Field(None, description="Display name")
    github_avatar_url: Optional[HttpUrl] = Field(None, description="GitHub avatar URL")
    bio: Optional[str] = Field(None, description="User bio")
    website: Optional[HttpUrl] = Field(None, description="User website")
    location: Optional[str] = Field(None, description="User location")
    company: Optional[str] = Field(None, description="User company")
    total_packages: int = Field(default=0, description="Total number of published packages")
    total_downloads: int = Field(default=0, description="Total downloads across all packages")
    created_at: datetime = Field(..., description="Account creation date")

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
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