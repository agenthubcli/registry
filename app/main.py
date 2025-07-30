"""
Main FastAPI application for AgentHub Registry.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, generate_latest
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.openapi.utils import get_openapi

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import create_tables, get_redis_connection
from app.core.logging import setup_logging
from app.middleware.security import SecurityHeadersMiddleware
from app.schemas import HealthCheck, ApiInfo

# Metrics
request_count = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
request_duration = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting AgentHub Registry...")
    
    # Initialize database
    await create_tables()
    
    # Test Redis connection
    redis = await get_redis_connection()
    if redis:
        await redis.close()
        logger.info("Redis connection established")
    
    logger.info("AgentHub Registry started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AgentHub Registry...")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Setup logging
    setup_logging()
    
    # Setup Sentry for error tracking
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(auto_enable=True),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
            release=f"agenthub-registry@{settings.VERSION}",
        )
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        contact={
            "name": "AgentHub Team",
            "url": "https://github.com/agenthubcli/registry",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "https://registry.agenthubcli.com",
                "description": "Production server"
            },
            {
                "url": "http://localhost:8000", 
                "description": "Development server"
            }
        ],
        # OpenAPI security configuration
        openapi_tags=[
            {
                "name": "authentication",
                "description": "GitHub OAuth and JWT token management"
            },
            {
                "name": "packages", 
                "description": "Package publishing, management, and downloads"
            },
            {
                "name": "search",
                "description": "Package discovery and search functionality"
            },
            {
                "name": "users",
                "description": "User profiles and package ownership"
            },
            {
                "name": "health",
                "description": "Service health and monitoring"
            }
        ]
    )
    
    # Configure OpenAPI security schemes
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained via GitHub OAuth"
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
    
    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging and metrics middleware
    @app.middleware("http")
    async def add_process_time_and_logging(request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            client_ip=get_remote_address(request),
        )
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Update metrics
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(process_time)
        
        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time,
            client_ip=get_remote_address(request),
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # Health check endpoint
    @app.get("/health", response_model=HealthCheck, tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return HealthCheck(
            status="healthy", 
            service="agenthub-registry",
            version=settings.VERSION,
            environment=settings.ENVIRONMENT
        )
    
    # Metrics endpoint
    @app.get("/metrics", tags=["monitoring"])
    async def metrics():
        """Prometheus metrics endpoint."""
        return generate_latest()
    
    # Root endpoint - serve web UI
    @app.get("/", include_in_schema=False)
    async def root():
        """Serve the web UI."""
        from fastapi.responses import FileResponse
        return FileResponse("static/index.html")
    
    # API info endpoint
    @app.get("/api", response_model=ApiInfo, tags=["root"])
    async def api_info():
        """API information."""
        return ApiInfo(
            service=settings.PROJECT_NAME,
            version=settings.VERSION,
            description=settings.PROJECT_DESCRIPTION,
            api_version="v1",
            docs_url="/docs" if settings.ENABLE_DOCS else None
        )
    
    return app


# Create the application instance
app = create_application()


# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        url=str(request.url),
        method=request.method,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    ) 