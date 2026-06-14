"""Configuration for Needs Allocation Engine."""
from pydantic_settings import BaseSettings
from typing import Dict, Optional


class Settings(BaseSettings):
    """Service configuration."""
    
    # Service
    SERVICE_NAME: str = "needs-allocation"
    SERVICE_PORT: int = 8565
    DEBUG: bool = False
    
    # Database (Commons Ministry database)
    DATABASE_URL: str = "postgresql+asyncpg://commons:commons123@localhost:5432/commons"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/2"
    
    # External Services
    TRUST_INDEX_URL: str = "http://localhost:8560"
    CONTRIBUTION_TRACKER_URL: str = "http://localhost:8570"
    CREDITS_GATEWAY_URL: str = "http://localhost:8765"

    # Credits Gateway Auth (use a limited service API key, not the master key)
    CREDITS_API_KEY: Optional[str] = None
    CREDITS_TRANSFER_CREDIT_TYPE: str = "fp_credits"

    # Commons Reserve Source
    # - If COMMONS_RESERVE_UC_OVERRIDE is set, use it (useful for staging/simulation)
    # - Otherwise, fetch credits gateway /api/treasury/allocations and read COMMONS_RESERVE_ACCOUNT
    COMMONS_RESERVE_ACCOUNT: str = "system:commons"
    COMMONS_RESERVE_UC_OVERRIDE: Optional[float] = None

    # Escrow account (system bucket used when fulfilling a request)
    # Funds move: system:commons → system:needs_escrow
    ESCROW_ACCOUNT: str = "system:needs_escrow"
    
    # Category Allocations
    CATEGORY_SURVIVAL: float = 0.40
    CATEGORY_STABILITY: float = 0.25
    CATEGORY_GROWTH: float = 0.20
    CATEGORY_CONTRIBUTION: float = 0.10
    CATEGORY_INFRASTRUCTURE: float = 0.05
    
    # Eligibility
    MIN_TRUST_SURVIVAL: int = 50
    MIN_TRUST_STABILITY: int = 100
    MIN_TRUST_GROWTH: int = 150
    MIN_CONTRIBUTION_SCORE: int = 100
    
    # Fairness Limits
    MAX_SINGLE_ALLOCATION_PERCENT: float = 0.05
    MAX_SINGLE_ALLOCATION_ABSOLUTE: float = 1000
    MAX_REQUESTS_PER_MONTH: int = 3
    COOLDOWN_DAYS_LARGE: int = 30
    LARGE_ALLOCATION_THRESHOLD: float = 200
    
    # Guardrails
    MIN_RESERVE_RATIO: float = 1.20
    EMERGENCY_FREEZE_TRUST_INDEX: float = 0.20
    
    class Config:
        env_prefix = "NEEDS_"
        env_file = ".env"


settings = Settings()

# Category configuration
CATEGORIES = {
    "survival": {
        "allocation": settings.CATEGORY_SURVIVAL,
        "min_trust": settings.MIN_TRUST_SURVIVAL,
        "description": "Food, shelter, health emergencies",
        "examples": ["rent", "utilities", "medical", "food"]
    },
    "stability": {
        "allocation": settings.CATEGORY_STABILITY,
        "min_trust": settings.MIN_TRUST_STABILITY,
        "description": "Debt relief, emergency fund, insurance",
        "examples": ["debt_payment", "emergency_fund", "insurance"]
    },
    "growth": {
        "allocation": settings.CATEGORY_GROWTH,
        "min_trust": settings.MIN_TRUST_GROWTH,
        "description": "Education, tools, creation grants",
        "examples": ["education", "tools", "equipment", "courses"]
    },
    "contribution": {
        "allocation": settings.CATEGORY_CONTRIBUTION,
        "min_trust": settings.MIN_TRUST_STABILITY,
        "description": "Contributor recognition and support",
        "examples": ["contributor_bonus", "recognition"]
    },
    "infrastructure": {
        "allocation": settings.CATEGORY_INFRASTRUCTURE,
        "min_trust": settings.MIN_TRUST_GROWTH,
        "description": "Commons infrastructure, public goods",
        "examples": ["infrastructure", "public_goods"]
    }
}

