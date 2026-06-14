"""Configuration management for Proxy Manager."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service
    proxy_manager_port: int = 8100

    # NGINX paths
    nginx_sites_available: str = "/etc/nginx/sites-available"
    nginx_sites_enabled: str = "/etc/nginx/sites-enabled"
    nginx_bin: str = "/usr/sbin/nginx"

    # Certbot
    certbot_bin: str = "/usr/bin/certbot"
    default_ssl_email: str = "admin@fullpotential.ai"

    # Registry integration
    registry_url: Optional[str] = None

    # Health checks
    health_check_timeout_ms: int = 1000
    health_check_path: str = "/health"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
