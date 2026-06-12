"""
Configuration management for Alerts Service
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    # Service Info
    SERVICE_NAME: str = "alerts"
    DROPLET_ID: int = 106
    APP_VERSION: str = "1.0.0"
    PORT: int = 8765
    DEBUG: bool = False

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_STEWARD_CHAT_ID: str = ""

    # Twilio Configuration (SMS)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Queue Configuration
    MAX_QUEUE_SIZE: int = 1000
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Channel Rate Limits (messages per minute)
    TELEGRAM_RATE_LIMIT: int = 30
    SMS_RATE_LIMIT: int = 5

    # Retry Configuration
    TELEGRAM_RETRY_COUNT: int = 3
    TELEGRAM_RETRY_DELAY: int = 5  # seconds
    SMS_RETRY_COUNT: int = 2
    SMS_RETRY_DELAY: int = 10  # seconds

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
