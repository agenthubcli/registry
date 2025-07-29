"""
Package schemas for request/response serialization.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl

from app.schemas.user import UserProfile


# Enums
from enum import Enum

class PackageTypeEnum(str, Enum):
    """Package type enumeration."""
    AGENT = "agent"
    TOOL = "tool"
    CHAIN = "chain"
    PROMPT = "prompt"
    DATASET = "dataset"


# Base Models
class PackageBase(BaseModel):
    """Base package model."""
    name: str = Field(..., pattern=r'^[a-z0-9]([a-z0-9\-])*[a-z0-9]$', min_length=1, max_length=214)
    description: Optional[str] = Field(None, max_length=1000)
    package_type: PackageTypeEnum
    homepage: Optional[HttpUrl] = None
    repository: Optional[HttpUrl] = None
    documentation: Optional[HttpUrl] = None
    keywords: List[str] = Field(default_factory=list)


class PackageVersionBase(BaseModel):
    """Base package version model."""
    version: str = Field(..., pattern=r'^[0-9]+\.[0-9]+\.[0-9]+([+-][a-zA-Z0-9\-\.]+)*$')
    description: Optional[str] = None
    is_prerelease: bool = False
    runtime: Optional[str] = None
    python_version: Optional[str] = None


# Request Models
class PackageCreate(PackageBase):
    """Package creation request."""
    pass


class PackageVersionCreate(PackageVersionBase):
    """Package version creation request."""
    pass


# Response Models
class PackageVersion(PackageVersionBase):
    """Package version response model."""
    id: int
    download_count: int
    file_size: int = Field(..., description="File size in bytes")
    file_hash_sha256: str
    download_url: HttpUrl
    manifest: Optional[Dict[str, Any]] = None
    published_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class Package(PackageBase):
    """Package response model."""
    id: int
    latest_version: Optional[str] = None
    total_downloads: int
    download_count_last_30_days: int
    version_count: int
    owner: UserProfile
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PackageDetails(BaseModel):
    """Detailed package information with versions."""
    package: Package
    owner: UserProfile
    versions: List[PackageVersion]
    latest_version: Optional[PackageVersion] = None

    model_config = {"from_attributes": True}


class PackageVersionDetails(BaseModel):
    """Detailed package version information."""
    package: Package
    version: PackageVersion
    owner: UserProfile

    model_config = {"from_attributes": True}


class PackageVersions(BaseModel):
    """Package versions list response."""
    package_name: str
    versions: List[PackageVersion]
    total: int
    limit: int
    offset: int

    model_config = {"from_attributes": True}


class PackageStats(BaseModel):
    """Package statistics response."""
    package_name: str
    total_downloads: int
    downloads_last_30_days: int
    downloads_last_7_days: int
    version_count: int
    latest_version: str

    model_config = {"from_attributes": True}


class SearchResults(BaseModel):
    """Search results response."""
    results: List[Package]
    total: int = Field(..., description="Total number of matching packages")
    limit: int
    offset: int
    query: str
    package_type: Optional[PackageTypeEnum] = None
    sort_by: str

    model_config = {"from_attributes": True}


class UserPackages(BaseModel):
    """User packages response."""
    username: str
    packages: List[Package]
    total_packages: int
    limit: int
    offset: int

    model_config = {"from_attributes": True}


class PublishSuccess(BaseModel):
    """Package publish success response."""
    message: str = "Package published successfully"
    package: Package
    version: PackageVersion

    model_config = {"from_attributes": True}


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Package not found",
                "error_code": "PACKAGE_NOT_FOUND"
            }
        }
    }


class MessageResponse(BaseModel):
    """Standard message response."""
    message: str = Field(..., description="Success message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Operation completed successfully"
            }
        }
    } 