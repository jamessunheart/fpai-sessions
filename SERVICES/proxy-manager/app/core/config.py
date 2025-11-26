import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Service Identity
    SERVICE_NAME: str = "proxy-manager"
    DROPLET_ID: int = 3
    VERSION: str = "1.0.0"
    
    # Server Config
    PORT: int = 8100
    HOST: str = "0.0.0.0"
    
    # Infrastructure
    NGINX_SITES_AVAILABLE: str = os.getenv("NGINX_SITES_AVAILABLE", "/etc/nginx/sites-available")
    NGINX_SITES_ENABLED: str = os.getenv("NGINX_SITES_ENABLED", "/etc/nginx/sites-enabled")
    NGINX_BIN: str = os.getenv("NGINX_BIN", "/usr/sbin/nginx")
    CERTBOT_BIN: str = os.getenv("CERTBOT_BIN", "/usr/bin/certbot")
    DEFAULT_SSL_EMAIL: str = os.getenv("DEFAULT_SSL_EMAIL", "admin@fullpotential.ai")
    
    # External Services
    REGISTRY_URL: str = os.getenv("REGISTRY_URL", "http://registry:8000")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"

settings = Settings()






