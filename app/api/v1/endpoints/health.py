"""
Health check endpoints for monitoring and status.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db, get_redis_connection
from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "agenthub-registry",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check including database and Redis."""
    status = {"service": "agenthub-registry", "version": settings.VERSION}
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        status["database"] = "healthy"
    except Exception as e:
        status["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis = await get_redis_connection()
        await redis.ping()
        status["redis"] = "healthy"
    except Exception as e:
        status["redis"] = f"unhealthy: {str(e)}"
    
    # Overall status
    status["status"] = "healthy" if all(
        v == "healthy" for k, v in status.items() 
        if k in ["database", "redis"]
    ) else "unhealthy"
    
    return status 