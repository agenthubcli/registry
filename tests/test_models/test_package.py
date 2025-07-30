"""
Tests for Package and PackageVersion models.
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.package import (
    Package, 
    PackageVersion, 
    PackageTag, 
    PackageDependency,
    PackageType, 
    PackageStatus, 
    VersionStatus
)
from app.models.user import User


@pytest.mark.models
@pytest.mark.asyncio
class TestPackageModel:
    """Test cases for Package model."""
    
    async def test_create_package_success(self, db_session, test_user):
        """Test creating a package successfully."""
        package = Package(
            name="test-package",
            normalized_name="test-package",
            description="A test package for unit testing",
            package_type=PackageType.TOOL,
            owner_id=test_user.id,
            homepage="https://github.com/testuser/test-package",
            repository="https://github.com/testuser/test-package",
            documentation="https://docs.test-package.dev",
            keywords=["test", "tool", "automation"],
        )
        
        db_session.add(package)
        await db_session.commit()
        await db_session.refresh(package)
        
        assert package.id is not None
        assert package.name == "test-package"
        assert package.normalized_name == "test-package"
        assert package.description == "A test package for unit testing"
        assert package.package_type == PackageType.TOOL
        assert package.status == PackageStatus.PUBLISHED  # Default
        assert package.owner_id == test_user.id
        assert package.is_private is False  # Default
        assert package.auto_publish is False  # Default
        assert package.total_downloads == 0  # Default
        assert package.version_count == 0  # Default
        assert package.keywords == ["test", "tool", "automation"]
        assert package.created_at is not None
        assert package.updated_at is not None
    
    async def test_package_name_unique_constraint(self, db_session, test_user):
        """Test that package name must be unique."""
        package1 = Package(
            name="duplicate-package",
            normalized_name="duplicate-package",
            package_type=PackageType.TOOL,
            owner_id=test_user.id,
        )
        
        package2 = Package(
            name="duplicate-package",  # Same name
            normalized_name="duplicate-package",
            package_type=PackageType.AGENT,
            owner_id=test_user.id,
        )
        
        db_session.add(package1)
        await db_session.commit()
        
        db_session.add(package2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_package_public_info_property(self, test_package):
        """Test public_info property returns expected data."""
        info = test_package.public_info
        
        assert isinstance(info, dict)
        assert info["id"] == test_package.id
        assert info["name"] == test_package.name
        assert info["description"] == test_package.description
        assert info["package_type"] == test_package.package_type.value
        assert info["latest_version"] == test_package.latest_version
        assert info["total_downloads"] == test_package.total_downloads
        assert info["download_count_last_30_days"] == test_package.download_count_last_30_days
        assert info["created_at"] == test_package.created_at
        assert info["updated_at"] == test_package.updated_at
        assert info["homepage"] == test_package.homepage
        assert info["repository"] == test_package.repository
        assert info["keywords"] == test_package.keywords
    
    async def test_package_owner_relationship(self, db_session, test_package, test_user):
        """Test package-owner relationship."""
        stmt = select(Package).options(selectinload(Package.owner)).where(Package.id == test_package.id)
        result = await db_session.execute(stmt)
        package = result.scalar_one()
        
        assert package.owner is not None
        assert package.owner.id == test_user.id
        assert package.owner.github_username == test_user.github_username
    
    async def test_package_versions_relationship(self, db_session, test_package, test_package_version):
        """Test package-versions relationship."""
        stmt = select(Package).options(selectinload(Package.versions)).where(Package.id == test_package.id)
        result = await db_session.execute(stmt)
        package = result.scalar_one()
        
        assert len(package.versions) == 1
        assert package.versions[0].id == test_package_version.id
        assert package.versions[0].version == "1.0.0"
    
    async def test_package_repr(self, test_package):
        """Test package string representation."""
        repr_str = repr(test_package)
        assert "Package(" in repr_str
        assert f"id={test_package.id}" in repr_str
        assert f"name='{test_package.name}'" in repr_str
        assert f"type='{test_package.package_type}'" in repr_str
    
    async def test_package_filter_by_type(self, db_session, test_user):
        """Test filtering packages by type."""
        # Create packages of different types
        agent_package = Package(
            name="agent-package",
            normalized_name="agent-package",
            package_type=PackageType.AGENT,
            owner_id=test_user.id,
        )
        
        tool_package = Package(
            name="tool-package",
            normalized_name="tool-package",
            package_type=PackageType.TOOL,
            owner_id=test_user.id,
        )
        
        db_session.add(agent_package)
        db_session.add(tool_package)
        await db_session.commit()
        
        # Query only tool packages
        stmt = select(Package).where(Package.package_type == PackageType.TOOL)
        result = await db_session.execute(stmt)
        tool_packages = result.scalars().all()
        
        package_names = [pkg.name for pkg in tool_packages]
        assert "tool-package" in package_names
        assert "agent-package" not in package_names
    
    async def test_package_filter_by_status(self, db_session, test_user):
        """Test filtering packages by status."""
        # Create packages with different statuses
        published_package = Package(
            name="published-package",
            normalized_name="published-package",
            package_type=PackageType.TOOL,
            status=PackageStatus.PUBLISHED,
            owner_id=test_user.id,
        )
        
        suspended_package = Package(
            name="suspended-package",
            normalized_name="suspended-package",
            package_type=PackageType.TOOL,
            status=PackageStatus.SUSPENDED,
            owner_id=test_user.id,
        )
        
        db_session.add(published_package)
        db_session.add(suspended_package)
        await db_session.commit()
        
        # Query only published packages
        stmt = select(Package).where(Package.status == PackageStatus.PUBLISHED)
        result = await db_session.execute(stmt)
        published_packages = result.scalars().all()
        
        package_names = [pkg.name for pkg in published_packages]
        assert "published-package" in package_names
        assert "suspended-package" not in package_names


@pytest.mark.models
@pytest.mark.asyncio
class TestPackageVersionModel:
    """Test cases for PackageVersion model."""
    
    async def test_create_package_version_success(self, db_session, test_package, test_user):
        """Test creating a package version successfully."""
        version = PackageVersion(
            package_id=test_package.id,
            version="2.0.0",
            description="Version 2.0.0 with new features",
            changelog="Added new features and bug fixes",
            filename="test-package-2.0.0.tar.gz",
            file_size=2048,
            file_hash_sha256="abcd1234567890abcd1234567890abcd1234567890abcd1234567890abcd1234",
            s3_key="packages/test-package/2.0.0/test-package-2.0.0.tar.gz",
            manifest={
                "name": "test-package",
                "version": "2.0.0",
                "type": "tool",
                "description": "Test package version 2.0.0",
            },
            runtime="python",
            python_version=">=3.8",
            published_by_id=test_user.id,
        )
        
        db_session.add(version)
        await db_session.commit()
        await db_session.refresh(version)
        
        assert version.id is not None
        assert version.package_id == test_package.id
        assert version.version == "2.0.0"
        assert version.description == "Version 2.0.0 with new features"
        assert version.changelog == "Added new features and bug fixes"
        assert version.filename == "test-package-2.0.0.tar.gz"
        assert version.file_size == 2048
        assert version.file_hash_sha256 == "abcd1234567890abcd1234567890abcd1234567890abcd1234567890abcd1234"
        assert version.runtime == "python"
        assert version.python_version == ">=3.8"
        assert version.status == VersionStatus.DRAFT  # Default
        assert version.is_prerelease is False  # Default
        assert version.download_count == 0  # Default
        assert version.is_validated is False  # Default
        assert version.virus_scan_status == "pending"  # Default
        assert version.published_by_id == test_user.id
        assert version.created_at is not None
        assert version.updated_at is not None
    
    async def test_package_version_unique_constraint(self, db_session, test_package, test_user):
        """Test that package_id + version must be unique."""
        version1 = PackageVersion(
            package_id=test_package.id,
            version="1.0.0",
            filename="test-1.tar.gz",
            file_size=1024,
            file_hash_sha256="hash1",
            s3_key="packages/test/1.0.0/test-1.tar.gz",
            manifest={"name": "test", "version": "1.0.0"},
            published_by_id=test_user.id,
        )
        
        version2 = PackageVersion(
            package_id=test_package.id,
            version="1.0.0",  # Same version for same package
            filename="test-2.tar.gz",
            file_size=2048,
            file_hash_sha256="hash2",
            s3_key="packages/test/1.0.0/test-2.tar.gz",
            manifest={"name": "test", "version": "1.0.0"},
            published_by_id=test_user.id,
        )
        
        db_session.add(version1)
        await db_session.commit()
        
        db_session.add(version2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_package_version_download_url_property(self, test_package_version):
        """Test download_url property."""
        download_url = test_package_version.download_url
        
        assert isinstance(download_url, str)
        assert test_package_version.s3_key in download_url
        assert download_url.startswith("https://")
    
    async def test_package_version_public_info_property(self, test_package_version):
        """Test public_info property returns expected data."""
        info = test_package_version.public_info
        
        assert isinstance(info, dict)
        assert info["id"] == test_package_version.id
        assert info["version"] == test_package_version.version
        assert info["description"] == test_package_version.description
        assert info["download_count"] == test_package_version.download_count
        assert info["file_size"] == test_package_version.file_size
        assert info["file_hash_sha256"] == test_package_version.file_hash_sha256
        assert info["is_prerelease"] == test_package_version.is_prerelease
        assert info["runtime"] == test_package_version.runtime
        assert info["python_version"] == test_package_version.python_version
        assert info["published_at"] == test_package_version.published_at
        assert info["created_at"] == test_package_version.created_at
        assert info["download_url"] == test_package_version.download_url
        assert info["manifest"] == test_package_version.manifest
    
    async def test_package_version_package_relationship(self, db_session, test_package_version, test_package):
        """Test version-package relationship."""
        stmt = select(PackageVersion).options(selectinload(PackageVersion.package)).where(
            PackageVersion.id == test_package_version.id
        )
        result = await db_session.execute(stmt)
        version = result.scalar_one()
        
        assert version.package is not None
        assert version.package.id == test_package.id
        assert version.package.name == test_package.name
    
    async def test_package_version_published_by_relationship(self, db_session, test_package_version, test_user):
        """Test version-published_by relationship."""
        stmt = select(PackageVersion).options(selectinload(PackageVersion.published_by)).where(
            PackageVersion.id == test_package_version.id
        )
        result = await db_session.execute(stmt)
        version = result.scalar_one()
        
        assert version.published_by is not None
        assert version.published_by.id == test_user.id
        assert version.published_by.github_username == test_user.github_username
    
    async def test_package_version_repr(self, test_package_version):
        """Test package version string representation."""
        repr_str = repr(test_package_version)
        assert "PackageVersion(" in repr_str
        assert f"id={test_package_version.id}" in repr_str
        assert f"package_id={test_package_version.package_id}" in repr_str
        assert f"version='{test_package_version.version}'" in repr_str
    
    async def test_package_version_filter_by_status(self, db_session, test_package, test_user):
        """Test filtering versions by status."""
        # Create versions with different statuses
        published_version = PackageVersion(
            package_id=test_package.id,
            version="1.0.0",
            status=VersionStatus.PUBLISHED,
            filename="test-1.0.0.tar.gz",
            file_size=1024,
            file_hash_sha256="hash1",
            s3_key="packages/test/1.0.0/test-1.0.0.tar.gz",
            manifest={"name": "test", "version": "1.0.0"},
            published_by_id=test_user.id,
        )
        
        draft_version = PackageVersion(
            package_id=test_package.id,
            version="2.0.0",
            status=VersionStatus.DRAFT,
            filename="test-2.0.0.tar.gz",
            file_size=2048,
            file_hash_sha256="hash2",
            s3_key="packages/test/2.0.0/test-2.0.0.tar.gz",
            manifest={"name": "test", "version": "2.0.0"},
            published_by_id=test_user.id,
        )
        
        db_session.add(published_version)
        db_session.add(draft_version)
        await db_session.commit()
        
        # Query only published versions
        stmt = select(PackageVersion).where(
            PackageVersion.package_id == test_package.id,
            PackageVersion.status == VersionStatus.PUBLISHED
        )
        result = await db_session.execute(stmt)
        published_versions = result.scalars().all()
        
        versions = [v.version for v in published_versions]
        assert "1.0.0" in versions
        assert "2.0.0" not in versions


@pytest.mark.models
@pytest.mark.asyncio
class TestPackageTagModel:
    """Test cases for PackageTag model."""
    
    async def test_create_package_tag_success(self, db_session, test_package):
        """Test creating a package tag successfully."""
        tag = PackageTag(
            package_id=test_package.id,
            tag="machine-learning",
        )
        
        db_session.add(tag)
        await db_session.commit()
        await db_session.refresh(tag)
        
        assert tag.id is not None
        assert tag.package_id == test_package.id
        assert tag.tag == "machine-learning"
        assert tag.created_at is not None
    
    async def test_package_tag_unique_constraint(self, db_session, test_package):
        """Test that package_id + tag must be unique."""
        tag1 = PackageTag(
            package_id=test_package.id,
            tag="automation",
        )
        
        tag2 = PackageTag(
            package_id=test_package.id,
            tag="automation",  # Same tag for same package
        )
        
        db_session.add(tag1)
        await db_session.commit()
        
        db_session.add(tag2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_package_tags_relationship(self, db_session, test_package):
        """Test package-tags relationship."""
        # Create multiple tags for the package
        tag1 = PackageTag(package_id=test_package.id, tag="ai")
        tag2 = PackageTag(package_id=test_package.id, tag="automation")
        tag3 = PackageTag(package_id=test_package.id, tag="tool")
        
        db_session.add_all([tag1, tag2, tag3])
        await db_session.commit()
        
        # Load package with tags
        stmt = select(Package).options(selectinload(Package.tags)).where(Package.id == test_package.id)
        result = await db_session.execute(stmt)
        package = result.scalar_one()
        
        assert len(package.tags) == 3
        tag_names = [tag.tag for tag in package.tags]
        assert "ai" in tag_names
        assert "automation" in tag_names
        assert "tool" in tag_names
    
    async def test_package_tag_repr(self, db_session, test_package):
        """Test package tag string representation."""
        tag = PackageTag(package_id=test_package.id, tag="test-tag")
        db_session.add(tag)
        await db_session.commit()
        await db_session.refresh(tag)
        
        repr_str = repr(tag)
        assert "PackageTag(" in repr_str
        assert f"package_id={tag.package_id}" in repr_str
        assert f"tag='{tag.tag}'" in repr_str


@pytest.mark.models
@pytest.mark.asyncio
class TestPackageDependencyModel:
    """Test cases for PackageDependency model."""
    
    async def test_create_package_dependency_success(self, db_session, test_package_version):
        """Test creating a package dependency successfully."""
        dependency = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="pandas-tool",
            version_spec="^2.0.0",
            dependency_type="runtime",
            description="Data manipulation library",
        )
        
        db_session.add(dependency)
        await db_session.commit()
        await db_session.refresh(dependency)
        
        assert dependency.id is not None
        assert dependency.version_id == test_package_version.id
        assert dependency.dependency_name == "pandas-tool"
        assert dependency.version_spec == "^2.0.0"
        assert dependency.dependency_type == "runtime"
        assert dependency.description == "Data manipulation library"
        assert dependency.created_at is not None
    
    async def test_package_dependency_unique_constraint(self, db_session, test_package_version):
        """Test that version_id + dependency_name must be unique."""
        dep1 = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="numpy-tool",
            version_spec="^1.0.0",
        )
        
        dep2 = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="numpy-tool",  # Same dependency for same version
            version_spec="^2.0.0",
        )
        
        db_session.add(dep1)
        await db_session.commit()
        
        db_session.add(dep2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_package_version_dependencies_relationship(self, db_session, test_package_version):
        """Test version-dependencies relationship."""
        # Create multiple dependencies for the version
        dep1 = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="pandas-tool",
            version_spec="^2.0.0",
            dependency_type="runtime"
        )
        dep2 = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="pytest-helper",
            version_spec="^7.0.0",
            dependency_type="dev"
        )
        
        db_session.add_all([dep1, dep2])
        await db_session.commit()
        
        # Load version with dependencies
        stmt = select(PackageVersion).options(selectinload(PackageVersion.dependencies)).where(
            PackageVersion.id == test_package_version.id
        )
        result = await db_session.execute(stmt)
        version = result.scalar_one()
        
        assert len(version.dependencies) == 2
        dep_names = [dep.dependency_name for dep in version.dependencies]
        assert "pandas-tool" in dep_names
        assert "pytest-helper" in dep_names
    
    async def test_package_dependency_default_values(self, db_session, test_package_version):
        """Test dependency model default values."""
        dependency = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="test-dependency",
            version_spec=">=1.0.0",
        )
        
        db_session.add(dependency)
        await db_session.commit()
        await db_session.refresh(dependency)
        
        assert dependency.dependency_type == "runtime"  # Default value
        assert dependency.description is None
    
    async def test_package_dependency_repr(self, db_session, test_package_version):
        """Test package dependency string representation."""
        dependency = PackageDependency(
            version_id=test_package_version.id,
            dependency_name="test-dep",
            version_spec="^1.0.0",
        )
        db_session.add(dependency)
        await db_session.commit()
        await db_session.refresh(dependency)
        
        repr_str = repr(dependency)
        assert "PackageDependency(" in repr_str
        assert f"version_id={dependency.version_id}" in repr_str
        assert f"dependency='{dependency.dependency_name}'" in repr_str
        assert f"spec='{dependency.version_spec}'" in repr_str 