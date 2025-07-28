"""
Main API v1 router for AgentHub Registry.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, packages, search, users, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(packages.router, prefix="/packages", tags=["packages"])
api_router.include_router(search.router, prefix="/search", tags=["search"]) 