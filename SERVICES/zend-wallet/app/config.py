"""Configuration for Zend Wallet service.

Canonical Spec: docs/protocols/ZEND_REGENERATIVE_SPEC.md (v2.0)
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "zend-wallet"
    SERVICE_VERSION: str = "2.0.0"  # Regenerative integration
    SERVICE_PORT: int = 8580
    DEBUG: bool = False

    # Simple MVP protection (optional)
    ZEND_ADMIN_KEY: Optional[str] = None  # if set, require X-Zend-Key on write endpoints

    # Credits Gateway (SSOT)
    CREDITS_GATEWAY_URL: str = "http://localhost:8765"
    CREDITS_API_KEY: Optional[str] = None  # service API key (read/transfer [+debit if using /api/ai/query])

    # Ledger accounts used by Zend
    ESCROW_ACCOUNT: str = "system:zend_escrow"
    FEES_ACCOUNT: str = "system:zend_fees"
    OPS_ACCOUNT: str = "system:zend_ops"

    # Limits (MVP) - per ZEND_REGENERATIVE_SPEC.md Part 9
    MAX_SEND_UC: float = 10000.0  # Hard guardrail
    MAX_DAILY_SEND_UC: float = 25000.0  # Hardcoded per spec
    HUMAN_ESCALATION_THRESHOLD: float = 5000.0  # Require human review

    # AI drafting
    USE_CREDITS_GATEWAY_AI_QUERY: bool = True
    AI_PROVIDER: str = "anthropic"  # passed to credits gateway /api/ai/query if enabled
    AI_MAX_TOKENS: int = 300
    AI_BRAIN_URL: str = "http://162.0.208.88:8101"  # fallback direct call

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./zend_wallet.db"

    # ==========================================================
    # REGENERATIVE INTEGRATIONS (v2.0)
    # ==========================================================

    # Trust Index - adaptive ease based on Commons health
    TRUST_INDEX_URL: str = "http://localhost:8560"
    TRUST_INDEX_ENABLED: bool = True

    # Contribution Tracker - sends earn Proof of Contribution
    CONTRIBUTION_TRACKER_URL: str = "http://localhost:8570"
    CONTRIBUTION_LOGGING_ENABLED: bool = True

    # Experience layer thresholds (UC lifetime balance)
    EXPERIENCE_THRESHOLD_MEDITATION: float = 100.0
    EXPERIENCE_THRESHOLD_ZEN_RAFFLE: float = 250.0
    EXPERIENCE_THRESHOLD_SEND_FOR_ME: float = 500.0
    EXPERIENCE_THRESHOLD_CONCIERGE: float = 1000.0
    EXPERIENCE_THRESHOLD_FOUNDER: float = 2500.0

    class Config:
        env_prefix = "ZEND_"
        env_file = ".env"


settings = Settings()


