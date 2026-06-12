"""Configuration for Contribution Tracker Service."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Service configuration."""
    
    # Service
    SERVICE_NAME: str = "contribution-tracker"
    SERVICE_PORT: int = 8570
    DEBUG: bool = False
    
    # Database (Commons Ministry database)
    DATABASE_URL: str = "postgresql+asyncpg://commons:commons123@localhost:5432/commons"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # External Services
    CREDITS_GATEWAY_URL: str = "http://localhost:8765"
    TRUST_INDEX_URL: str = "http://localhost:8560"
    PMA_SERVICE_URL: str = "http://localhost:8400"
    
    # TRUST Token Rates
    TRUST_RATE_SERVICE_HOUR: int = 10
    TRUST_RATE_GOVERNANCE_VOTE: int = 5
    TRUST_RATE_REFERRAL: int = 50
    TRUST_RATE_FINANCIAL_PER_UC: int = 1
    
    # Founding Period
    FOUNDING_MULTIPLIER: float = 1.5
    FOUNDING_THRESHOLD_UC: float = 100000  # End founding when reserve > $100K
    
    # Tiers
    TIER_ACTIVE_MIN: int = 100
    TIER_ENGAGED_MIN: int = 50
    
    # Verification
    VERIFICATION_TIMEOUT_DAYS: int = 7
    
    class Config:
        env_prefix = "CONTRIB_"
        env_file = ".env"


settings = Settings()

