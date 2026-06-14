"""
Ad Portal Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment"""
    
    # Service
    APP_NAME: str = "Ad Portal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8800
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://adportal:adportal@localhost:5432/ad_portal"
    
    # Meta Ads
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""
    META_AD_ACCOUNT_ID: str = ""  # Format: act_XXXXX
    META_PIXEL_ID: str = ""
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # UC Credits Gateway
    UC_GATEWAY_URL: str = "http://198.54.123.234:8765"
    
    # AI Brain
    AI_BRAIN_URL: str = "http://162.0.208.88:8101"
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8801", "https://fullpotential.ai"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()


