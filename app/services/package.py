"""
Package service for AgentHub Registry package management.
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import yaml
import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.package import (
    Package, PackageVersion, PackageTag, PackageDependency,
    PackageType, PackageStatus, VersionStatus
)
from app.models.user import User
from app.services.storage import storage_service
from app.services.cache import cache_service
from app.schemas.package import PackageCreate, PackageVersionCreate

logger = structlog.get_logger()


class PackageService:
    """Service for managing package operations."""
    
    def __init__(self):
        """Initialize the package service."""
        self.allowed_extensions = {".tar.gz", ".zip", ".tgz"}
        self.version_pattern = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+([+-][a-zA-Z0-9\-\.]+)*$')
        self.name_pattern = re.compile(r'^[a-z0-9]([a-z0-9\-])*[a-z0-9]$')
    
    def normalize_package_name(self, name: str) -> str:
        """Normalize package name for consistent storage."""
        return name.lower().replace("_", "-")
    
    def validate_package_name(self, name: str) -> bool:
        """Validate package name format."""
        if not name or len(name) < 2 or len(name) > 214:
            return False
        return bool(self.name_pattern.match(name))
    
    def validate_version(self, version: str) -> bool:
        """Validate version format (semver)."""
        if not version:
            return False
        return bool(self.version_pattern.match(version))
    
    def validate_manifest(self, manifest_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate package manifest structure."""
        errors = []
        
        # Required fields
        required_fields = ["name", "version", "type"]
        for field in required_fields:
            if field not in manifest_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate name
        if "name" in manifest_data:
            if not self.validate_package_name(manifest_data["name"]):
                errors.append("Invalid package name format")
        
        # Validate version
        if "version" in manifest_data:
            if not self.validate_version(manifest_data["version"]):
                errors.append("Invalid version format (must be semver)")
        
        # Validate type
        if "type" in manifest_data:
            valid_types = [t.value for t in PackageType]
            if manifest_data["type"] not in valid_types:
                errors.append(f"Invalid package type. Must be one of: {valid_types}")
        
        # Validate optional fields
        if "description" in manifest_data:
            desc = manifest_data["description"]
            if len(desc) > settings.MAX_DESCRIPTION_LENGTH:
                errors.append(f"Description too long (max {settings.MAX_DESCRIPTION_LENGTH} chars)")
        
        return len(errors) == 0, errors
    
    async def get_package_by_name(
        self, 
        db: AsyncSession, 
        package_name: str, 
        include_private: bool = False
    ) -> Optional[Package]:
        """Get package by name."""
        try:
            cache_key = f"package:{package_name}:{include_private}"
            cached = await cache_service.get(cache_key)
            if cached:
                logger.debug("Package retrieved from cache", package=package_name)
                return Package(**cached) if cached else None
            
            query = select(Package).where(Package.name == package_name)
            
            if not include_private:
                query = query.where(
                    Package.status == PackageStatus.PUBLISHED,
                    Package.is_private == False
                )
            
            result = await db.execute(query)
            package = result.scalar_one_or_none()
            
            # Cache the result
            package_data = package.public_info if package else None
            await cache_service.set(cache_key, package_data, ttl=300)  # 5 minutes
            
            return package
            
        except Exception as e:
            logger.error("Failed to get package by name", package=package_name, error=str(e))
            return None
    
    async def get_package_with_versions(
        self, 
        db: AsyncSession, 
        package_name: str,
        include_private: bool = False
    ) -> Optional[Package]:
        """Get package with all versions loaded."""
        try:
            query = select(Package).options(
                joinedload(Package.versions),
                joinedload(Package.owner),
                joinedload(Package.tags)
            ).where(Package.name == package_name)
            
            if not include_private:
                query = query.where(
                    Package.status == PackageStatus.PUBLISHED,
                    Package.is_private == False
                )
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get package with versions", package=package_name, error=str(e))
            return None
    
    async def create_package(
        self, 
        db: AsyncSession, 
        package_data: PackageCreate, 
        owner: User
    ) -> Package:
        """Create a new package."""
        try:
            # Validate package name
            if not self.validate_package_name(package_data.name):
                raise ValueError("Invalid package name format")
            
            # Check if package already exists
            existing = await self.get_package_by_name(db, package_data.name, include_private=True)
            if existing:
                raise ValueError(f"Package '{package_data.name}' already exists")
            
            # Create package
            package = Package(
                name=package_data.name,
                normalized_name=self.normalize_package_name(package_data.name),
                description=package_data.description,
                package_type=PackageType(package_data.package_type.value),
                homepage=str(package_data.homepage) if package_data.homepage else None,
                repository=str(package_data.repository) if package_data.repository else None,
                documentation=str(package_data.documentation) if package_data.documentation else None,
                keywords=package_data.keywords,
                owner_id=owner.id,
                status=PackageStatus.PUBLISHED,
            )
            
            db.add(package)
            await db.commit()
            await db.refresh(package)
            
            # Create tags
            if package_data.keywords:
                await self._create_package_tags(db, package.id, package_data.keywords)
            
            # Clear cache
            await cache_service.delete_pattern(f"package:{package_data.name}:*")
            
            logger.info("Package created", package=package_data.name, owner=owner.github_username)
            return package
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create package", package=package_data.name, error=str(e))
            raise
    
    async def create_package_version(
        self,
        db: AsyncSession,
        package: Package,
        version_data: PackageVersionCreate,
        file_data: bytes,
        filename: str,
        manifest: Dict[str, Any],
        publisher: User
    ) -> PackageVersion:
        """Create a new package version."""
        try:
            # Validate version
            if not self.validate_version(version_data.version):
                raise ValueError("Invalid version format")
            
            # Check if version already exists
            existing_version = await self._get_package_version(
                db, package.id, version_data.version
            )
            if existing_version:
                raise ValueError(f"Version {version_data.version} already exists")
            
            # Validate manifest
            is_valid, errors = self.validate_manifest(manifest)
            if not is_valid:
                raise ValueError(f"Invalid manifest: {'; '.join(errors)}")
            
            # Upload file to storage
            s3_key, file_hash, file_size = await storage_service.upload_package(
                file_data=file_data,
                package_name=package.name,
                version=version_data.version,
                filename=filename
            )
            
            # Create version record
            version = PackageVersion(
                package_id=package.id,
                version=version_data.version,
                description=version_data.description,
                filename=filename,
                file_size=file_size,
                file_hash_sha256=file_hash,
                s3_key=s3_key,
                manifest=manifest,
                runtime=version_data.runtime,
                python_version=version_data.python_version,
                is_prerelease=version_data.is_prerelease,
                status=VersionStatus.PUBLISHED,
                published_by_id=publisher.id,
                published_at=datetime.utcnow(),
            )
            
            db.add(version)
            
            # Update package stats
            package.latest_version = version_data.version
            package.latest_version_published_at = version.published_at
            package.version_count = await self._count_package_versions(db, package.id)
            package.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(version)
            
            # Clear cache
            await cache_service.delete_pattern(f"package:{package.name}:*")
            await cache_service.delete_pattern(f"package_versions:{package.name}:*")
            
            logger.info(
                "Package version created",
                package=package.name,
                version=version_data.version,
                publisher=publisher.github_username
            )
            
            return version
            
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to create package version",
                package=package.name,
                version=version_data.version,
                error=str(e)
            )
            raise
    
    async def get_package_versions(
        self,
        db: AsyncSession,
        package_name: str,
        limit: int = 20,
        offset: int = 0,
        include_prerelease: bool = False
    ) -> Tuple[List[PackageVersion], int]:
        """Get package versions with pagination."""
        try:
            cache_key = f"package_versions:{package_name}:{limit}:{offset}:{include_prerelease}"
            cached = await cache_service.get(cache_key)
            if cached:
                return cached["versions"], cached["total"]
            
            package = await self.get_package_by_name(db, package_name)
            if not package:
                return [], 0
            
            # Base query
            query = select(PackageVersion).where(
                PackageVersion.package_id == package.id,
                PackageVersion.status == VersionStatus.PUBLISHED
            )
            
            if not include_prerelease:
                query = query.where(PackageVersion.is_prerelease == False)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Get versions
            query = query.order_by(desc(PackageVersion.published_at))
            query = query.limit(limit).offset(offset)
            
            result = await db.execute(query)
            versions = result.scalars().all()
            
            # Cache result
            cache_data = {
                "versions": [v.public_info for v in versions],
                "total": total
            }
            await cache_service.set(cache_key, cache_data, ttl=300)
            
            return list(versions), total
            
        except Exception as e:
            logger.error("Failed to get package versions", package=package_name, error=str(e))
            return [], 0
    
    async def increment_download_count(
        self,
        db: AsyncSession,
        package_name: str,
        version: str
    ) -> bool:
        """Increment download count for a package version."""
        try:
            # Use cache to batch download count updates
            cache_key = f"downloads:{package_name}:{version}"
            current_count = await cache_service.increment(cache_key, ttl=3600)  # 1 hour
            
            # Update database every 10 downloads or on cache expiry
            if current_count % 10 == 0:
                await self._flush_download_counts(db, package_name, version, current_count)
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to increment download count",
                package=package_name,
                version=version,
                error=str(e)
            )
            return False
    
    async def get_package_stats(self, db: AsyncSession, package_name: str) -> Optional[Dict[str, Any]]:
        """Get package statistics."""
        try:
            cache_key = f"package_stats:{package_name}"
            cached = await cache_service.get(cache_key)
            if cached:
                return cached
            
            package = await self.get_package_by_name(db, package_name)
            if not package:
                return None
            
            # Get download stats from database
            stats = {
                "package_name": package_name,
                "total_downloads": package.total_downloads,
                "downloads_last_30_days": package.download_count_last_30_days,
                "downloads_last_7_days": 0,  # Would need separate tracking
                "version_count": package.version_count,
                "latest_version": package.latest_version,
                "created_at": package.created_at,
                "updated_at": package.updated_at,
            }
            
            await cache_service.set(cache_key, stats, ttl=600)  # 10 minutes
            return stats
            
        except Exception as e:
            logger.error("Failed to get package stats", package=package_name, error=str(e))
            return None
    
    async def _get_package_version(
        self, 
        db: AsyncSession, 
        package_id: int, 
        version: str
    ) -> Optional[PackageVersion]:
        """Get specific package version."""
        stmt = select(PackageVersion).where(
            PackageVersion.package_id == package_id,
            PackageVersion.version == version
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _count_package_versions(self, db: AsyncSession, package_id: int) -> int:
        """Count package versions."""
        stmt = select(func.count()).where(PackageVersion.package_id == package_id)
        result = await db.execute(stmt)
        return result.scalar()
    
    async def _create_package_tags(self, db: AsyncSession, package_id: int, keywords: List[str]):
        """Create package tags from keywords."""
        for keyword in keywords:
            tag = PackageTag(package_id=package_id, tag=keyword.lower())
            db.add(tag)
        await db.commit()
    
    async def _flush_download_counts(
        self, 
        db: AsyncSession, 
        package_name: str, 
        version: str, 
        count: int
    ):
        """Flush cached download counts to database."""
        try:
            # Update version download count
            version_stmt = select(PackageVersion).join(Package).where(
                Package.name == package_name,
                PackageVersion.version == version
            )
            version_result = await db.execute(version_stmt)
            package_version = version_result.scalar_one_or_none()
            
            if package_version:
                package_version.download_count += count
                
                # Update package total downloads
                package = package_version.package
                package.total_downloads += count
                
                await db.commit()
                
                # Clear cache
                await cache_service.delete(f"downloads:{package_name}:{version}")
                await cache_service.delete_pattern(f"package:{package_name}:*")
                
        except Exception as e:
            logger.error(
                "Failed to flush download counts",
                package=package_name,
                version=version,
                error=str(e)
            )


# Global package service instance
package_service = PackageService() 