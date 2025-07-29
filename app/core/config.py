"""
Configuration settings for AgentHub Registry.
"""

import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Basic app settings
    PROJECT_NAME: str = "AgentHub Registry"
    PROJECT_DESCRIPTION: str = "Universal package registry for AI-native agents, tools, chains, and prompts"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 8, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 30, env="REFRESH_TOKEN_EXPIRE_MINUTES")  # 30 days
    
    # CORS and Security
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"], 
        env="ALLOWED_HOSTS",
        description="Comma-separated list of allowed hosts"
    )
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")  # 1 hour
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    S3_BUCKET_NAME: str = Field(env="S3_BUCKET_NAME")
    S3_PUBLIC_BASE_URL: Optional[str] = Field(default=None, env="S3_PUBLIC_BASE_URL")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: str = Field(env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: str = Field(env="GITHUB_CLIENT_SECRET")
    GITHUB_OAUTH_REDIRECT_URI: str = Field(env="GITHUB_OAUTH_REDIRECT_URI")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_BURST: int = Field(default=200, env="RATE_LIMIT_BURST")
    
    # Search Settings
    SEARCH_RESULTS_PER_PAGE: int = Field(default=20, env="SEARCH_RESULTS_PER_PAGE")
    MAX_SEARCH_RESULTS: int = Field(default=1000, env="MAX_SEARCH_RESULTS")
    
    # Package Settings
    MAX_PACKAGE_SIZE_MB: int = Field(default=100, env="MAX_PACKAGE_SIZE_MB")
    MAX_DESCRIPTION_LENGTH: int = Field(default=1000, env="MAX_DESCRIPTION_LENGTH")
    MAX_README_LENGTH: int = Field(default=50000, env="MAX_README_LENGTH")
    SUPPORTED_PACKAGE_TYPES: List[str] = Field(
        default=["agent", "tool", "chain", "prompt", "dataset"],
        env="SUPPORTED_PACKAGE_TYPES"
    )
    
    # Monitoring & Observability
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    
    # Email Settings (for notifications)
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: Optional[int] = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_TLS: bool = Field(default=True, env="SMTP_TLS")
    
    # Admin Settings
    ADMIN_EMAIL: Optional[EmailStr] = Field(default=None, env="ADMIN_EMAIL")
    FIRST_SUPERUSER_EMAIL: Optional[EmailStr] = Field(default=None, env="FIRST_SUPERUSER_EMAIL")
    
    # Background Tasks
    CELERY_BROKER_URL: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")
    
    # Content Delivery
    CDN_BASE_URL: Optional[str] = Field(default=None, env="CDN_BASE_URL")
    
    # Analytics
    ANALYTICS_ENABLED: bool = Field(default=True, env="ANALYTICS_ENABLED")
    DOWNLOAD_STATS_RETENTION_DAYS: int = Field(default=365, env="DOWNLOAD_STATS_RETENTION_DAYS")
    
    # Package Validation
    VALIDATE_PACKAGE_SCHEMAS: bool = Field(default=True, env="VALIDATE_PACKAGE_SCHEMAS")
    SCHEMA_CACHE_TTL: int = Field(default=3600, env="SCHEMA_CACHE_TTL")
    
    # Feature Flags
    ENABLE_PACKAGE_DELETION: bool = Field(default=False, env="ENABLE_PACKAGE_DELETION")
    ENABLE_PRIVATE_PACKAGES: bool = Field(default=False, env="ENABLE_PRIVATE_PACKAGES")
    ENABLE_PACKAGE_MIRRORING: bool = Field(default=False, env="ENABLE_PACKAGE_MIRRORING")
    
    # API Documentation
    ENABLE_DOCS: bool = Field(default=True, env="ENABLE_DOCS")
    DOCS_REQUIRE_AUTH: bool = Field(default=False, env="DOCS_REQUIRE_AUTH")
    
    # Security & Scanning
    ENABLE_VIRUS_SCANNING: bool = Field(default=True, env="ENABLE_VIRUS_SCANNING")
    ENABLE_VULNERABILITY_SCANNING: bool = Field(default=True, env="ENABLE_VULNERABILITY_SCANNING")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @property
    def database_url_async(self) -> str:
        """Get async database URL."""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def s3_public_url(self) -> str:
        """Get S3 public URL base."""
        if self.S3_PUBLIC_BASE_URL:
            return self.S3_PUBLIC_BASE_URL.rstrip("/")
        return f"https://{self.S3_BUCKET_NAME}.s3.{self.AWS_REGION}.amazonaws.com"


# Create global settings instance
settings = Settings() 