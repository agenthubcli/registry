"""
Authentication service for AgentHub Registry using GitHub OAuth.
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx
import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User

logger = structlog.get_logger()

# Password hashing (for token encryption)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service using GitHub OAuth."""
    
    def __init__(self):
        self.github_client_id = settings.GITHUB_CLIENT_ID
        self.github_client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = settings.GITHUB_OAUTH_REDIRECT_URI
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_minutes = settings.REFRESH_TOKEN_EXPIRE_MINUTES
    
    def get_github_oauth_url(self, state: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL."""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": self.github_client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "true",
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    async def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange GitHub OAuth code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "client_id": self.github_client_id,
                        "client_secret": self.github_client_secret,
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
                
                if response.status_code != 200:
                    logger.error("GitHub token exchange failed", status=response.status_code)
                    raise ValueError("Failed to exchange code for token")
                
                data = response.json()
                
                if "error" in data:
                    logger.error("GitHub OAuth error", error=data["error"])
                    raise ValueError(f"GitHub OAuth error: {data['error']}")
                
                return data
                
        except httpx.RequestError as e:
            logger.error("GitHub API request failed", error=str(e))
            raise ValueError("Failed to communicate with GitHub")
    
    async def get_github_user_info(self, access_token: str) -> Dict:
        """Get user information from GitHub API."""
        try:
            async with httpx.AsyncClient() as client:
                # Get user profile
                user_response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                
                if user_response.status_code != 200:
                    logger.error("GitHub user info request failed", status=user_response.status_code)
                    raise ValueError("Failed to get user info from GitHub")
                
                user_data = user_response.json()
                
                # Get user emails
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                
                emails_data = []
                if emails_response.status_code == 200:
                    emails_data = emails_response.json()
                
                # Find primary email
                primary_email = None
                for email in emails_data:
                    if email.get("primary", False):
                        primary_email = email["email"]
                        break
                
                # Combine user data with email
                user_data["primary_email"] = primary_email
                user_data["all_emails"] = emails_data
                
                return user_data
                
        except httpx.RequestError as e:
            logger.error("GitHub API request failed", error=str(e))
            raise ValueError("Failed to get user info from GitHub")
    
    async def create_or_update_user(self, db: AsyncSession, github_user_data: Dict, access_token: str) -> User:
        """Create or update user from GitHub data."""
        try:
            # Check if user exists
            stmt = select(User).where(User.github_id == github_user_data["id"])
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            # Encrypt the access token
            encrypted_token = pwd_context.hash(access_token)
            
            if user:
                # Update existing user
                user.github_username = github_user_data["login"]
                user.github_email = github_user_data.get("primary_email")
                user.github_avatar_url = github_user_data.get("avatar_url")
                user.display_name = github_user_data.get("name")
                user.bio = github_user_data.get("bio")
                user.website = github_user_data.get("blog")
                user.location = github_user_data.get("location")
                user.company = github_user_data.get("company")
                user.github_access_token = encrypted_token
                user.last_login_at = datetime.utcnow()
                user.updated_at = datetime.utcnow()
                
                logger.info("Updated existing user", github_id=user.github_id, username=user.github_username)
            else:
                # Create new user
                user = User(
                    github_id=github_user_data["id"],
                    github_username=github_user_data["login"],
                    github_email=github_user_data.get("primary_email"),
                    github_avatar_url=github_user_data.get("avatar_url"),
                    display_name=github_user_data.get("name"),
                    bio=github_user_data.get("bio"),
                    website=github_user_data.get("blog"),
                    location=github_user_data.get("location"),
                    company=github_user_data.get("company"),
                    github_access_token=encrypted_token,
                    is_verified=True,  # GitHub users are pre-verified
                    last_login_at=datetime.utcnow(),
                )
                
                db.add(user)
                logger.info("Created new user", github_id=user.github_id, username=user.github_username)
            
            await db.commit()
            await db.refresh(user)
            
            return user
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create/update user", error=str(e))
            raise
    
    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow(),
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(minutes=self.refresh_token_expire_minutes)
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow(),
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                return None
            
            return payload
            
        except JWTError:
            return None
    
    async def get_user_by_token(self, db: AsyncSession, token: str) -> Optional[User]:
        """Get user by JWT token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        try:
            stmt = select(User).where(User.id == int(user_id), User.is_active == True)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by token", error=str(e))
            return None
    
    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Verify user still exists and is active
        user = await self.get_user_by_token(db, refresh_token)
        if not user:
            return None
        
        # Create new access token
        return self.create_access_token(user.id)
    
    def hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return pwd_context.hash(token)
    
    def verify_hashed_token(self, token: str, hashed_token: str) -> bool:
        """Verify a token against its hash."""
        return pwd_context.verify(token, hashed_token)


# Global auth service instance
auth_service = AuthService() 