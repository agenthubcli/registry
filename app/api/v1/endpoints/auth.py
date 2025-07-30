"""
Authentication endpoints for GitHub OAuth and JWT management.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.auth import auth_service
from app.schemas.auth import OAuthUrl, AuthSuccess, RefreshRequest, TokenResponse
from app.schemas.user import UserProfile
from app.schemas.package import ErrorResponse, MessageResponse

router = APIRouter()


@router.get(
    "/github",
    response_model=OAuthUrl,
    summary="Initiate GitHub OAuth",
    description="Get GitHub OAuth authorization URL to start login process"
)
async def github_oauth_initiate(
    redirect_to: Optional[str] = Query(None, description="URL to redirect to after successful authentication")
):
    """Initiate GitHub OAuth flow."""
    
    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Build GitHub OAuth URL
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
        "scope": "user:email",
        "state": state,
    }
    
    if redirect_to:
        # Store redirect_to in state or session for later use
        params["state"] = f"{state}:{redirect_to}"
    
    oauth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    
    return OAuthUrl(oauth_url=oauth_url)


@router.get(
    "/github/callback", 
    response_model=AuthSuccess,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid authorization code or OAuth error"}
    },
    summary="GitHub OAuth callback",
    description="Handle GitHub OAuth callback and issue JWT tokens"
)
async def github_oauth_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: Optional[str] = Query(None, description="State parameter to prevent CSRF attacks"),
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    
    try:
        # Exchange code for access token and get user info
        github_user = await auth_service.exchange_code_for_user(code)
        
        # Create or update user in database
        user_stmt = select(User).where(User.github_id == github_user["id"])
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                github_id=github_user["id"],
                github_username=github_user["login"],
                github_email=github_user.get("email"),
                github_avatar_url=github_user.get("avatar_url"),
                display_name=github_user.get("name"),
                bio=github_user.get("bio"),
                website=github_user.get("blog"),
                location=github_user.get("location"),
                company=github_user.get("company"),
                is_active=True,
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
        else:
            # Update existing user
            user.github_username = github_user["login"]
            user.github_email = github_user.get("email")
            user.github_avatar_url = github_user.get("avatar_url")
            user.display_name = github_user.get("name")
            user.bio = github_user.get("bio")
            user.website = github_user.get("blog")
            user.location = github_user.get("location")
            user.company = github_user.get("company")
            user.last_login_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(user)
        
        # Generate JWT tokens
        access_token = auth_service.create_access_token(user.id)
        refresh_token = auth_service.create_refresh_token(user.id)
        
        return AuthSuccess(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user.public_profile
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Failed to authenticate with GitHub"
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"}
    },
    summary="Refresh access token",
    description="Get a new access token using a refresh token"
)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    
    try:
        # Validate refresh token and get user ID
        user_id = auth_service.verify_refresh_token(refresh_request.refresh_token)
        
        # Check if user still exists and is active
        user_stmt = select(User).where(User.id == user_id, User.is_active == True)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        # Generate new access token
        access_token = auth_service.create_access_token(user.id)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get(
    "/me",
    response_model=UserProfile,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Get current user",
    description="Get information about the currently authenticated user"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user's profile."""
    return current_user.public_profile


@router.post(
    "/logout",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Logout",
    description="Logout the current user (client-side token invalidation)"
)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout current user."""
    # In a JWT-based system, logout is typically handled client-side
    # by discarding the tokens. For enhanced security, you could:
    # 1. Maintain a blacklist of revoked tokens
    # 2. Use shorter token expiry times
    # 3. Implement token rotation
    
    return MessageResponse(message="Logged out successfully") 