"""Configuration management for Orchestrator service."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variable mapping (case-insensitive):
    - SERVICE_NAME
    - VERSION
    - ENVIRONMENT
    - LOG_LEVEL
    - REGISTRY_URL
    - REGISTRY_SYNC_INTERVAL
    - REGISTRY_TIMEOUT
    - CACHE_DIR or REGISTRY_CACHE_DIR (both work)
    - TASK_TIMEOUT
    - TASK_MAX_RETRIES
    - TASK_MAX_HISTORY
    - HOST
    - PORT
    """

    # Service
    service_name: str = "orchestrator"
    version: str = "1.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # Registry
    registry_url: str = "http://localhost:8000"
    registry_sync_interval: int = 60  # seconds
    registry_timeout: float = 5.0  # seconds
    registry_cache_dir: str = Field(
        default="/var/cache/fpai",
        validation_alias="cache_dir",  # Accept CACHE_DIR env var
    )
    registry_cache_expiry: int = 300  # seconds (5 minutes)

    # Tasks
    task_timeout: int = 30  # seconds
    task_max_retries: int = 3
    task_max_history: int = 10000  # keep last N tasks in memory

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
