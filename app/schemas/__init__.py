"""
Common schemas for the AgentHub Registry API.
"""

from .auth import *
from .package import *
from .user import *

# Common response models
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Basic health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: Optional[str] = Field(None, description="Service version")
    environment: Optional[str] = Field(None, description="Environment")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "agenthub-registry",
                "version": "1.0.0",
                "environment": "production"
            }
        }
    }


class ComponentHealth(BaseModel):
    """Component health status."""
    status: str = Field(..., description="Component health status")
    message: Optional[str] = Field(None, description="Health status message")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "message": "Database connection successful",
                "response_time_ms": 5.2
            }
        }
    }


class DetailedHealthCheck(BaseModel):
    """Detailed health check response."""
    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    checks: Dict[str, ComponentHealth] = Field(..., description="Individual component health checks")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "service": "agenthub-registry",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "message": "Database connection successful",
                        "response_time_ms": 5.2
                    },
                    "redis": {
                        "status": "healthy",
                        "message": "Redis connection successful",
                        "response_time_ms": 2.1
                    },
                    "storage": {
                        "status": "healthy",
                        "message": "S3 storage accessible",
                        "response_time_ms": 15.3
                    }
                }
            }
        }
    }


class ApiInfo(BaseModel):
    """API information response."""
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    api_version: str = Field(..., description="API version")
    description: Optional[str] = Field(None, description="Service description")
    docs_url: Optional[str] = Field(None, description="Documentation URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service": "AgentHub Registry",
                "version": "1.0.0",
                "api_version": "v1",
                "description": "Universal package registry for AI-native components",
                "docs_url": "/docs"
            }
        }
    } 