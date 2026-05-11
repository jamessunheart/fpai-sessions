"""Configuration for SPEC Verifier Service"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """SPEC Verifier Settings"""

    # Service
    service_name: str = "spec-verifier"
    service_port: int = 8205
    service_host: str = "0.0.0.0"
    service_version: str = "1.0.0"

    # Registry Integration
    registry_url: str = "http://localhost:8000"
    registry_id: int = 7

    # Paths
    services_base_path: str = "/Users/jamessunheart/Development/SERVICES"

    # Validation Settings
    strict_mode: bool = False
    min_build_ready_score: int = 75

    # Required SPEC sections
    required_sections: list[str] = [
        "Purpose",
        "Capabilities",
        "UDC Endpoints",
        "Dependencies"
    ]

    # UDC Endpoints
    required_udc_endpoints: list[str] = [
        "/health",
        "/capabilities",
        "/state",
        "/dependencies",
        "/message"
    ]

    class Config:
        env_file = ".env"


settings = Settings()
