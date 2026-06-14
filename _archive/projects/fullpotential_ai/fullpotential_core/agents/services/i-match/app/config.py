"""Configuration management for I MATCH"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Service Configuration
    service_name: str = "i-match"
    service_port: int = 8401
    service_host: str = "0.0.0.0"
    droplet_id: int = 21

    # Database
    database_url: str = "sqlite:///./imatch.db"

    # AI Model API Keys
    anthropic_api_key: str = ""

    # Ollama (Local Sovereign AI)
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Stripe Configuration
    stripe_api_key: str = ""
    stripe_secret_key: str = ""  # Alternative name for Stripe key
    stripe_webhook_secret: str = ""

    # Commission Settings
    default_commission_percent: float = 20.0
    minimum_match_score: int = 70

    # Email Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = "matches@fullpotential.ai"

    # Registry Integration
    registry_url: str = "http://198.54.123.234:8000"

    # I PROACTIVE Integration
    i_proactive_url: str = "http://localhost:8400"

    # Frontend URL
    frontend_url: str = "http://localhost:3000"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
