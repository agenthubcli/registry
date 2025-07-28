"""
Integration tests for complete workflows in AgentHub Registry.
"""

import pytest
from io import BytesIO
from fastapi import status

from app.services.auth import auth_service


@pytest.mark.integration
@pytest.mark.asyncio
class TestCompleteWorkflows:
    """Integration tests for end-to-end workflows."""
    
    async def test_complete_package_lifecycle(self, client, auth_headers, sample_package_file, mock_s3_service):
        """Test complete package lifecycle: publish -> get -> download -> stats."""
        
        # 1. Publish a package
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "tool"}
        
        publish_response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        
        assert publish_response.status_code == status.HTTP_200_OK
        publish_data = publish_response.json()
        
        package_name = publish_data["package"]["name"]
        version = publish_data["version"]["version"]
        
        # 2. Get package details
        get_response = await client.get(f"/api/v1/packages/{package_name}")
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        
        assert get_data["package"]["name"] == package_name
        assert len(get_data["versions"]) == 1
        assert get_data["versions"][0]["version"] == version
        
        # 3. Download the package
        download_response = await client.get(f"/api/v1/packages/{package_name}/{version}/download")
        assert download_response.status_code == status.HTTP_200_OK
        assert download_response.headers["x-package-name"] == package_name
        assert download_response.headers["x-package-version"] == version
        
        # 4. Get package stats
        stats_response = await client.get(f"/api/v1/packages/{package_name}/stats")
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        
        assert stats_data["package_name"] == package_name
        assert stats_data["version_count"] == 1
    
    async def test_user_authentication_workflow(self, client, mock_httpx, db_session):
        """Test complete user authentication workflow."""
        
        # 1. Get GitHub OAuth URL
        oauth_response = await client.get("/api/v1/auth/github")
        assert oauth_response.status_code == status.HTTP_200_OK
        oauth_data = oauth_response.json()
        assert "oauth_url" in oauth_data
        
        # 2. Simulate OAuth callback (mocked)
        callback_response = await client.get("/api/v1/auth/github/callback?code=test_code&state=test_state")
        assert callback_response.status_code == status.HTTP_200_OK
        callback_data = callback_response.json()
        
        assert "access_token" in callback_data
        assert "refresh_token" in callback_data
        assert "user" in callback_data
        
        access_token = callback_data["access_token"]
        refresh_token = callback_data["refresh_token"]
        
        # 3. Use access token to get user info
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        me_data = me_response.json()
        
        assert me_data["github_username"] == callback_data["user"]["github_username"]
        
        # 4. Refresh the access token
        refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == status.HTTP_200_OK
        refresh_data = refresh_response.json()
        
        assert "access_token" in refresh_data
        new_access_token = refresh_data["access_token"]
        
        # 5. Use new access token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        me_response2 = await client.get("/api/v1/auth/me", headers=new_headers)
        assert me_response2.status_code == status.HTTP_200_OK
        
        # 6. Logout
        logout_response = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == status.HTTP_200_OK
    
    async def test_search_and_discovery_workflow(self, client, db_session, test_user):
        """Test package search and discovery workflow."""
        from app.models.package import Package, PackageType
        
        # 1. Create multiple packages for testing
        packages = []
        for i in range(5):
            package = Package(
                name=f"search-test-package-{i}",
                normalized_name=f"search-test-package-{i}",
                package_type=PackageType.TOOL if i % 2 == 0 else PackageType.AGENT,
                description=f"A test package for search testing number {i}",
                owner_id=test_user.id,
                total_downloads=100 * (i + 1),
                download_count_last_30_days=20 * (i + 1),
                keywords=["search", "test", f"keyword{i}"],
            )
            packages.append(package)
        
        db_session.add_all(packages)
        await db_session.commit()
        
        # 2. Search for packages
        search_response = await client.get("/api/v1/search/?q=search-test")
        assert search_response.status_code == status.HTTP_200_OK
        search_data = search_response.json()
        
        assert search_data["total"] >= 5
        assert len(search_data["results"]) >= 5
        
        # 3. Filter by package type
        tool_search_response = await client.get("/api/v1/search/?q=search-test&package_type=tool")
        assert tool_search_response.status_code == status.HTTP_200_OK
        tool_search_data = tool_search_response.json()
        
        for result in tool_search_data["results"]:
            assert result["package_type"] == "tool"
        
        # 4. Get popular packages
        popular_response = await client.get("/api/v1/search/popular")
        assert popular_response.status_code == status.HTTP_200_OK
        popular_data = popular_response.json()
        
        # Should be sorted by downloads
        if len(popular_data["results"]) >= 2:
            first = popular_data["results"][0]
            second = popular_data["results"][1]
            assert first["total_downloads"] >= second["total_downloads"]
        
        # 5. Get trending packages
        trending_response = await client.get("/api/v1/search/trending")
        assert trending_response.status_code == status.HTTP_200_OK
        trending_data = trending_response.json()
        
        assert "results" in trending_data
        
        # 6. Get recent packages
        recent_response = await client.get("/api/v1/search/recent")
        assert recent_response.status_code == status.HTTP_200_OK
        recent_data = recent_response.json()
        
        assert "results" in recent_data
    
    async def test_user_profile_and_packages_workflow(self, client, auth_headers, test_user, sample_package_file, mock_s3_service):
        """Test user profile and package management workflow."""
        
        # 1. Get user profile
        profile_response = await client.get(f"/api/v1/users/{test_user.github_username}")
        assert profile_response.status_code == status.HTTP_200_OK
        profile_data = profile_response.json()
        
        assert profile_data["github_username"] == test_user.github_username
        initial_package_count = profile_data["total_packages"]
        
        # 2. Publish a package
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "agent"}
        
        publish_response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        assert publish_response.status_code == status.HTTP_200_OK
        publish_data = publish_response.json()
        
        package_name = publish_data["package"]["name"]
        
        # 3. Get user's packages
        user_packages_response = await client.get(f"/api/v1/users/{test_user.github_username}/packages")
        assert user_packages_response.status_code == status.HTTP_200_OK
        user_packages_data = user_packages_response.json()
        
        # Should include the new package
        package_names = [pkg["name"] for pkg in user_packages_data["packages"]]
        assert package_name in package_names
        assert user_packages_data["total_packages"] == initial_package_count + 1
        
        # 4. Get specific package details
        package_response = await client.get(f"/api/v1/packages/{package_name}")
        assert package_response.status_code == status.HTTP_200_OK
        package_data = package_response.json()
        
        assert package_data["package"]["name"] == package_name
        assert package_data["owner"]["github_username"] == test_user.github_username
    
    async def test_error_handling_workflow(self, client, auth_headers):
        """Test error handling across different endpoints."""
        
        # 1. Try to get non-existent package
        response = await client.get("/api/v1/packages/nonexistent-package-xyz")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
        
        # 2. Try to download non-existent package
        response = await client.get("/api/v1/packages/nonexistent/1.0.0/download")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # 3. Try to publish package with invalid type
        files = {"file": ("test.tar.gz", BytesIO(b"test content"), "application/gzip")}
        data = {"package_type": "invalid_type"}
        
        response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid package type" in response.json()["detail"].lower()
        
        # 4. Try to search with invalid parameters
        response = await client.get("/api/v1/search/?q=test&limit=1000")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # 5. Try to access protected endpoint without auth
        response = await client.post("/api/v1/packages/publish", files=files, data={"package_type": "tool"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # 6. Try to get non-existent user
        response = await client.get("/api/v1/users/nonexistentuser123xyz")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_concurrent_operations(self, client, db_session, test_user):
        """Test concurrent operations don't interfere with each other."""
        import asyncio
        
        # Create multiple packages concurrently
        async def create_package(i):
            from app.models.package import Package, PackageType
            package = Package(
                name=f"concurrent-package-{i}",
                normalized_name=f"concurrent-package-{i}",
                package_type=PackageType.TOOL,
                description=f"Concurrent test package {i}",
                owner_id=test_user.id,
            )
            db_session.add(package)
            return package
        
        # Create 5 packages concurrently
        tasks = [create_package(i) for i in range(5)]
        packages = await asyncio.gather(*tasks)
        
        await db_session.commit()
        
        # Search for all packages concurrently
        async def search_package(name):
            response = await client.get(f"/api/v1/search/?q={name}")
            return response
        
        search_tasks = [search_package(f"concurrent-package-{i}") for i in range(5)]
        responses = await asyncio.gather(*search_tasks)
        
        # All searches should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["results"]) >= 1
    
    async def test_health_and_monitoring_workflow(self, client):
        """Test health check and monitoring endpoints."""
        
        # 1. Basic health check
        health_response = await client.get("/health")
        assert health_response.status_code == status.HTTP_200_OK
        health_data = health_response.json()
        
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "agenthub-registry"
        
        # 2. Detailed health check
        detailed_health_response = await client.get("/api/v1/health/detailed")
        assert detailed_health_response.status_code == status.HTTP_200_OK
        detailed_health_data = detailed_health_response.json()
        
        assert "database" in detailed_health_data
        assert "redis" in detailed_health_data
        assert detailed_health_data["service"] == "agenthub-registry"
        
        # 3. Metrics endpoint
        metrics_response = await client.get("/metrics")
        assert metrics_response.status_code == status.HTTP_200_OK
        
        # Should return Prometheus format metrics
        metrics_text = metrics_response.text
        assert "http_requests_total" in metrics_text
    
    async def test_api_versioning_and_compatibility(self, client):
        """Test API versioning and backward compatibility."""
        
        # 1. Test root API endpoint
        api_response = await client.get("/api")
        assert api_response.status_code == status.HTTP_200_OK
        api_data = api_response.json()
        
        assert api_data["service"] == "AgentHub Registry"
        assert "version" in api_data
        assert "api_version" in api_data
        
        # 2. Test main application root
        root_response = await client.get("/")
        assert root_response.status_code == status.HTTP_200_OK
        # Should serve the web UI (HTML)
        assert "text/html" in root_response.headers.get("content-type", "")
    
    async def test_rate_limiting_workflow(self, client):
        """Test rate limiting doesn't interfere with normal operations."""
        
        # Make multiple requests rapidly
        responses = []
        for i in range(10):
            response = await client.get("/health")
            responses.append(response)
        
        # All should succeed (rate limit is high for tests)
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
    
    async def test_data_consistency_workflow(self, client, db_session, test_user, auth_headers, sample_package_file, mock_s3_service):
        """Test data consistency across operations."""
        
        # 1. Publish a package
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "tool"}
        
        publish_response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        assert publish_response.status_code == status.HTTP_200_OK
        publish_data = publish_response.json()
        
        package_name = publish_data["package"]["name"]
        version = publish_data["version"]["version"]
        
        # 2. Verify package appears in search
        search_response = await client.get(f"/api/v1/search/?q={package_name}")
        assert search_response.status_code == status.HTTP_200_OK
        search_data = search_response.json()
        
        found_packages = [pkg["name"] for pkg in search_data["results"]]
        assert package_name in found_packages
        
        # 3. Verify package appears in user's packages
        user_packages_response = await client.get(f"/api/v1/users/{test_user.github_username}/packages")
        assert user_packages_response.status_code == status.HTTP_200_OK
        user_packages_data = user_packages_response.json()
        
        user_package_names = [pkg["name"] for pkg in user_packages_data["packages"]]
        assert package_name in user_package_names
        
        # 4. Verify package details are consistent
        package_response = await client.get(f"/api/v1/packages/{package_name}")
        assert package_response.status_code == status.HTTP_200_OK
        package_data = package_response.json()
        
        assert package_data["package"]["name"] == package_name
        assert package_data["versions"][0]["version"] == version
        assert package_data["owner"]["github_username"] == test_user.github_username
        
        # 5. Verify stats are consistent
        stats_response = await client.get(f"/api/v1/packages/{package_name}/stats")
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        
        assert stats_data["package_name"] == package_name
        assert stats_data["version_count"] == 1 