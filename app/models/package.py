"""
Package models for AgentHub Registry.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class PackageType(str, enum.Enum):
    """Supported package types."""
    AGENT = "agent"
    TOOL = "tool"
    CHAIN = "chain"
    PROMPT = "prompt"
    DATASET = "dataset"


class PackageStatus(str, enum.Enum):
    """Package status."""
    PENDING = "pending"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


class VersionStatus(str, enum.Enum):
    """Package version status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    YANKED = "yanked"


class Package(Base):
    """Package model representing a unique package name."""
    
    __tablename__ = "packages"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Package identification
    name = Column(String(255), unique=True, index=True, nullable=False)
    normalized_name = Column(String(255), unique=True, index=True, nullable=False)
    
    # Package metadata
    description = Column(Text, nullable=True)
    readme = Column(Text, nullable=True)
    homepage = Column(String(512), nullable=True)
    repository = Column(String(512), nullable=True)
    documentation = Column(String(512), nullable=True)
    
    # Package classification
    package_type = Column(Enum(PackageType), nullable=False, index=True)
    status = Column(Enum(PackageStatus), default=PackageStatus.PUBLISHED, nullable=False, index=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Package settings
    is_private = Column(Boolean, default=False, nullable=False, index=True)
    auto_publish = Column(Boolean, default=False, nullable=False)
    
    # Statistics
    total_downloads = Column(Integer, default=0, nullable=False, index=True)
    download_count_last_30_days = Column(Integer, default=0, nullable=False)
    version_count = Column(Integer, default=0, nullable=False)
    
    # Latest version info (denormalized for performance)
    latest_version = Column(String(50), nullable=True)
    latest_version_published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Search and discovery
    keywords = Column(JSON, nullable=True)  # List of keywords
    search_vector = Column(Text, nullable=True)  # For full-text search
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="packages")
    versions = relationship("PackageVersion", back_populates="package", cascade="all, delete-orphan")
    tags = relationship("PackageTag", back_populates="package", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_packages_type_status", "package_type", "status"),
        Index("idx_packages_downloads", "total_downloads"),
        Index("idx_packages_updated", "updated_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Package(id={self.id}, name='{self.name}', type='{self.package_type}')>"
    
    @property
    def public_info(self) -> dict:
        """Get public package information."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "package_type": self.package_type.value,
            "latest_version": self.latest_version,
            "total_downloads": self.total_downloads,
            "download_count_last_30_days": self.download_count_last_30_days,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "homepage": self.homepage,
            "repository": self.repository,
            "keywords": self.keywords or [],
        }


class PackageVersion(Base):
    """Package version model representing a specific version of a package."""
    
    __tablename__ = "package_versions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Version identification
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    
    # Version metadata
    description = Column(Text, nullable=True)
    changelog = Column(Text, nullable=True)
    
    # Package files and artifacts
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False)
    s3_key = Column(String(512), nullable=False)  # S3 object key
    
    # Package manifest/metadata
    manifest = Column(JSON, nullable=False)  # The full package.yaml content
    
    # Runtime requirements
    runtime = Column(String(50), nullable=True)  # e.g., "python", "node", "docker"
    python_version = Column(String(50), nullable=True)  # e.g., ">=3.8"
    
    # Status and publishing
    status = Column(Enum(VersionStatus), default=VersionStatus.DRAFT, nullable=False, index=True)
    is_prerelease = Column(Boolean, default=False, nullable=False)
    
    # Statistics
    download_count = Column(Integer, default=0, nullable=False, index=True)
    download_count_last_30_days = Column(Integer, default=0, nullable=False)
    
    # Validation and security
    is_validated = Column(Boolean, default=False, nullable=False)
    virus_scan_status = Column(String(20), default="pending", nullable=False)  # pending, clean, infected
    vulnerability_scan_status = Column(String(20), default="pending", nullable=False)
    
    # Publishing info
    published_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    yanked_at = Column(DateTime(timezone=True), nullable=True)
    yanked_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    package = relationship("Package", back_populates="versions")
    published_by = relationship("User", foreign_keys=[published_by_id])
    dependencies = relationship("PackageDependency", back_populates="version", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("package_id", "version", name="uq_package_version"),
        Index("idx_versions_package_status", "package_id", "status"),
        Index("idx_versions_downloads", "download_count"),
        Index("idx_versions_published", "published_at"),
    )
    
    def __repr__(self) -> str:
        return f"<PackageVersion(id={self.id}, package_id={self.package_id}, version='{self.version}')>"
    
    @property
    def download_url(self) -> str:
        """Get download URL for this version."""
        from app.core.config import settings
        return f"{settings.s3_public_url}/{self.s3_key}"
    
    @property
    def public_info(self) -> dict:
        """Get public version information."""
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "download_count": self.download_count,
            "download_count_last_30_days": self.download_count_last_30_days,
            "file_size": self.file_size,
            "file_hash_sha256": self.file_hash_sha256,
            "is_prerelease": self.is_prerelease,
            "runtime": self.runtime,
            "python_version": self.python_version,
            "published_at": self.published_at,
            "created_at": self.created_at,
            "download_url": self.download_url,
            "manifest": self.manifest,
        }


class PackageTag(Base):
    """Tags for packages to enable categorization and discovery."""
    
    __tablename__ = "package_tags"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Tag information
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False, index=True)
    tag = Column(String(50), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    package = relationship("Package", back_populates="tags")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("package_id", "tag", name="uq_package_tag"),
        Index("idx_tags_tag", "tag"),
    )
    
    def __repr__(self) -> str:
        return f"<PackageTag(package_id={self.package_id}, tag='{self.tag}')>"


class PackageDependency(Base):
    """Package dependencies for version resolution."""
    
    __tablename__ = "package_dependencies"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Dependency relationship
    version_id = Column(Integer, ForeignKey("package_versions.id"), nullable=False, index=True)
    dependency_name = Column(String(255), nullable=False, index=True)
    version_spec = Column(String(100), nullable=False)  # e.g., "^1.0.0", ">=2.0.0,<3.0.0"
    
    # Dependency type
    dependency_type = Column(String(20), default="runtime", nullable=False)  # runtime, dev, optional
    
    # Optional metadata
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    version = relationship("PackageVersion", back_populates="dependencies")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("version_id", "dependency_name", name="uq_version_dependency"),
        Index("idx_dependencies_name", "dependency_name"),
    )
    
    def __repr__(self) -> str:
        return f"<PackageDependency(version_id={self.version_id}, dependency='{self.dependency_name}', spec='{self.version_spec}')>" 