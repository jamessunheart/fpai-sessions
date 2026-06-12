"""
WhiteRock Blessings Engine - Configuration
Uses Pydantic Settings for environment-based configuration.
v2.2 - With security enhancements
"""

import secrets
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "WhiteRock Blessings Engine"
    APP_VERSION: str = "2.2.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8020
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/whiterock"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_RECYCLE: int = 3600  # Recycle connections after 1 hour
    DATABASE_POOL_TIMEOUT: int = 30
    
    # JWT Authentication - MUST be set in production via environment variable
    JWT_SECRET: str = ""  # Will generate secure default if not set
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    
    # Rate Limiting (per IP/user)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REGISTER: str = "5/hour"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_TITHE: str = "20/hour"
    RATE_LIMIT_BLESSING: str = "5/day"
    RATE_LIMIT_DEFAULT: str = "100/minute"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "https://whiterock.us",
        "https://www.whiterock.us",
        "https://api.whiterock.us",
    ]
    
    # Stripe
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # SendGrid
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "blessings@whiterock.us"
    SENDGRID_FROM_NAME: str = "WhiteRock Ministry"
    
    # Redis (for Celery and Caching)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_CAPACITY: int = 60  # 1 minute
    CACHE_TTL_TIERS: int = 3600  # 1 hour
    CACHE_TTL_DISCLOSURE: int = 3600  # 1 hour
    CACHE_TTL_STATS: int = 300  # 5 minutes
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # CORA Configuration
    CORA_DECAY_RATE: float = 0.10  # 10% monthly decay
    CORA_DECAY_THRESHOLD_MONTHS: int = 12  # Start decay after 12 months inactivity
    CORA_DECAY_WARNING_DAYS: int = 30  # Warn 30 days before first decay
    
    # Blessing Categories
    BLESSING_CATEGORIES: list = [
        "housing", "food", "medical", "education", 
        "emergency", "utilities", "other"
    ]
    
    # UDC Registry
    REGISTRY_URL: str = "http://198.54.123.234:8000"
    ORCHESTRATOR_URL: str = "http://198.54.123.234:8010"
    SERVICE_ID: str = "whiterock-blessings"
    
    # Compliance
    CURRENT_DISCLOSURE_VERSION: str = "1.0.0"
    MIN_MEMBERSHIP_DAYS_FOR_BLESSING: int = 30
    
    # Email Disclaimer Footer (REQUIRED)
    BLESSING_EMAIL_FOOTER: str = """
This blessing is a one-time discretionary gift from WhiteRock community 
and does not constitute an ongoing obligation, contract, or entitlement 
to future support.

WhiteRock Church Trust - 508(c)(1)(A) Religious Organization
"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Generate secure JWT secret if not provided
        if not self.JWT_SECRET:
            self.JWT_SECRET = secrets.token_urlsafe(32)
            if not self.DEBUG:
                import warnings
                warnings.warn(
                    "JWT_SECRET not set! Using auto-generated secret. "
                    "Set JWT_SECRET environment variable for production.",
                    RuntimeWarning
                )

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton access
settings = get_settings()

