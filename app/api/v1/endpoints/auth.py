"""
Authentication API endpoints using GitHub OAuth.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth import auth_service
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/github")
async def github_oauth_login(
    redirect_to: str = Query(None, description="URL to redirect to after login")
):
    """Initiate GitHub OAuth login."""
    # Store redirect_to in state parameter (simplified)
    state = redirect_to or "default"
    oauth_url = auth_service.get_github_oauth_url(state)
    
    return {"oauth_url": oauth_url}


@router.get("/github/callback")
async def github_oauth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(None, description="OAuth state parameter"),
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback."""
    try:
        # Exchange code for access token
        token_data = await auth_service.exchange_code_for_token(code)
        github_access_token = token_data["access_token"]
        
        # Get user info from GitHub
        github_user_data = await auth_service.get_github_user_info(github_access_token)
        
        # Create or update user in database
        user = await auth_service.create_or_update_user(
            db, github_user_data, github_access_token
        )
        
        # Generate our JWT tokens
        access_token = auth_service.create_access_token(user.id)
        refresh_token = auth_service.create_refresh_token(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.public_profile,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    new_access_token = await auth_service.refresh_access_token(db, refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user.public_profile


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (invalidate tokens on client side)."""
    # In a production system, you might want to maintain a blacklist of tokens
    # For now, just return success - tokens will expire naturally
    return {"message": "Logged out successfully"} 