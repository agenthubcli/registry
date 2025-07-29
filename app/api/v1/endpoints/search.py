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
from app.schemas.package import SearchResults, PackageTypeEnum, ErrorResponse

router = APIRouter()


@router.get(
    "/",
    response_model=SearchResults,
    responses={
        422: {"model": ErrorResponse, "description": "Invalid search parameters"}
    },
    summary="Search packages",
    description="Search for packages by name, description, or keywords"
)
async def search_packages(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    package_type: Optional[PackageTypeEnum] = Query(None, description="Filter by package type"),
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
        query = query.where(Package.package_type == package_type.value)
    
    # Add sorting
    if sort_by == "downloads":
        query = query.order_by(desc(Package.total_downloads))
    elif sort_by == "created":
        query = query.order_by(desc(Package.created_at))
    elif sort_by == "updated":
        query = query.order_by(desc(Package.updated_at))
    else:  # relevance (default)
        # TODO: Implement relevance scoring
        query = query.order_by(desc(Package.created_at))
    
    # Get total count (before pagination)
    count_query = query
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return SearchResults(
        results=[package.public_info for package in packages],
        total=total,
        limit=limit,
        offset=offset,
        query=q,
        package_type=package_type,
        sort_by=sort_by
    )


@router.get(
    "/popular",
    response_model=SearchResults,
    summary="Get popular packages",
    description="Get packages sorted by download count"
)
async def get_popular_packages(
    package_type: Optional[PackageTypeEnum] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """Get popular packages sorted by download count."""
    
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    ).order_by(desc(Package.total_downloads))
    
    # Filter by package type
    if package_type:
        query = query.where(Package.package_type == package_type.value)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return SearchResults(
        results=[package.public_info for package in packages],
        total=total,
        limit=limit,
        offset=offset,
        query="",
        package_type=package_type,
        sort_by="downloads"
    )


@router.get(
    "/recent",
    response_model=SearchResults,
    summary="Get recent packages",
    description="Get recently published packages"
)
async def get_recent_packages(
    package_type: Optional[PackageTypeEnum] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """Get recently published packages."""
    
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    ).order_by(desc(Package.created_at))
    
    # Filter by package type
    if package_type:
        query = query.where(Package.package_type == package_type.value)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return SearchResults(
        results=[package.public_info for package in packages],
        total=total,
        limit=limit,
        offset=offset,
        query="",
        package_type=package_type,
        sort_by="created"
    )


@router.get(
    "/trending",
    response_model=SearchResults,
    summary="Get trending packages",
    description="Get packages with high recent download activity"
)
async def get_trending_packages(
    package_type: Optional[PackageTypeEnum] = Query(None, description="Filter by package type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """Get trending packages with high recent download activity."""
    
    query = select(Package).where(
        Package.status == PackageStatus.PUBLISHED
    ).order_by(desc(Package.download_count_last_30_days))
    
    # Filter by package type
    if package_type:
        query = query.where(Package.package_type == package_type.value)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return SearchResults(
        results=[package.public_info for package in packages],
        total=total,
        limit=limit,
        offset=offset,
        query="",
        package_type=package_type,
        sort_by="trending"
    ) 