"""Configuration for Autonomous Executor"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Autonomous Executor Settings"""

    # Service
    executor_port: int = 8400
    executor_host: str = "0.0.0.0"

    # Claude API
    anthropic_api_key: Optional[str] = None  # Optional for testing UDC compliance
    claude_model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096

    # GitHub
    github_token: Optional[str] = None
    github_org: str = "fullpotential-ai"

    # Paths
    development_base_path: str = "/Users/jamessunheart/Development"
    foundation_files_path: str = "/Users/jamessunheart/Development/AI FILES"

    # Sacred Loop Tools
    fp_tools_path: str = "/Users/jamessunheart/Development/RESOURCES/tools/fullpotential-tools/bin/fp-tools"
    fpai_tools_path: str = "/Users/jamessunheart/Development/RESOURCES/tools/fpai-tools"

    # Registry Integration
    registry_url: str = "http://localhost:8000"

    # Build Settings
    max_build_iterations: int = 10
    build_timeout_minutes: int = 120

    # Notifications
    slack_webhook_url: Optional[str] = None
    notification_email: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
