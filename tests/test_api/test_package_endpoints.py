"""
Tests for package management API endpoints.
"""

import pytest
from io import BytesIO
from fastapi import status
from unittest.mock import patch

from app.models.package import PackageType, VersionStatus


@pytest.mark.api
@pytest.mark.asyncio
class TestPackageEndpoints:
    """Test cases for package endpoints."""
    
    async def test_get_package_success(self, client, test_package, test_package_version, test_user):
        """Test getting package details successfully."""
        response = await client.get(f"/api/v1/packages/{test_package.name}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package"]["id"] == test_package.id
        assert data["package"]["name"] == test_package.name
        assert data["package"]["description"] == test_package.description
        assert data["package"]["package_type"] == test_package.package_type.value
        
        assert data["owner"]["id"] == test_user.id
        assert data["owner"]["github_username"] == test_user.github_username
        
        assert len(data["versions"]) == 1
        assert data["versions"][0]["version"] == test_package_version.version
        
        assert data["latest_version"]["version"] == test_package_version.version
    
    async def test_get_package_not_found(self, client):
        """Test getting non-existent package."""
        response = await client.get("/api/v1/packages/nonexistent-package")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Package not found"
    
    async def test_get_package_versions_success(self, client, test_package, test_package_version):
        """Test getting package versions successfully."""
        response = await client.get(f"/api/v1/packages/{test_package.name}/versions")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package_name"] == test_package.name
        assert len(data["versions"]) == 1
        assert data["versions"][0]["version"] == test_package_version.version
        assert data["versions"][0]["download_count"] == test_package_version.download_count
    
    async def test_get_package_versions_not_found(self, client):
        """Test getting versions for non-existent package."""
        response = await client.get("/api/v1/packages/nonexistent/versions")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Package not found"
    
    async def test_get_package_version_success(self, client, test_package, test_package_version, test_user):
        """Test getting specific package version successfully."""
        response = await client.get(f"/api/v1/packages/{test_package.name}/{test_package_version.version}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package"]["id"] == test_package.id
        assert data["package"]["name"] == test_package.name
        
        assert data["version"]["version"] == test_package_version.version
        assert data["version"]["download_count"] == test_package_version.download_count
        assert data["version"]["file_size"] == test_package_version.file_size
        
        assert data["owner"]["id"] == test_user.id
    
    async def test_get_package_version_not_found(self, client, test_package):
        """Test getting non-existent package version."""
        response = await client.get(f"/api/v1/packages/{test_package.name}/99.99.99")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Package version not found"
    
    async def test_download_package_success(self, client, test_package, test_package_version, mock_s3_service):
        """Test downloading package successfully."""
        response = await client.get(f"/api/v1/packages/{test_package.name}/{test_package_version.version}/download")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"] == f"attachment; filename={test_package_version.filename}"
        assert response.headers["content-length"] == str(test_package_version.file_size)
        assert response.headers["x-package-name"] == test_package.name
        assert response.headers["x-package-version"] == test_package_version.version
        
        # Verify S3 service was called
        mock_s3_service.download_package.assert_called_once_with(test_package_version.s3_key)
    
    async def test_download_package_not_found(self, client):
        """Test downloading non-existent package."""
        response = await client.get("/api/v1/packages/nonexistent/1.0.0/download")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_download_package_file_not_found(self, client, test_package, test_package_version, mock_s3_service):
        """Test downloading package when file not found in S3."""
        # Mock S3 service to raise FileNotFoundError
        mock_s3_service.download_package.side_effect = FileNotFoundError("File not found")
        
        response = await client.get(f"/api/v1/packages/{test_package.name}/{test_package_version.version}/download")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Package file not found"
    
    async def test_publish_package_success(self, client, auth_headers, sample_package_file, mock_s3_service):
        """Test publishing a new package successfully."""
        # Create form data
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "tool"}
        
        response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        
        assert response_data["message"] == "Package published successfully"
        assert "package" in response_data
        assert "version" in response_data
        assert response_data["package"]["package_type"] == "tool"
        
        # Verify S3 service was called
        mock_s3_service.upload_package.assert_called_once()
    
    async def test_publish_package_unauthorized(self, client, sample_package_file):
        """Test publishing package without authentication."""
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "tool"}
        
        response = await client.post("/api/v1/packages/publish", files=files, data=data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert response_data["detail"] == "Not authenticated"
    
    async def test_publish_package_user_cannot_publish(self, client, db_session, sample_package_file):
        """Test publishing package with user who cannot publish."""
        from app.models.user import User
        from app.services.auth import auth_service
        
        # Create user who cannot publish
        user = User(
            github_id=99999,
            github_username="nopublishuser",
            is_verified=False,  # Not verified, so cannot publish
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        token = auth_service.create_access_token(user.id)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "tool"}
        
        response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_data = response.json()
        assert response_data["detail"] == "User not authorized to publish packages"
    
    async def test_publish_package_invalid_type(self, client, auth_headers, sample_package_file):
        """Test publishing package with invalid package type."""
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": "invalid_type"}
        
        response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "Invalid package type" in response_data["detail"]
    
    async def test_publish_package_too_large(self, client, auth_headers):
        """Test publishing package that exceeds size limit."""
        # Create large file content (11MB when limit is 10MB for tests)
        large_content = b"x" * (11 * 1024 * 1024)
        
        files = {"file": ("large-package.tar.gz", BytesIO(large_content), "application/gzip")}
        data = {"package_type": "tool"}
        
        response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        response_data = response.json()
        assert "Package size exceeds maximum" in response_data["detail"]
    
    async def test_publish_package_duplicate_version(self, client, auth_headers, test_package, test_user, sample_package_file):
        """Test publishing duplicate version of existing package."""
        # Set up test package to be owned by the test user
        test_package.owner_id = test_user.id
        
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": test_package.package_type.value}
        
        # Mock manifest extraction to return existing package name and version
        with patch('app.api.v1.endpoints.packages.extract_manifest') as mock_extract:
            mock_extract.return_value = {
                "name": test_package.name,
                "version": "1.0.0",  # Same as test_package_version
                "type": test_package.package_type.value,
            }
            
            response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        response_data = response.json()
        assert "already exists" in response_data["detail"]
    
    async def test_publish_package_not_owner(self, client, auth_headers, test_package, sample_package_file):
        """Test publishing to package owned by another user."""
        files = {"file": (sample_package_file["filename"], BytesIO(sample_package_file["content"]), sample_package_file["content_type"])}
        data = {"package_type": test_package.package_type.value}
        
        # Mock manifest extraction to return existing package name
        with patch('app.api.v1.endpoints.packages.extract_manifest') as mock_extract:
            mock_extract.return_value = {
                "name": test_package.name,
                "version": "2.0.0",  # Different version
                "type": test_package.package_type.value,
            }
            
            response = await client.post("/api/v1/packages/publish", files=files, data=data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_data = response.json()
        assert "don't have permission" in response_data["detail"]
    
    async def test_delete_package_success(self, client, auth_headers, test_package, test_user):
        """Test deleting package successfully."""
        # Set up test package to be owned by the test user
        test_package.owner_id = test_user.id
        
        with patch('app.core.config.settings.ENABLE_PACKAGE_DELETION', True):
            response = await client.delete(f"/api/v1/packages/{test_package.name}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["message"] == "Package deleted successfully"
    
    async def test_delete_package_disabled(self, client, auth_headers, test_package):
        """Test deleting package when deletion is disabled."""
        with patch('app.core.config.settings.ENABLE_PACKAGE_DELETION', False):
            response = await client.delete(f"/api/v1/packages/{test_package.name}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_data = response.json()
        assert response_data["detail"] == "Package deletion is not enabled"
    
    async def test_delete_package_unauthorized(self, client, test_package):
        """Test deleting package without authentication."""
        response = await client.delete(f"/api/v1/packages/{test_package.name}")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    async def test_delete_package_not_owner(self, client, auth_headers, test_package):
        """Test deleting package not owned by user."""
        with patch('app.core.config.settings.ENABLE_PACKAGE_DELETION', True):
            response = await client.delete(f"/api/v1/packages/{test_package.name}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        response_data = response.json()
        assert "don't have permission" in response_data["detail"]
    
    async def test_delete_package_admin(self, client, admin_auth_headers, test_package):
        """Test admin can delete any package."""
        with patch('app.core.config.settings.ENABLE_PACKAGE_DELETION', True):
            response = await client.delete(f"/api/v1/packages/{test_package.name}", headers=admin_auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
    
    async def test_delete_package_not_found(self, client, auth_headers):
        """Test deleting non-existent package."""
        with patch('app.core.config.settings.ENABLE_PACKAGE_DELETION', True):
            response = await client.delete("/api/v1/packages/nonexistent", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_package_stats_success(self, client, test_package):
        """Test getting package statistics successfully."""
        response = await client.get(f"/api/v1/packages/{test_package.name}/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["package_name"] == test_package.name
        assert data["total_downloads"] == test_package.total_downloads
        assert data["downloads_last_30_days"] == test_package.download_count_last_30_days
        assert data["version_count"] == test_package.version_count
    
    async def test_get_package_stats_not_found(self, client):
        """Test getting stats for non-existent package."""
        response = await client.get("/api/v1/packages/nonexistent/stats")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_package_name_validation(self, client):
        """Test package name validation in URLs."""
        invalid_names = [
            "",  # Empty
            "a" * 300,  # Too long
            "invalid/name",  # Contains slash
            "invalid name",  # Contains space
        ]
        
        for name in invalid_names:
            response = await client.get(f"/api/v1/packages/{name}")
            # Should either be 404 (not found) or 422 (validation error)
            assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    async def test_version_string_validation(self, client, test_package):
        """Test version string validation in URLs."""
        invalid_versions = [
            "",  # Empty
            "v" * 100,  # Too long
            "invalid version",  # Contains space
            "../../../etc/passwd",  # Path traversal attempt
        ]
        
        for version in invalid_versions:
            response = await client.get(f"/api/v1/packages/{test_package.name}/{version}")
            # Should either be 404 (not found) or 422 (validation error)
            assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY] 