# Config settings
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "proxy-manager"
    service_port: int = 8100
    
    # Nginx configuration - Default to local temp dirs for development/testing
    nginx_sites_available: str = os.getenv("NGINX_SITES_AVAILABLE", "./tmp/nginx/sites-available")
    nginx_sites_enabled: str = os.getenv("NGINX_SITES_ENABLED", "./tmp/nginx/sites-enabled")
    nginx_bin: str = os.getenv("NGINX_BIN", "/usr/sbin/nginx")
    
    # SSL configuration
    certbot_bin: str = os.getenv("CERTBOT_BIN", "/usr/bin/certbot")
    default_ssl_email: str = "admin@fullpotential.ai"
    
    # Registry integration
    registry_url: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
