"""
Download statistics model for AgentHub Registry analytics.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


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
    
    # Relationships
    package = relationship("Package")
    version = relationship("PackageVersion")
    user = relationship("User")
    
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
    
    def __repr__(self) -> str:
        return f"<DownloadStats(package_id={self.package_id}, version_id={self.version_id}, date={self.download_date}, count={self.download_count})>"


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
    
    # Relationships
    package = relationship("Package")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("package_id", "download_date", name="uq_daily_summary"),
        Index("idx_daily_summary_date", "download_date"),
        Index("idx_daily_summary_downloads", "total_downloads"),
    )
    
    def __repr__(self) -> str:
        return f"<DailyDownloadSummary(package_id={self.package_id}, date={self.download_date}, downloads={self.total_downloads})>" 