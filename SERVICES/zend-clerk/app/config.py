"""Configuration for Zend Clerk (POS Chat Agent).

Canonical Spec: docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 8
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "zend-clerk"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8582
    DEBUG: bool = False

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None  # For production webhook mode

    # Zend Payments API
    ZEND_PAYMENTS_URL: str = "http://localhost:8581"

    # Zend Wallet API (for UC balance checks)
    ZEND_WALLET_URL: str = "http://localhost:8580"

    # Credits Gateway
    CREDITS_GATEWAY_URL: str = "http://localhost:8765"

    # Default settings
    DEFAULT_COMMONS_TITHE_PCT: float = 0.0
    DEFAULT_EXPIRY_MINUTES: int = 30

    class Config:
        env_prefix = "ZEND_CLERK_"
        env_file = ".env"


settings = Settings()




