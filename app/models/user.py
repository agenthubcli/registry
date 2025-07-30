"""
User model for AgentHub Registry.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """User model for registry authentication and package ownership."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # GitHub OAuth fields
    github_id = Column(Integer, unique=True, index=True, nullable=False)
    github_username = Column(String(255), unique=True, index=True, nullable=False)
    github_email = Column(String(255), unique=True, index=True, nullable=True)
    github_avatar_url = Column(String(512), nullable=True)
    
    # User profile
    display_name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    website = Column(String(512), nullable=True)
    location = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Package publishing settings
    can_publish = Column(Boolean, default=True, nullable=False)
    max_package_size_mb = Column(Integer, default=100, nullable=False)
    
    # OAuth tokens (encrypted/hashed)
    github_access_token = Column(String(512), nullable=True)  # Should be encrypted
    github_refresh_token = Column(String(512), nullable=True)  # Should be encrypted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Statistics
    total_packages = Column(Integer, default=0, nullable=False)
    total_downloads = Column(Integer, default=0, nullable=False)
    
    # Relationships
    packages = relationship("Package", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, github_username='{self.github_username}')>"
    
    @property
    def public_profile(self) -> dict:
        """Get public profile information."""
        return {
            "id": self.id,
            "github_username": self.github_username,
            "display_name": self.display_name,
            "github_avatar_url": self.github_avatar_url,
            "bio": self.bio,
            "website": self.website,
            "location": self.location,
            "company": self.company,
            "total_packages": self.total_packages,
            "total_downloads": self.total_downloads,
            "created_at": self.created_at,
        }
    
    def can_publish_package(self) -> bool:
        """Check if user can publish packages."""
        return self.is_active and self.can_publish and self.is_verified 