"""Configuration for governance service"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    service_name: str = "governance"
    service_port: int = 8213
    service_host: str = "0.0.0.0"
    service_version: str = "1.0.0"
    tier: int = 0

    registry_url: str = "http://localhost:8000"
    intent_queue_url: str = "http://localhost:8212"

    # Claude API configuration
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-5-20250929"

    # Governance settings
    alignment_threshold: float = 0.85
    default_mode: str = "supervised"  # supervised, autonomous, aggressive

    # Blueprint file path
    blueprint_path: str = "/Users/jamessunheart/Development/ARCHITECTURE/BLUEPRINT.md"

    class Config:
        env_file = ".env"

settings = Settings()
