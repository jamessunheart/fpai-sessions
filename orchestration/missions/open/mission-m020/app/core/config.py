"""Application configuration settings."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    service_name: str = "treasury-growth-backend"
    environment: str = "local"
    version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./treasury.db"
    mission_id: str = "M020"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

