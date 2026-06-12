import os
from typing import Literal
from dotenv import load_dotenv

# Load .env file with override to force reload
load_dotenv(override=True)


class DropletConfig:
    def __init__(self):
        self.id = int(os.getenv("DROPLET_ID", "42"))
        self.registry_id = os.getenv("DROPLET_REGISTRY_ID", f"droplet-{self.id}")
        self.name = os.getenv("DROPLET_NAME", "droplet0")
        self.steward = os.getenv("DROPLET_STEWARD", "Haythem")
        self.url = os.getenv("DROPLET_URL", "http://localhost:8001")
        self.version = os.getenv("DROPLET_VERSION", "1.0.0")
        self.udc_version = os.getenv("DROPLET_UDC_VERSION", "1.0")

class RegistryConfig:
    def __init__(self):
        self.url = os.getenv("REGISTRY_URL", "https://drop18.fullpotential.ai")

class Config:
    def __init__(self):
        self.droplet = DropletConfig()
        self.registry = RegistryConfig()

class Settings:
    # Droplet Configuration
    droplet_id: int = int(os.getenv("DROPLET_ID", "42"))
    droplet_name: str = os.getenv("DROPLET_NAME", "droplet0")
    droplet_steward: str = os.getenv("DROPLET_STEWARD", "Haythem")
    droplet_url: str = os.getenv("DROPLET_URL", "http://localhost:8001")
    
    # External Services
    registry_url: str = os.getenv("REGISTRY_URL", "https://drop18.fullpotential.ai")
    orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "https://orchestrator.fullpotential.ai")
    
    # Security
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-key")
    registry_public_key: str = os.getenv("REGISTRY_PUBLIC_KEY", "")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Airtable Configuration
    airtable_api_key: str = os.getenv("AIRTABLE_API_KEY", "")
    airtable_base_id: str = os.getenv("BASE_ID", "")

def get_config():
    return Config()

settings = Settings()