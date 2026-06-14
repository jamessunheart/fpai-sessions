"""Configuration settings for Proxy Manager."""
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Proxy Manager"
    VERSION: str = "1.0.0"
    
    # Server
    PROXY_MANAGER_PORT: int = 8100
    
    # Nginx
    nginx_bin: str = "nginx"
    nginx_sites_available: str = "/etc/nginx/sites-available"
    nginx_sites_enabled: str = "/etc/nginx/sites-enabled"
    
    # UDC
    registry_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
