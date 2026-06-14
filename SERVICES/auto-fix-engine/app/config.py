"""Configuration for Auto-Fix Engine"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service
    service_name: str = "auto-fix-engine"
    service_port: int = 8300
    droplet_id: int = 23

    # AI Configuration
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 8000

    # Fix Settings
    max_fix_iterations: int = 3

    # Verifier Integration
    verifier_url: str = "http://localhost:8200"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
