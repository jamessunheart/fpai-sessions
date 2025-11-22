"""Configuration for SPEC Builder Service"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """SPEC Builder Settings"""

    # Service
    service_name: str = "spec-builder"
    service_port: int = 8207
    service_host: str = "0.0.0.0"
    service_version: str = "1.0.0"

    # Claude API
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8192
    temperature: float = 0.3

    # Integration
    registry_url: str = "http://localhost:8000"
    registry_id: int = 9
    spec_verifier_url: str = "http://localhost:8205"
    spec_optimizer_url: str = "http://localhost:8206"

    # Paths
    services_base_path: str = "/Users/jamessunheart/Development/SERVICES"

    # Generation Settings
    default_target_score: int = 90
    auto_optimize: bool = True

    # Cost Tracking
    input_cost_per_million: float = 3.0
    output_cost_per_million: float = 15.0

    class Config:
        env_file = ".env"


settings = Settings()
