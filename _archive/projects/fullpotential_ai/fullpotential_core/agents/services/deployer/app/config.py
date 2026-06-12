"""Configuration for Deployer"""

from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings"""

    # Service
    service_name: str = "deployer"
    service_port: int = 8007
    droplet_id: int = 24

    # Server Configuration
    server_host: str = "198.54.123.234"
    server_user: str = "root"
    ssh_key_path: str = "~/.ssh/fpai_deploy_ed25519"

    # Registry Integration
    registry_url: str = "http://198.54.123.234:8000"

    # Verifier Integration
    verifier_url: str = "http://localhost:8200"

    # Deployment Settings
    deployment_method: str = "docker"  # docker or systemd
    default_network: str = "fpai-network"
    deployment_timeout: int = 300  # 5 minutes

    # Auto-Registration
    auto_register: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def ssh_key_path_expanded(self) -> Path:
        """Expand ~ in SSH key path"""
        return Path(os.path.expanduser(self.ssh_key_path))


settings = Settings()
