"""
Proof Witness - Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service info
    SERVICE_NAME: str = "proof-witness"
    APP_VERSION: str = "0.1.0"
    PORT: int = 8900
    DEBUG: bool = False

    # Database
    DATABASE_PATH: str = "./proof_witness.db"

    # GitHub integration
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    GITHUB_ORG: Optional[str] = None  # e.g., "jamessunheart"

    # Telegram integration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_PROOF_CHAT_ID: Optional[str] = None  # Where to send confirmations

    # Chief of Staff integration
    CHIEF_OF_STAFF_URL: str = "http://localhost:8107"

    # Auto-tagging
    TAG_CONFIDENCE_THRESHOLD: float = 0.6  # Only suggest tags if AI is >60% confident

    # Keywords for auto-tagging
    GREENHOUSE_KEYWORDS: list = ["greenhouse", "electrical", "plumbing", "construction", "remodel"]
    REVENUE_KEYWORDS: list = ["revenue", "payment", "transaction", "sale", "customer"]
    CONTENT_KEYWORDS: list = ["tiktok", "twitter", "post", "story", "video"]

    class Config:
        env_file = ".env"


settings = Settings()
