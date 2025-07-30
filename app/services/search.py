"""
Search service for AgentHub Registry package discovery.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc, func, text, and_
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.package import Package, PackageType, PackageStatus, PackageTag
from app.models.user import User
from app.services.cache import cache_service

logger = structlog.get_logger()


class SearchService:
    """Service for package search and discovery."""
    
    def __init__(self):
        """Initialize the search service."""
        self.search_cache_ttl = 300  # 5 minutes
        self.trending_cache_ttl = 1800  # 30 minutes
        self.popular_cache_ttl = 3600  # 1 hour
    
    def _normalize_query(self, query: str) -> str:
        """Normalize search query."""
        # Remove special characters and normalize whitespace
        query = re.sub(r'[^\w\s\-]', '', query)
        query = re.sub(r'\s+', ' ', query)
        return query.strip().lower()
    
    def _build_search_terms(self, query: str) -> List[str]:
        """Build search terms from query."""
        normalized = self._normalize_query(query)
        terms = normalized.split()
        
        # Also include partial matches for package names
        search_terms = []
        search_terms.extend(terms)
        
        # Add combinations for multi-word queries
        if len(terms) > 1:
            search_terms.append(' '.join(terms))
        
        return search_terms
    
    async def search_packages(
        self,
        db: AsyncSession,
        query: str,
        package_type: Optional[PackageType] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        include_prerelease: bool = False
    ) -> Tuple[List[Package], int]:
        """Search for packages with filters and sorting."""
        try:
            # Create cache key
            cache_key = f"search:{hash(query)}:{package_type}:{limit}:{offset}:{sort_by}:{include_prerelease}"
            cached = await cache_service.get(cache_key)
            if cached:
                logger.debug("Search results retrieved from cache", query=query)
                return cached["packages"], cached["total"]
            
            # Build base query
            base_query = select(Package).options(
                joinedload(Package.owner)
            ).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False
            )
            
            # Add package type filter
            if package_type:
                base_query = base_query.where(Package.package_type == package_type)
            
            # Build search conditions
            search_conditions = self._build_search_conditions(query)
            
            if search_conditions:
                search_query = base_query.where(or_(*search_conditions))
            else:
                search_query = base_query
            
            # Get total count
            count_query = select(func.count()).select_from(search_query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply sorting
            sorted_query = self._apply_sorting(search_query, sort_by, query)
            
            # Apply pagination
            final_query = sorted_query.limit(limit).offset(offset)
            
            # Execute query
            result = await db.execute(final_query)
            packages = result.scalars().all()
            
            # Cache results
            cache_data = {
                "packages": [self._package_to_dict(p) for p in packages],
                "total": total
            }
            await cache_service.set(cache_key, cache_data, ttl=self.search_cache_ttl)
            
            logger.info(
                "Package search completed",
                query=query,
                results=len(packages),
                total=total
            )
            
            return list(packages), total
            
        except Exception as e:
            logger.error("Failed to search packages", query=query, error=str(e))
            return [], 0
    
    def _build_search_conditions(self, query: str) -> List:
        """Build search conditions for query."""
        conditions = []
        search_terms = self._build_search_terms(query)
        
        for term in search_terms:
            if not term:
                continue
                
            # Search in package name (highest priority)
            conditions.append(Package.name.ilike(f"%{term}%"))
            
            # Search in description
            conditions.append(Package.description.ilike(f"%{term}%"))
            
            # Search in keywords (JSON field)
            conditions.append(
                func.jsonb_array_elements_text(Package.keywords).op('ILIKE')(f"%{term}%")
            )
            
            # Search in normalized name
            conditions.append(Package.normalized_name.ilike(f"%{term}%"))
        
        return conditions
    
    def _apply_sorting(self, query, sort_by: str, search_query: str = ""):
        """Apply sorting to search query."""
        if sort_by == "downloads":
            return query.order_by(desc(Package.total_downloads))
        elif sort_by == "created":
            return query.order_by(desc(Package.created_at))
        elif sort_by == "updated":
            return query.order_by(desc(Package.updated_at))
        elif sort_by == "name":
            return query.order_by(Package.name)
        elif sort_by == "relevance":
            # For relevance, prioritize exact name matches, then partial matches
            return query.order_by(
                # Exact name match first
                desc(Package.name == search_query.lower()),
                # Name starts with query
                desc(Package.name.startswith(search_query.lower())),
                # Then by download count
                desc(Package.total_downloads),
                # Finally by update time
                desc(Package.updated_at)
            )
        else:
            # Default to relevance
            return self._apply_sorting(query, "relevance", search_query)
    
    async def get_popular_packages(
        self,
        db: AsyncSession,
        package_type: Optional[PackageType] = None,
        limit: int = 20,
        days: int = 30
    ) -> List[Package]:
        """Get popular packages based on download counts."""
        try:
            cache_key = f"popular:{package_type}:{limit}:{days}"
            cached = await cache_service.get(cache_key)
            if cached:
                return [Package(**p) for p in cached]
            
            query = select(Package).options(
                joinedload(Package.owner)
            ).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False
            )
            
            if package_type:
                query = query.where(Package.package_type == package_type)
            
            # Sort by download count in the specified period
            if days <= 30:
                query = query.order_by(desc(Package.download_count_last_30_days))
            else:
                query = query.order_by(desc(Package.total_downloads))
            
            query = query.limit(limit)
            
            result = await db.execute(query)
            packages = result.scalars().all()
            
            # Cache results
            cache_data = [self._package_to_dict(p) for p in packages]
            await cache_service.set(cache_key, cache_data, ttl=self.popular_cache_ttl)
            
            return list(packages)
            
        except Exception as e:
            logger.error("Failed to get popular packages", error=str(e))
            return []
    
    async def get_trending_packages(
        self,
        db: AsyncSession,
        package_type: Optional[PackageType] = None,
        limit: int = 20
    ) -> List[Package]:
        """Get trending packages based on recent activity."""
        try:
            cache_key = f"trending:{package_type}:{limit}"
            cached = await cache_service.get(cache_key)
            if cached:
                return [Package(**p) for p in cached]
            
            # Calculate trending based on recent downloads vs historical average
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            query = select(Package).options(
                joinedload(Package.owner)
            ).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False,
                Package.created_at <= thirty_days_ago,  # Exclude very new packages
                Package.download_count_last_30_days > 0
            )
            
            if package_type:
                query = query.where(Package.package_type == package_type)
            
            # Order by trending score (recent downloads / total downloads ratio)
            query = query.order_by(
                desc(
                    func.cast(Package.download_count_last_30_days, func.Float) / 
                    func.greatest(Package.total_downloads, 1)
                ),
                desc(Package.download_count_last_30_days)
            ).limit(limit)
            
            result = await db.execute(query)
            packages = result.scalars().all()
            
            # Cache results
            cache_data = [self._package_to_dict(p) for p in packages]
            await cache_service.set(cache_key, cache_data, ttl=self.trending_cache_ttl)
            
            return list(packages)
            
        except Exception as e:
            logger.error("Failed to get trending packages", error=str(e))
            return []
    
    async def get_recent_packages(
        self,
        db: AsyncSession,
        package_type: Optional[PackageType] = None,
        limit: int = 20
    ) -> List[Package]:
        """Get recently published packages."""
        try:
            cache_key = f"recent:{package_type}:{limit}"
            cached = await cache_service.get(cache_key)
            if cached:
                return [Package(**p) for p in cached]
            
            query = select(Package).options(
                joinedload(Package.owner)
            ).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False
            )
            
            if package_type:
                query = query.where(Package.package_type == package_type)
            
            query = query.order_by(desc(Package.created_at)).limit(limit)
            
            result = await db.execute(query)
            packages = result.scalars().all()
            
            # Cache results
            cache_data = [self._package_to_dict(p) for p in packages]
            await cache_service.set(cache_key, cache_data, ttl=self.search_cache_ttl)
            
            return list(packages)
            
        except Exception as e:
            logger.error("Failed to get recent packages", error=str(e))
            return []
    
    async def search_by_tag(
        self,
        db: AsyncSession,
        tag: str,
        package_type: Optional[PackageType] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Package], int]:
        """Search packages by tag."""
        try:
            cache_key = f"tag_search:{tag}:{package_type}:{limit}:{offset}"
            cached = await cache_service.get(cache_key)
            if cached:
                return cached["packages"], cached["total"]
            
            # Join with PackageTag table
            query = select(Package).join(PackageTag).options(
                joinedload(Package.owner)
            ).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False,
                PackageTag.tag == tag.lower()
            )
            
            if package_type:
                query = query.where(Package.package_type == package_type)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(desc(Package.total_downloads)).limit(limit).offset(offset)
            
            result = await db.execute(query)
            packages = result.scalars().all()
            
            # Cache results
            cache_data = {
                "packages": [self._package_to_dict(p) for p in packages],
                "total": total
            }
            await cache_service.set(cache_key, cache_data, ttl=self.search_cache_ttl)
            
            return list(packages), total
            
        except Exception as e:
            logger.error("Failed to search by tag", tag=tag, error=str(e))
            return [], 0
    
    async def get_package_suggestions(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10
    ) -> List[str]:
        """Get package name suggestions for autocomplete."""
        try:
            cache_key = f"suggestions:{hash(query)}:{limit}"
            cached = await cache_service.get(cache_key)
            if cached:
                return cached
            
            normalized_query = self._normalize_query(query)
            
            # Search for package names that start with the query
            name_query = select(Package.name).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False,
                Package.name.ilike(f"{normalized_query}%")
            ).order_by(
                desc(Package.total_downloads)
            ).limit(limit)
            
            result = await db.execute(name_query)
            suggestions = [row[0] for row in result.fetchall()]
            
            # Cache suggestions
            await cache_service.set(cache_key, suggestions, ttl=self.search_cache_ttl)
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to get package suggestions", query=query, error=str(e))
            return []
    
    async def get_popular_tags(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get popular tags with package counts."""
        try:
            cache_key = f"popular_tags:{limit}"
            cached = await cache_service.get(cache_key)
            if cached:
                return cached
            
            # Get tags with their package counts
            tag_query = select(
                PackageTag.tag,
                func.count(PackageTag.package_id).label('package_count')
            ).join(Package).where(
                Package.status == PackageStatus.PUBLISHED,
                Package.is_private == False
            ).group_by(PackageTag.tag).order_by(
                desc(func.count(PackageTag.package_id))
            ).limit(limit)
            
            result = await db.execute(tag_query)
            tags = [
                {"tag": row.tag, "package_count": row.package_count}
                for row in result.fetchall()
            ]
            
            # Cache results
            await cache_service.set(cache_key, tags, ttl=self.popular_cache_ttl)
            
            return tags
            
        except Exception as e:
            logger.error("Failed to get popular tags", error=str(e))
            return []
    
    def _package_to_dict(self, package: Package) -> Dict[str, Any]:
        """Convert package to dictionary for caching."""
        return {
            "id": package.id,
            "name": package.name,
            "normalized_name": package.normalized_name,
            "description": package.description,
            "package_type": package.package_type.value,
            "status": package.status.value,
            "is_private": package.is_private,
            "total_downloads": package.total_downloads,
            "download_count_last_30_days": package.download_count_last_30_days,
            "version_count": package.version_count,
            "latest_version": package.latest_version,
            "latest_version_published_at": package.latest_version_published_at.isoformat() if package.latest_version_published_at else None,
            "keywords": package.keywords,
            "homepage": package.homepage,
            "repository": package.repository,
            "documentation": package.documentation,
            "created_at": package.created_at.isoformat(),
            "updated_at": package.updated_at.isoformat(),
            "owner_id": package.owner_id,
        }
    
    async def clear_search_cache(self):
        """Clear all search-related cache entries."""
        try:
            await cache_service.delete_pattern("search:*")
            await cache_service.delete_pattern("popular:*")
            await cache_service.delete_pattern("trending:*")
            await cache_service.delete_pattern("recent:*")
            await cache_service.delete_pattern("tag_search:*")
            await cache_service.delete_pattern("suggestions:*")
            await cache_service.delete_pattern("popular_tags:*")
            
            logger.info("Search cache cleared")
            
        except Exception as e:
            logger.error("Failed to clear search cache", error=str(e))


# Global search service instance
search_service = SearchService() 