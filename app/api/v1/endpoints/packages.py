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

router = APIRouter()


@router.get("/{package_name}")
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


@router.get("/{package_name}/versions")
async def get_package_versions(
    package_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all versions of a package."""
    stmt = select(Package).where(Package.name == package_name)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    versions_stmt = select(PackageVersion).where(
        PackageVersion.package_id == package.id,
        PackageVersion.status == VersionStatus.PUBLISHED
    ).order_by(desc(PackageVersion.published_at))
    
    versions_result = await db.execute(versions_stmt)
    versions = versions_result.scalars().all()
    
    return {
        "package_name": package.name,
        "versions": [v.public_info for v in versions]
    }


@router.get("/{package_name}/{version}")
async def get_package_version(
    package_name: str,
    version: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific package version details."""
    stmt = select(Package).where(Package.name == package_name)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()
    
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
    
    return {
        "package": package.public_info,
        "version": package_version.public_info,
        "owner": package.owner.public_profile,
    }


@router.get("/{package_name}/{version}/download")
async def download_package(
    package_name: str,
    version: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Download a package version."""
    # Get package version
    stmt = select(Package).where(Package.name == package_name)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()
    
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


@router.post("/publish")
async def publish_package(
    file: UploadFile = File(...),
    package_type: str = Form(...),
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
        pkg_type = PackageType(package_type)
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
    
    if package:
        # Check if user owns the package
        if package.owner_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to publish to this package"
            )
        
        # Check if version already exists
        version_stmt = select(PackageVersion).where(
            PackageVersion.package_id == package.id,
            PackageVersion.version == version
        )
        version_result = await db.execute(version_stmt)
        existing_version = version_result.scalar_one_or_none()
        
        if existing_version:
            raise HTTPException(
                status_code=409,
                detail=f"Version {version} already exists for package {package_name}"
            )
    else:
        # Create new package
        package = Package(
            name=package_name,
            normalized_name=package_name.lower().replace("_", "-"),
            description=manifest.get("description"),
            package_type=pkg_type,
            owner_id=current_user.id,
        )
        db.add(package)
        await db.commit()
        await db.refresh(package)
    
    try:
        # Upload to S3
        s3_key, file_hash, file_size = await storage_service.upload_package(
            file_data,
            package_name,
            version,
            file.filename,
            file.content_type or "application/octet-stream"
        )
        
        # Create package version
        package_version = PackageVersion(
            package_id=package.id,
            version=version,
            description=manifest.get("description"),
            filename=file.filename,
            file_size=file_size,
            file_hash_sha256=file_hash,
            s3_key=s3_key,
            manifest=manifest,
            status=VersionStatus.PUBLISHED,
            published_by_id=current_user.id,
            published_at=db.func.now(),
        )
        
        db.add(package_version)
        
        # Update package metadata
        package.latest_version = version
        package.latest_version_published_at = db.func.now()
        package.version_count += 1
        
        await db.commit()
        await db.refresh(package_version)
        
        return {
            "message": "Package published successfully",
            "package": package.public_info,
            "version": package_version.public_info,
        }
    
    except Exception as e:
        await db.rollback()
        # Clean up S3 file if database commit failed
        # TODO: Add cleanup logic
        raise HTTPException(status_code=500, detail="Failed to publish package")


@router.delete("/{package_name}")
async def delete_package(
    package_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a package (if deletion is enabled)."""
    
    if not settings.ENABLE_PACKAGE_DELETION:
        raise HTTPException(status_code=403, detail="Package deletion is not enabled")
    
    stmt = select(Package).where(Package.name == package_name)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Check permissions
    if package.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this package"
        )
    
    try:
        # Delete all S3 files for this package
        for version in package.versions:
            await storage_service.delete_package(version.s3_key)
        
        # Delete from database (cascade will handle versions)
        await db.delete(package)
        await db.commit()
        
        return {"message": "Package deleted successfully"}
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete package")


@router.get("/{package_name}/stats")
async def get_package_stats(
    package_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get package download statistics."""
    stmt = select(Package).where(Package.name == package_name)
    result = await db.execute(stmt)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # TODO: Implement detailed analytics from download_stats table
    
    return {
        "package_name": package.name,
        "total_downloads": package.total_downloads,
        "downloads_last_30_days": package.download_count_last_30_days,
        "version_count": package.version_count,
    } 