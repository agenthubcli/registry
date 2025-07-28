"""
Search API endpoints for package discovery.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, func
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.package import Package, PackageType, PackageStatus
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def search_packages(
    q: str = Query(..., min_length=1, description="Search query"),
    package_type: Optional[PackageType] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("relevance", description="Sort by: relevance, downloads, created, updated"),
    db: AsyncSession = Depends(get_db)
):
    """Search packages by name, description, and keywords."""
    
    # Build base query
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    )
    
    # Add search filters
    search_conditions = []
    
    # Search in name (highest priority)
    search_conditions.append(Package.name.ilike(f"%{q}%"))
    
    # Search in description
    search_conditions.append(Package.description.ilike(f"%{q}%"))
    
    # Search in keywords (JSON array contains)
    search_conditions.append(
        func.json_extract_path_text(Package.keywords, 'keywords').ilike(f"%{q}%")
    )
    
    # Combine search conditions with OR
    query = query.where(or_(*search_conditions))
    
    # Filter by package type
    if package_type:
        query = query.where(Package.package_type == package_type)
    
    # Apply sorting
    if sort_by == "downloads":
        query = query.order_by(desc(Package.total_downloads))
    elif sort_by == "created":
        query = query.order_by(desc(Package.created_at))
    elif sort_by == "updated":
        query = query.order_by(desc(Package.updated_at))
    else:  # relevance (default)
        # For now, order by exact name matches first, then by downloads
        query = query.order_by(
            Package.name.ilike(f"{q}%").desc(),  # Exact prefix matches first
            desc(Package.total_downloads)
        )
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Include owner information
    query = query.options(joinedload(Package.owner))
    
    # Execute query
    result = await db.execute(query)
    packages = result.scalars().all()
    
    # Get total count for pagination
    count_query = select(func.count(Package.id)).where(
        Package.status == PackageStatus.PUBLISHED
    ).where(or_(*search_conditions))
    
    if package_type:
        count_query = count_query.where(Package.package_type == package_type)
    
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()
    
    # Format results
    results = []
    for package in packages:
        results.append({
            **package.public_info,
            "owner": package.owner.public_profile,
        })
    
    return {
        "results": results,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "query": q,
        "package_type": package_type.value if package_type else None,
        "sort_by": sort_by,
    }


@router.get("/popular")
async def get_popular_packages(
    package_type: Optional[PackageType] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get popular packages by download count."""
    
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    ).order_by(desc(Package.total_downloads))
    
    if package_type:
        query = query.where(Package.package_type == package_type)
    
    query = query.limit(limit).options(joinedload(Package.owner))
    
    result = await db.execute(query)
    packages = result.scalars().all()
    
    results = []
    for package in packages:
        results.append({
            **package.public_info,
            "owner": package.owner.public_profile,
        })
    
    return {
        "results": results,
        "limit": limit,
        "package_type": package_type.value if package_type else None,
    }


@router.get("/recent")
async def get_recent_packages(
    package_type: Optional[PackageType] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get recently published packages."""
    
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    ).order_by(desc(Package.created_at))
    
    if package_type:
        query = query.where(Package.package_type == package_type)
    
    query = query.limit(limit).options(joinedload(Package.owner))
    
    result = await db.execute(query)
    packages = result.scalars().all()
    
    results = []
    for package in packages:
        results.append({
            **package.public_info,
            "owner": package.owner.public_profile,
        })
    
    return {
        "results": results,
        "limit": limit,
        "package_type": package_type.value if package_type else None,
    }


@router.get("/trending")
async def get_trending_packages(
    package_type: Optional[PackageType] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get trending packages (based on recent downloads)."""
    
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    ).order_by(desc(Package.download_count_last_30_days))
    
    if package_type:
        query = query.where(Package.package_type == package_type)
    
    query = query.limit(limit).options(joinedload(Package.owner))
    
    result = await db.execute(query)
    packages = result.scalars().all()
    
    results = []
    for package in packages:
        results.append({
            **package.public_info,
            "owner": package.owner.public_profile,
        })
    
    return {
        "results": results,
        "limit": limit,
        "package_type": package_type.value if package_type else None,
    } 