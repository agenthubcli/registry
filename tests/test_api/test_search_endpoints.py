"""
Tests for search API endpoints.
"""

import pytest
from fastapi import status

from app.models.package import PackageType, PackageStatus


@pytest.mark.api
@pytest.mark.asyncio
class TestSearchEndpoints:
    """Test cases for search endpoints."""
    
    async def test_search_packages_success(self, client, test_package, test_user):
        """Test searching packages successfully."""
        response = await client.get(f"/api/v1/search/?q={test_package.name}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "query" in data
        assert data["query"] == test_package.name
        
        # Should find our test package
        assert len(data["results"]) >= 1
        
        # Check first result structure
        result = data["results"][0]
        assert "id" in result
        assert "name" in result
        assert "description" in result
        assert "package_type" in result
        assert "owner" in result
        assert result["owner"]["github_username"] == test_user.github_username
    
    async def test_search_packages_empty_query(self, client):
        """Test search with empty query."""
        response = await client.get("/api/v1/search/?q=")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_search_packages_no_results(self, client):
        """Test search with query that returns no results."""
        response = await client.get("/api/v1/search/?q=nonexistent-package-xyz-123")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["results"] == []
        assert data["total"] == 0
    
    async def test_search_packages_with_package_type_filter(self, client, db_session, test_user):
        """Test searching with package type filter."""
        from app.models.package import Package
        
        # Create packages of different types
        tool_package = Package(
            name="test-tool",
            normalized_name="test-tool",
            package_type=PackageType.TOOL,
            description="A test tool package",
            owner_id=test_user.id,
        )
        agent_package = Package(
            name="test-agent",
            normalized_name="test-agent",
            package_type=PackageType.AGENT,
            description="A test agent package",
            owner_id=test_user.id,
        )
        
        db_session.add(tool_package)
        db_session.add(agent_package)
        await db_session.commit()
        
        # Search for only tool packages
        response = await client.get("/api/v1/search/?q=test&package_type=tool")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package_type"] == "tool"
        
        # All results should be tool packages
        for result in data["results"]:
            assert result["package_type"] == "tool"
    
    async def test_search_packages_pagination(self, client, db_session, test_user):
        """Test search pagination."""
        from app.models.package import Package
        
        # Create multiple packages
        packages = []
        for i in range(25):  # More than default limit of 20
            package = Package(
                name=f"test-package-{i:02d}",
                normalized_name=f"test-package-{i:02d}",
                package_type=PackageType.TOOL,
                description=f"Test package number {i}",
                owner_id=test_user.id,
            )
            packages.append(package)
        
        db_session.add_all(packages)
        await db_session.commit()
        
        # Test first page
        response = await client.get("/api/v1/search/?q=test-package&limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["results"]) == 10
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert data["total"] >= 25
        
        # Test second page
        response = await client.get("/api/v1/search/?q=test-package&limit=10&offset=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data["results"]) == 10
        assert data["offset"] == 10
    
    async def test_search_packages_sorting(self, client, db_session, test_user):
        """Test search result sorting."""
        from app.models.package import Package
        
        # Create packages with different download counts
        high_downloads = Package(
            name="popular-package",
            normalized_name="popular-package",
            package_type=PackageType.TOOL,
            description="Very popular package",
            owner_id=test_user.id,
            total_downloads=1000,
        )
        low_downloads = Package(
            name="unpopular-package",
            normalized_name="unpopular-package",
            package_type=PackageType.TOOL,
            description="Less popular package",
            owner_id=test_user.id,
            total_downloads=10,
        )
        
        db_session.add(high_downloads)
        db_session.add(low_downloads)
        await db_session.commit()
        
        # Test sorting by downloads
        response = await client.get("/api/v1/search/?q=package&sort_by=downloads")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["sort_by"] == "downloads"
        
        # Results should be sorted by downloads (descending)
        if len(data["results"]) >= 2:
            first_result = data["results"][0]
            second_result = data["results"][1]
            assert first_result["total_downloads"] >= second_result["total_downloads"]
    
    async def test_search_packages_limit_validation(self, client):
        """Test search limit validation."""
        # Test limit too high
        response = await client.get("/api/v1/search/?q=test&limit=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test negative limit
        response = await client.get("/api/v1/search/?q=test&limit=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test zero limit
        response = await client.get("/api/v1/search/?q=test&limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_search_packages_offset_validation(self, client):
        """Test search offset validation."""
        # Test negative offset
        response = await client.get("/api/v1/search/?q=test&offset=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_popular_packages(self, client, db_session, test_user):
        """Test getting popular packages."""
        from app.models.package import Package
        
        # Create packages with different download counts
        packages = []
        for i in range(5):
            package = Package(
                name=f"popular-package-{i}",
                normalized_name=f"popular-package-{i}",
                package_type=PackageType.TOOL,
                description=f"Popular package {i}",
                owner_id=test_user.id,
                total_downloads=1000 - (i * 100),  # Descending order
            )
            packages.append(package)
        
        db_session.add_all(packages)
        await db_session.commit()
        
        response = await client.get("/api/v1/search/popular")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "results" in data
        assert "limit" in data
        
        # Should be sorted by downloads descending
        if len(data["results"]) >= 2:
            for i in range(len(data["results"]) - 1):
                current = data["results"][i]["total_downloads"]
                next_item = data["results"][i + 1]["total_downloads"]
                assert current >= next_item
    
    async def test_get_popular_packages_with_type_filter(self, client, db_session, test_user):
        """Test getting popular packages with type filter."""
        from app.models.package import Package
        
        # Create tool and agent packages
        tool_package = Package(
            name="popular-tool",
            normalized_name="popular-tool",
            package_type=PackageType.TOOL,
            description="Popular tool",
            owner_id=test_user.id,
            total_downloads=500,
        )
        agent_package = Package(
            name="popular-agent",
            normalized_name="popular-agent",
            package_type=PackageType.AGENT,
            description="Popular agent",
            owner_id=test_user.id,
            total_downloads=600,
        )
        
        db_session.add(tool_package)
        db_session.add(agent_package)
        await db_session.commit()
        
        # Get only agent packages
        response = await client.get("/api/v1/search/popular?package_type=agent")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package_type"] == "agent"
        
        # All results should be agent packages
        for result in data["results"]:
            assert result["package_type"] == "agent"
    
    async def test_get_recent_packages(self, client, test_package, test_user):
        """Test getting recent packages."""
        response = await client.get("/api/v1/search/recent")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "results" in data
        assert "limit" in data
        
        # Should include our test package
        package_names = [pkg["name"] for pkg in data["results"]]
        assert test_package.name in package_names
    
    async def test_get_recent_packages_with_type_filter(self, client, test_package):
        """Test getting recent packages with type filter."""
        response = await client.get(f"/api/v1/search/recent?package_type={test_package.package_type.value}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package_type"] == test_package.package_type.value
        
        # All results should match the package type
        for result in data["results"]:
            assert result["package_type"] == test_package.package_type.value
    
    async def test_get_trending_packages(self, client, db_session, test_user):
        """Test getting trending packages."""
        from app.models.package import Package
        
        # Create packages with different recent download counts
        trending_package = Package(
            name="trending-package",
            normalized_name="trending-package",
            package_type=PackageType.TOOL,
            description="Trending package",
            owner_id=test_user.id,
            total_downloads=500,
            download_count_last_30_days=200,  # High recent downloads
        )
        
        db_session.add(trending_package)
        await db_session.commit()
        
        response = await client.get("/api/v1/search/trending")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "results" in data
        assert "limit" in data
        
        # Should include our trending package
        package_names = [pkg["name"] for pkg in data["results"]]
        assert "trending-package" in package_names
    
    async def test_get_trending_packages_with_type_filter(self, client, test_package):
        """Test getting trending packages with type filter."""
        response = await client.get(f"/api/v1/search/trending?package_type={test_package.package_type.value}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package_type"] == test_package.package_type.value
    
    async def test_search_packages_invalid_sort_by(self, client):
        """Test search with invalid sort_by parameter."""
        response = await client.get("/api/v1/search/?q=test&sort_by=invalid_sort")
        
        # Should still work, probably defaults to relevance
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sort_by"] == "invalid_sort"  # Parameter is preserved
    
    async def test_search_packages_invalid_package_type(self, client):
        """Test search with invalid package type."""
        response = await client.get("/api/v1/search/?q=test&package_type=invalid_type")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_search_case_insensitive(self, client, test_package):
        """Test that search is case insensitive."""
        # Search with different cases
        test_cases = [
            test_package.name.upper(),
            test_package.name.lower(),
            test_package.name.title(),
        ]
        
        for query in test_cases:
            response = await client.get(f"/api/v1/search/?q={query}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Should find the package regardless of case
            package_names = [pkg["name"] for pkg in data["results"]]
            assert test_package.name in package_names
    
    async def test_search_special_characters(self, client):
        """Test search with special characters."""
        special_queries = [
            "test-package",
            "test_package", 
            "test.package",
            "test@package",
            "test+package",
        ]
        
        for query in special_queries:
            response = await client.get(f"/api/v1/search/?q={query}")
            # Should not crash, even if no results
            assert response.status_code == status.HTTP_200_OK
    
    async def test_search_long_query(self, client):
        """Test search with very long query."""
        long_query = "a" * 1000
        response = await client.get(f"/api/v1/search/?q={long_query}")
        
        # Should handle gracefully
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["query"] == long_query
    
    async def test_search_unicode_query(self, client):
        """Test search with unicode characters."""
        unicode_queries = [
            "测试包",  # Chinese
            "пакет",   # Russian
            "パッケージ", # Japanese
            "emoji-🚀-package",
        ]
        
        for query in unicode_queries:
            response = await client.get(f"/api/v1/search/?q={query}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["query"] == query
    
    async def test_search_results_structure(self, client, test_package, test_user):
        """Test that search results have correct structure."""
        response = await client.get(f"/api/v1/search/?q={test_package.name}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check top-level structure
        required_fields = ["results", "total", "limit", "offset", "query", "sort_by"]
        for field in required_fields:
            assert field in data
        
        # Check individual result structure
        if data["results"]:
            result = data["results"][0]
            required_result_fields = [
                "id", "name", "description", "package_type", 
                "latest_version", "total_downloads", "created_at", 
                "updated_at", "owner"
            ]
            for field in required_result_fields:
                assert field in result
            
            # Check owner structure
            owner = result["owner"]
            required_owner_fields = ["id", "github_username", "display_name", "github_avatar_url"]
            for field in required_owner_fields:
                assert field in owner 