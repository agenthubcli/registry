"""
User management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.user import User
from app.models.package import Package
from app.api.dependencies import get_current_user

router = APIRouter()


@router.get("/{username}")
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


@router.get("/{username}/packages")
async def get_user_packages(
    username: str,
    db: AsyncSession = Depends(get_db)
):
    """Get packages owned by a user."""
    # Get user
    user_stmt = select(User).where(
        User.github_username == username,
        User.is_active == True
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's packages
    packages_stmt = select(Package).where(
        Package.owner_id == user.id,
        Package.status == "published"
    ).options(joinedload(Package.owner))
    
    packages_result = await db.execute(packages_stmt)
    packages = packages_result.scalars().all()
    
    return {
        "user": user.public_profile,
        "packages": [pkg.public_info for pkg in packages],
        "total_packages": len(packages),
    } 