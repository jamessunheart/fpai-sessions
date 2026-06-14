"""Application configuration settings for Autonomous Executor."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    service_name: str = "autonomous-executor"
    environment: str = "local"
    version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./executor.db"
    task_broker_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret"
    mission_id: str = "M001"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

