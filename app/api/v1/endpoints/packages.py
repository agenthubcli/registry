"""
Package management API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import io
import yaml
import json

from app.core.database import get_db
from app.models.user import User
from app.models.package import Package, PackageVersion, PackageType, VersionStatus
from app.services.storage import storage_service
from app.api.dependencies import get_current_user, get_current_user_optional
from app.core.config import settings
from app.schemas.package import (
    PackageDetails, PackageVersions, PackageVersionDetails, PackageStats,
    PublishSuccess, ErrorResponse, MessageResponse, PackageTypeEnum
)

router = APIRouter()


@router.get(
    "/{package_name}",
    response_model=PackageDetails,
    responses={
        404: {"model": ErrorResponse, "description": "Package not found"}
    },
    summary="Get package details",
    description="Get detailed information about a package including all versions"
)
async def get_package(
    package_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get package details by name."""
    stmt = select(Package).where(
        Package.name == package_name,
        Package.status == "published"
    )
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get versions
    versions_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.status == VersionStatus.PUBLISHED
    ).order_by(desc(PackageVersion.published_at))
    
    versions_result = await db.execute(versions_stmt)
    versions = versions_result.scalars().all()
    
    return {
        "package": package.public_info,
        "owner": package.owner.public_profile,
        "versions": [v.public_info for v in versions],
        "latest_version": versions[0].public_info if versions else None,
    }


@router.get(
    "/{package_name}/versions",
    response_model=PackageVersions,
    responses={
        404: {"model": ErrorResponse, "description": "Package not found"}
    },
    summary="Get package versions",
    description="Get all versions of a package"
)
async def get_package_versions(
    package_name: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get all versions of a package."""
    # Check if package exists
    package_stmt = select(Package).where(
        Package.name == package_name,
        Package.status == "published"
    )
    package_result = await db.execute(package_stmt)
    package = package_result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get versions with pagination
    versions_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.status == VersionStatus.PUBLISHED
    ).order_by(desc(PackageVersion.published_at)).limit(limit).offset(offset)
    
    versions_result = await db.execute(versions_stmt)
    versions = versions_result.scalars().all()
    
    # Get total count
    count_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.status == VersionStatus.PUBLISHED
    )
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())
    
    return PackageVersions(
        package_name=package_name,
        versions=[v.public_info for v in versions],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{package_name}/{version}",
    response_model=PackageVersionDetails,
    responses={
        404: {"model": ErrorResponse, "description": "Package or version not found"}
    },
    summary="Get specific version",
    description="Get details about a specific package version"
)
async def get_package_version(
    package_name: str,
    version: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details about a specific package version."""
    # First get the package
    package_stmt = select(Package).where(
        Package.name == package_name,
        Package.status == "published"
    )
    package_result = await db.execute(package_stmt)
    package = package_result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get specific version
    version_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version,
        PackageVersion.status == VersionStatus.PUBLISHED
    )
    version_result = await db.execute(version_stmt)
    package_version = version_result.scalar_one_or_none()
    
    if not package_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return PackageVersionDetails(
        package=package.public_info,
        version=package_version.public_info,
        owner=package.owner.public_profile
    )


