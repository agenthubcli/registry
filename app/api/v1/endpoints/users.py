"""
User management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.user import User
from app.models.package import Package, PackageStatus
from app.api.dependencies import get_current_user
from app.schemas.user import UserProfile
from app.schemas.package import UserPackages, ErrorResponse, PackageTypeEnum
from typing import Optional

router = APIRouter()


@router.get(
    "/{username}",
    response_model=UserProfile,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"}
    },
    summary="Get user profile",
    description="Get public profile information for a user"
)
async def get_user_profile(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user profile by username."""
    stmt = select(User).where(
        User.github_username == username,
        User.is_active == True
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.public_profile


@router.get(
    "/{username}/packages",
    response_model=UserPackages,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"}
    },
    summary="Get user packages",
    description="Get packages owned by a specific user"
)
async def get_user_packages(
    username: str,
    package_type: Optional[PackageTypeEnum] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """Get packages owned by a specific user."""
    
    # First check if user exists
    user_stmt = select(User).where(
        User.github_username == username,
        User.is_active == True
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build packages query
    packages_query = select(Package).where(
        Package.owner_id == user.id,
        Package.status == PackageStatus.PUBLISHED
    )
    
    # Filter by package type if provided
    if package_type:
        packages_query = packages_query.where(Package.package_type == package_type.value)
    
    # Get total count
    count_result = await db.execute(packages_query)
    total_packages = len(count_result.scalars().all())
    
    # Apply pagination and ordering
    packages_query = packages_query.order_by(Package.created_at.desc()).limit(limit).offset(offset)
    
    # Execute query
    packages_result = await db.execute(packages_query)
    packages = packages_result.scalars().all()
    
    return UserPackages(
        username=username,
        packages=[package.public_info for package in packages],
        total_packages=total_packages,
        limit=limit,
        offset=offset
    ) 