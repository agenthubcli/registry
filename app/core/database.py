"""
Database connection and session management for AgentHub Registry.
"""

from redis import asyncio as aioredis
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create async engine
async_engine = create_async_engine(
    settings.database_url_async,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()

# Redis connection
redis_pool = None


async def get_redis_connection():
    """Get Redis connection from pool."""
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
        )
    return redis_pool


async def get_db():
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    # Import all models to ensure they are registered
    from app.models import user, package, download_stats  # noqa
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db_connections():
    """Close all database connections."""
    await async_engine.dispose()
    if redis_pool:
        await redis_pool.close() 