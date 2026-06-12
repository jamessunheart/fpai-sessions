"""Configuration management for I PROACTIVE"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Service Configuration
    service_name: str = "i-proactive"
    service_port: int = 8400
    service_host: str = "0.0.0.0"
    droplet_id: int = 20

    # AI Model API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # Ollama (Local Sovereign AI)
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Mem0 Configuration
    mem0_config_path: str = "./config/mem0_config.json"

    # Registry Integration
    registry_url: str = "http://198.54.123.234:8000"

    # Orchestrator Integration
    orchestrator_url: str = "http://198.54.123.234:8001"

    # CrewAI Configuration
    crew_max_agents: int = 10
    crew_parallel_execution: bool = True
    crew_verbose: bool = True

    # Strategic Decision Engine
    priority_algorithm: Literal["weighted_multi_criteria", "simple", "ml_based"] = "weighted_multi_criteria"
    risk_threshold: float = 0.7
    resource_allocation_mode: Literal["static", "dynamic", "adaptive"] = "dynamic"

    # Logging
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