@router.get(
    "/{package_name}/{version}/download",
    response_model=None,
    responses={
        404: {"model": ErrorResponse, "description": "Package or version not found"}
    },
    summary="Download package version",
    description="Download a specific package version"
)
async def download_package(
    package_name: str,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Download a package version."""
    # Get package version
    package_stmt = select(Package).where(Package.name == package_name)
    package_result = await db.execute(package_stmt)
    package = package_result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    version_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.version == version,
        PackageVersion.status == VersionStatus.PUBLISHED
    )
    
    version_result = await db.execute(version_stmt)
    package_version = version_result.scalar_one_or_none()
    
    if not package_version:
        raise HTTPException(status_code=404, detail="Package version not found")
    
    try:
        # Download from S3
        file_data = await storage_service.download_package(package_version.s3_key)
        
        # Update download stats (in background)
        # TODO: Add async background task for download tracking
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={package_version.filename}",
                "Content-Length": str(package_version.file_size),
                "X-Package-Name": package.name,
                "X-Package-Version": package_version.version,
            }
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Package file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to download package")


@router.post(
    "/publish",
    response_model=PublishSuccess,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid package data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized to publish"},
        409: {"model": ErrorResponse, "description": "Package version already exists"},
        413: {"model": ErrorResponse, "description": "Package too large"}
    },
    summary="Publish package",
    description="Upload and publish a new package or version"
)
async def publish_package(
    file: UploadFile = File(..., description="Package file (tar.gz, zip, etc.)"),
    package_type: PackageTypeEnum = Form(..., description="Type of package"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish a new package or version."""
    
    if not current_user.can_publish_package():
        raise HTTPException(
            status_code=403, 
            detail="User not authorized to publish packages"
        )
    
    # Validate package type
    try:
        pkg_type = PackageType(package_type.value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid package type. Must be one of: {', '.join([t.value for t in PackageType])}"
        )
    
    # Read and validate file
    file_data = await file.read()
    
    if len(file_data) > settings.MAX_PACKAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Package size exceeds maximum of {settings.MAX_PACKAGE_SIZE_MB}MB"
        )
    
    # TODO: Extract and validate package manifest
    # For now, assume the file contains a valid package.yaml
    try:
        # This is a simplified version - in reality you'd extract the manifest
        # from the package archive and validate it
        manifest = {
            "name": file.filename.replace(".tar.gz", "").replace(".zip", ""),
            "version": "1.0.0",  # Extract from manifest
            "type": package_type,
            "description": "Package description",  # Extract from manifest
        }
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid package format")
    
    package_name = manifest["name"]
    version = manifest["version"]
    
    # Check if package exists
    package_stmt = select(Package).where(Package.name == package_name)
    package_result = await db.execute(package_stmt)
    package = package_result.scalar_one_or_none()
    
    # Return mock success response for now
    return PublishSuccess(
        message="Package published successfully",
        package={
            "id": 1,
            "name": package_name,
            "description": manifest.get("description"),
            "package_type": package_type,
            "latest_version": version,
            "total_downloads": 0,
            "download_count_last_30_days": 0,
            "version_count": 1,
            "owner": current_user.public_profile,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z"
        },
        version={
            "id": 1,
            "version": version,
            "download_count": 0,
            "file_size": len(file_data),
            "file_hash_sha256": "abc123...",
            "download_url": f"https://example.com/download/{package_name}/{version}",
            "published_at": "2023-01-01T00:00:00Z",
            "created_at": "2023-01-01T00:00:00Z"
        }
    )


@router.delete(
    "/{package_name}",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized to delete package"},
        404: {"model": ErrorResponse, "description": "Package not found"}
    },
    summary="Delete package",
    description="Delete a package and all its versions (admin or owner only)"
)
async def delete_package(
    package_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a package and all its versions."""
    if not settings.ENABLE_PACKAGE_DELETION:
        raise HTTPException(status_code=403, detail="Package deletion is disabled")
    
    # Check if package exists
    package_stmt = select(Package).where(Package.name == package_name)
    package_result = await db.execute(package_stmt)
    package = package_result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Check permissions (owner or admin)
    if package.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this package")
    
    # TODO: Implement actual deletion logic
    return MessageResponse(message=f"Package '{package_name}' deleted successfully")


@router.get(
    "/{package_name}/stats",
    response_model=PackageStats,
    responses={
        404: {"model": ErrorResponse, "description": "Package not found"}
    },
    summary="Get package statistics",
    description="Get download and usage statistics for a package"
)
async def get_package_stats(
    package_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get package statistics."""
    package_stmt = select(Package).where(
        Package.name == package_name,
        Package.status == "published"
    )
    package_result = await db.execute(package_stmt)
    package = package_result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Get version count
    version_count_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.status == VersionStatus.PUBLISHED
    )
    version_count_result = await db.execute(version_count_stmt)
    version_count = len(version_count_result.scalars().all())
    
    return PackageStats(
        package_name=package_name,
        total_downloads=package.total_downloads or 0,
        downloads_last_30_days=package.download_count_last_30_days or 0,
        downloads_last_7_days=0,  # TODO: Implement 7-day stats
        version_count=version_count,
        latest_version=package.latest_version or "0.0.0"
    ) 