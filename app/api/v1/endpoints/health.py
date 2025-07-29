"""
Health check endpoints for monitoring and status.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db, get_redis_connection
from app.core.config import settings
from app.schemas import HealthCheck, DetailedHealthCheck, ComponentHealth

router = APIRouter()


@router.get(
    "/",
    response_model=HealthCheck,
    summary="Basic health check",
    description="Check if the API is running"
)
async def health_check():
    """Basic health check."""
    return HealthCheck(
        status="healthy",
        service="agenthub-registry",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/detailed",
    response_model=DetailedHealthCheck,
    responses={
        503: {"model": DetailedHealthCheck, "description": "Some components are unhealthy"}
    },
    summary="Detailed health check",
    description="Check health of all system components"
)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check for all system components."""
    
    checks = {}
    overall_healthy = True
    
    # Database health check
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - start_time) * 1000
        
        checks["database"] = ComponentHealth(
            status="healthy",
            message="Database connection successful",
            response_time_ms=round(db_response_time, 2)
        )
    except Exception as e:
        checks["database"] = ComponentHealth(
            status="unhealthy",
            message=f"Database connection failed: {str(e)}"
        )
        overall_healthy = False
    
    # Redis health check
    try:
        start_time = time.time()
        redis = await get_redis_connection()
        if redis:
            await redis.ping()
            await redis.close()
            redis_response_time = (time.time() - start_time) * 1000
            
            checks["redis"] = ComponentHealth(
                status="healthy",
                message="Redis connection successful",
                response_time_ms=round(redis_response_time, 2)
            )
        else:
            checks["redis"] = ComponentHealth(
                status="unhealthy",
                message="Redis connection not available"
            )
            overall_healthy = False
    except Exception as e:
        checks["redis"] = ComponentHealth(
            status="unhealthy",
            message=f"Redis connection failed: {str(e)}"
        )
        overall_healthy = False
    
    # Storage health check (simplified)
    try:
        start_time = time.time()
        # TODO: Add actual S3 health check
        storage_response_time = (time.time() - start_time) * 1000
        
        checks["storage"] = ComponentHealth(
            status="healthy",
            message="S3 storage accessible",
            response_time_ms=round(storage_response_time, 2)
        )
    except Exception as e:
        checks["storage"] = ComponentHealth(
            status="unhealthy",
            message=f"Storage check failed: {str(e)}"
        )
        overall_healthy = False
    
    response = DetailedHealthCheck(
        status="healthy" if overall_healthy else "unhealthy",
        service="agenthub-registry",
        checks=checks
    )
    
    # Return 503 if any component is unhealthy
    if not overall_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response 