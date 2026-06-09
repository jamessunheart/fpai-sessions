"""Configuration for Trust Index Service."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration."""
    
    # Service
    SERVICE_NAME: str = "trust-index"
    SERVICE_PORT: int = 8560
    DEBUG: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"
    
    # External Services (same server = localhost)
    CREDITS_GATEWAY_URL: str = "http://localhost:8765"
    CONTRIBUTION_TRACKER_URL: str = "http://localhost:8570"
    NEEDS_ALLOCATION_URL: str = "http://localhost:8565"

    # Commons Reserve (ledger account on Credits Gateway)
    COMMONS_RESERVE_ACCOUNT: str = "system:commons"
    
    # Component Weights
    WEIGHT_SOLVENCY: float = 0.40
    WEIGHT_COMMONS_HEALTH: float = 0.30
    WEIGHT_PARTICIPATION: float = 0.30
    
    # Thresholds
    THRESHOLD_CONSERVATIVE: float = 0.30
    THRESHOLD_GENEROUS: float = 0.70
    
    # Guardrails
    MIN_RESERVE_RATIO: float = 1.20
    MAX_DAILY_CHANGE: float = 0.05
    EMERGENCY_FREEZE_THRESHOLD: float = 0.20
    MAX_SINGLE_ALLOCATION: float = 0.05
    
    # Update interval (seconds)
    UPDATE_INTERVAL: int = 3600  # 1 hour
    
    class Config:
        env_prefix = "TRUST_INDEX_"
        env_file = ".env"


settings = Settings()


# Guardrails (cannot be overridden)
GUARDRAILS = {
    "min_reserve_ratio": settings.MIN_RESERVE_RATIO,
    "max_daily_change": settings.MAX_DAILY_CHANGE,
    "emergency_freeze": settings.EMERGENCY_FREEZE_THRESHOLD,
    "human_override": True,
    "max_single_allocation": settings.MAX_SINGLE_ALLOCATION
}

