"""
Package schemas for AgentHub Registry API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

from app.schemas.user import UserPublic


class PackageType(str, Enum):
    """Supported package types."""
    AGENT = "agent"
    TOOL = "tool"
    CHAIN = "chain"
    PROMPT = "prompt"
    DATASET = "dataset"


class PackageStatus(str, Enum):
    """Package status."""
    PENDING = "pending"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


class VersionStatus(str, Enum):
    """Package version status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    YANKED = "yanked"


class PackageBase(BaseModel):
    """Base package schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    homepage: Optional[HttpUrl] = None
    repository: Optional[HttpUrl] = None
    documentation: Optional[HttpUrl] = None
    keywords: Optional[List[str]] = Field(default_factory=list)


class PackageCreate(PackageBase):
    """Schema for creating a new package."""
    package_type: PackageType
    is_private: bool = False
    auto_publish: bool = False


class PackageUpdate(BaseModel):
    """Schema for updating package metadata."""
    description: Optional[str] = None
    homepage: Optional[HttpUrl] = None
    repository: Optional[HttpUrl] = None
    documentation: Optional[HttpUrl] = None
    keywords: Optional[List[str]] = None
    is_private: Optional[bool] = None
    auto_publish: Optional[bool] = None


class PackagePublic(BaseModel):
    """Public package information schema."""
    id: int
    name: str
    description: Optional[str] = None
    package_type: str
    latest_version: Optional[str] = None
    total_downloads: int = 0
    download_count_last_30_days: int = 0
    created_at: datetime
    updated_at: datetime
    homepage: Optional[str] = None
    repository: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PackageVersionBase(BaseModel):
    """Base package version schema."""
    version: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    changelog: Optional[str] = None
    runtime: Optional[str] = Field(None, max_length=50)
    python_version: Optional[str] = Field(None, max_length=50)
    is_prerelease: bool = False


class PackageVersionCreate(PackageVersionBase):
    """Schema for creating a new package version."""
    manifest: Dict[str, Any]


class PackageVersionPublic(BaseModel):
    """Public package version information schema."""
    id: int
    version: str
    description: Optional[str] = None
    download_count: int = 0
    download_count_last_30_days: int = 0
    file_size: int
    file_hash_sha256: str
    is_prerelease: bool = False
    runtime: Optional[str] = None
    python_version: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    download_url: str
    manifest: Dict[str, Any]

    class Config:
        from_attributes = True


class PackageVersionDetail(PackageVersionPublic):
    """Detailed package version information schema."""
    changelog: Optional[str] = None
    filename: str
    status: str
    virus_scan_status: str
    vulnerability_scan_status: str
    is_validated: bool
    yanked_at: Optional[datetime] = None
    yanked_reason: Optional[str] = None

    class Config:
        from_attributes = True


class PackageDetail(PackagePublic):
    """Detailed package information schema."""
    normalized_name: str
    readme: Optional[str] = None
    documentation: Optional[str] = None
    status: str
    is_private: bool
    auto_publish: bool
    version_count: int = 0
    latest_version_published_at: Optional[datetime] = None
    owner: UserPublic
    versions: List[PackageVersionPublic] = Field(default_factory=list)
    latest_version_info: Optional[PackageVersionPublic] = None

    class Config:
        from_attributes = True


class PackageSearch(BaseModel):
    """Package search request schema."""
    q: str = Field(..., min_length=1, description="Search query")
    package_type: Optional[PackageType] = Field(None, description="Filter by package type")
    limit: int = Field(20, ge=1, le=100, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    sort_by: str = Field("relevance", description="Sort by: relevance, downloads, created, updated")


class PackageSearchResultItem(PackagePublic):
    """Individual package search result."""
    owner: UserPublic

    class Config:
        from_attributes = True


class PackageSearchResult(BaseModel):
    """Package search response schema."""
    results: List[PackageSearchResultItem]
    total: int
    limit: int
    offset: int
    query: str
    package_type: Optional[str] = None
    sort_by: str


class PackageStats(BaseModel):
    """Package statistics schema."""
    package_name: str
    total_downloads: int
    downloads_last_30_days: int
    version_count: int
    # Additional stats can be added here

    class Config:
        from_attributes = True


class PackagePublishRequest(BaseModel):
    """Package publish request schema."""
    package_type: PackageType


class PackagePublishResponse(BaseModel):
    """Package publish response schema."""
    message: str
    package: PackagePublic
    version: PackageVersionPublic 