"""Configuration for SPEC Optimizer Service"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """SPEC Optimizer Settings"""

    # Service
    service_name: str = "spec-optimizer"
    service_port: int = 8206
    service_host: str = "0.0.0.0"
    service_version: str = "1.0.0"

    # Claude API
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8192
    temperature: float = 0.3

    # Integration
    registry_url: str = "http://localhost:8000"
    registry_id: int = 8
    spec_verifier_url: str = "http://localhost:8205"

    # Paths
    services_base_path: str = "/Users/jamessunheart/Development/SERVICES"

    # Optimization Settings
    default_optimization_level: str = "standard"
    default_target_score: int = 85
    max_optimization_iterations: int = 3

    # Cost Tracking
    input_cost_per_million: float = 3.0  # $3 per million input tokens
    output_cost_per_million: float = 15.0  # $15 per million output tokens

    class Config:
        env_file = ".env"


settings = Settings()
