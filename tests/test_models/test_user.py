"""
Tests for User model.
"""

import pytest
from datetime import datetime
from sqlalchemy import select

from app.models.user import User


@pytest.mark.models
@pytest.mark.asyncio
class TestUserModel:
    """Test cases for User model."""
    
    async def test_create_user_success(self, db_session):
        """Test creating a user successfully."""
        user = User(
            github_id=12345,
            github_username="testuser",
            github_email="test@example.com",
            github_avatar_url="https://github.com/avatars/testuser",
            display_name="Test User",
            bio="Test bio",
            website="https://testuser.dev",
            location="Test City",
            company="Test Company",
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.github_id == 12345
        assert user.github_username == "testuser"
        assert user.github_email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.is_verified is False
        assert user.can_publish is True
        assert user.total_packages == 0
        assert user.total_downloads == 0
        assert user.created_at is not None
        assert user.updated_at is not None
    
    async def test_user_github_id_unique_constraint(self, db_session):
        """Test that github_id must be unique."""
        user1 = User(
            github_id=12345,
            github_username="testuser1",
            github_email="test1@example.com",
        )
        
        user2 = User(
            github_id=12345,  # Same github_id
            github_username="testuser2",
            github_email="test2@example.com",
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_user_github_username_unique_constraint(self, db_session):
        """Test that github_username must be unique."""
        user1 = User(
            github_id=12345,
            github_username="testuser",
            github_email="test1@example.com",
        )
        
        user2 = User(
            github_id=67890,
            github_username="testuser",  # Same username
            github_email="test2@example.com",
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_user_github_email_unique_constraint(self, db_session):
        """Test that github_email must be unique when not null."""
        user1 = User(
            github_id=12345,
            github_username="testuser1",
            github_email="test@example.com",
        )
        
        user2 = User(
            github_id=67890,
            github_username="testuser2",
            github_email="test@example.com",  # Same email
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            await db_session.commit()
    
    async def test_user_public_profile_property(self, test_user):
        """Test public_profile property returns expected data."""
        profile = test_user.public_profile
        
        assert isinstance(profile, dict)
        assert profile["id"] == test_user.id
        assert profile["github_username"] == test_user.github_username
        assert profile["display_name"] == test_user.display_name
        assert profile["github_avatar_url"] == test_user.github_avatar_url
        assert profile["bio"] == test_user.bio
        assert profile["website"] == test_user.website
        assert profile["location"] == test_user.location
        assert profile["company"] == test_user.company
        assert profile["total_packages"] == test_user.total_packages
        assert profile["total_downloads"] == test_user.total_downloads
        assert profile["created_at"] == test_user.created_at
        
        # Check that private fields are not included
        assert "github_access_token" not in profile
        assert "github_refresh_token" not in profile
        assert "github_id" not in profile
    
    async def test_can_publish_package_method(self, db_session):
        """Test can_publish_package method logic."""
        # Active, verified user with publish permission
        user1 = User(
            github_id=1,
            github_username="user1",
            is_active=True,
            is_verified=True,
            can_publish=True,
        )
        
        # Inactive user
        user2 = User(
            github_id=2,
            github_username="user2",
            is_active=False,
            is_verified=True,
            can_publish=True,
        )
        
        # Unverified user
        user3 = User(
            github_id=3,
            github_username="user3",
            is_active=True,
            is_verified=False,
            can_publish=True,
        )
        
        # User without publish permission
        user4 = User(
            github_id=4,
            github_username="user4",
            is_active=True,
            is_verified=True,
            can_publish=False,
        )
        
        assert user1.can_publish_package() is True
        assert user2.can_publish_package() is False
        assert user3.can_publish_package() is False
        assert user4.can_publish_package() is False
    
    async def test_user_repr(self, test_user):
        """Test user string representation."""
        repr_str = repr(test_user)
        assert "User(" in repr_str
        assert f"id={test_user.id}" in repr_str
        assert f"github_username='{test_user.github_username}'" in repr_str
    
    async def test_user_default_values(self, db_session):
        """Test user model default values."""
        user = User(
            github_id=12345,
            github_username="testuser",
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Test default values
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.is_verified is False
        assert user.can_publish is True
        assert user.max_package_size_mb == 100
        assert user.total_packages == 0
        assert user.total_downloads == 0
        assert user.github_email is None
        assert user.github_avatar_url is None
        assert user.display_name is None
        assert user.bio is None
        assert user.website is None
        assert user.location is None
        assert user.company is None
    
    async def test_user_timestamps(self, db_session):
        """Test user timestamp fields."""
        user = User(
            github_id=12345,
            github_username="testuser",
        )
        
        # Before adding to session
        assert user.created_at is None
        assert user.updated_at is None
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # After commit
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        
        original_updated_at = user.updated_at
        
        # Update user
        user.display_name = "Updated Name"
        await db_session.commit()
        await db_session.refresh(user)
        
        # updated_at should change
        assert user.updated_at > original_updated_at
        # created_at should not change
        assert user.created_at is not None
    
    async def test_user_last_login_at(self, db_session):
        """Test last_login_at field functionality."""
        user = User(
            github_id=12345,
            github_username="testuser",
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Initially null
        assert user.last_login_at is None
        
        # Set login time
        login_time = datetime.utcnow()
        user.last_login_at = login_time
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)
    
    async def test_user_query_by_github_username(self, db_session, test_user):
        """Test querying user by github_username."""
        stmt = select(User).where(User.github_username == test_user.github_username)
        result = await db_session.execute(stmt)
        found_user = result.scalar_one_or_none()
        
        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.github_username == test_user.github_username
    
    async def test_user_query_by_github_id(self, db_session, test_user):
        """Test querying user by github_id."""
        stmt = select(User).where(User.github_id == test_user.github_id)
        result = await db_session.execute(stmt)
        found_user = result.scalar_one_or_none()
        
        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.github_id == test_user.github_id
    
    async def test_user_active_filter(self, db_session):
        """Test filtering users by active status."""
        # Create active user
        active_user = User(
            github_id=1,
            github_username="activeuser",
            is_active=True,
        )
        
        # Create inactive user
        inactive_user = User(
            github_id=2,
            github_username="inactiveuser",
            is_active=False,
        )
        
        db_session.add(active_user)
        db_session.add(inactive_user)
        await db_session.commit()
        
        # Query only active users
        stmt = select(User).where(User.is_active == True)
        result = await db_session.execute(stmt)
        active_users = result.scalars().all()
        
        usernames = [user.github_username for user in active_users]
        assert "activeuser" in usernames
        assert "inactiveuser" not in usernames
    
    async def test_user_superuser_filter(self, db_session):
        """Test filtering users by superuser status."""
        # Create regular user
        regular_user = User(
            github_id=1,
            github_username="regularuser",
            is_superuser=False,
        )
        
        # Create superuser
        super_user = User(
            github_id=2,
            github_username="superuser",
            is_superuser=True,
        )
        
        db_session.add(regular_user)
        db_session.add(super_user)
        await db_session.commit()
        
        # Query only superusers
        stmt = select(User).where(User.is_superuser == True)
        result = await db_session.execute(stmt)
        superusers = result.scalars().all()
        
        usernames = [user.github_username for user in superusers]
        assert "superuser" in usernames
        assert "regularuser" not in usernames 