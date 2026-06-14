"""
Configuration management for Multi-Cloud Droplet Manager
Centralized settings using Pydantic
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Droplet Identity
    droplet_id: int = 4
    droplet_name: str = "Multi-Cloud Manager"
    droplet_domain: str = "drop4.fullpotential.ai"
    steward: str = "Hassan"
    version: str = "1.0.0"
    udc_version: str = "1.0"
    
    # Server Configuration
    port: int = 8010
    api_token: str = "secretkey_7f8b4e2a9d034b5cb7219d6f81e3d2c1"
    
    # Cloud Provider Tokens
    do_token: str = ""
    hetzner_token: str = ""
    vultr_token: str = ""
    
    # Registry Configuration (v2)
    registry_url: str = "https://drop18.fullpotential.ai"
    registry_key: str = "a5447df6e4fe34df8c4d0c671ad98ce78de9e55cf152e5d07e5bf221769e31dc"
    orchestrator_url: str = "https://drop18.fullpotential.ai"
    heartbeat_interval: int = 30
    
    # JWT Configuration (Incoming - for verifying tokens FROM other services)
    jwt_issuer: str = "registry.fullpotential.ai"
    jwt_audience: str = "fullpotential.droplets"
    jwt_algorithm: str = "RS256"
    jwks_url: str = "https://drop18.fullpotential.ai/.well-known/jwks.json"
    allow_simple_token: bool = True
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env without error


settings = Settings()
