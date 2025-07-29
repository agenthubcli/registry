"""
Standalone models for Alembic migrations.
"""

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
    Date,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


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
    
    # Indexes
    __table_args__ = (
        Index("idx_packages_type_status", "package_type", "status"),
        Index("idx_packages_downloads", "total_downloads"),
        Index("idx_packages_updated", "updated_at"),
    )


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
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("package_id", "version", name="uq_package_version"),
        Index("idx_versions_package_status", "package_id", "status"),
        Index("idx_versions_downloads", "download_count"),
        Index("idx_versions_published", "published_at"),
    )


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
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("package_id", "tag", name="uq_package_tag"),
        Index("idx_tags_tag", "tag"),
    )


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
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("version_id", "dependency_name", name="uq_version_dependency"),
        Index("idx_dependencies_name", "dependency_name"),
    )


class DownloadStats(Base):
    """Download statistics for packages and versions."""
    
    __tablename__ = "download_stats"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # What was downloaded
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("package_versions.id"), nullable=True, index=True)
    
    # When and who
    download_date = Column(Date, nullable=False, index=True)
    download_count = Column(Integer, default=1, nullable=False)
    
    # User info (optional, for authenticated downloads)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Request metadata
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    country_code = Column(String(2), nullable=True)  # ISO country code
    
    # Referrer info
    referrer = Column(String(512), nullable=True)
    download_source = Column(String(50), nullable=True)  # cli, web, api, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Constraints and Indexes
    __table_args__ = (
        # Unique constraint for daily aggregation
        UniqueConstraint("package_id", "version_id", "download_date", "user_id", name="uq_daily_download_stats"),
        
        # Indexes for common queries
        Index("idx_download_stats_package_date", "package_id", "download_date"),
        Index("idx_download_stats_version_date", "version_id", "download_date"),
        Index("idx_download_stats_date", "download_date"),
        Index("idx_download_stats_country", "country_code"),
        Index("idx_download_stats_source", "download_source"),
    )


class DailyDownloadSummary(Base):
    """Pre-aggregated daily download statistics for performance."""
    
    __tablename__ = "daily_download_summary"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # What and when
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False, index=True)
    download_date = Column(Date, nullable=False, index=True)
    
    # Aggregated metrics
    total_downloads = Column(Integer, default=0, nullable=False)
    unique_users = Column(Integer, default=0, nullable=False)
    unique_ips = Column(Integer, default=0, nullable=False)
    
    # Download sources breakdown
    cli_downloads = Column(Integer, default=0, nullable=False)
    web_downloads = Column(Integer, default=0, nullable=False)
    api_downloads = Column(Integer, default=0, nullable=False)
    other_downloads = Column(Integer, default=0, nullable=False)
    
    # Geographic breakdown (top countries)
    top_countries = Column(String(200), nullable=True)  # JSON-like string: "US:50,GB:20,DE:15"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("package_id", "download_date", name="uq_daily_summary"),
        Index("idx_daily_summary_date", "download_date"),
        Index("idx_daily_summary_downloads", "total_downloads"),
    ) 