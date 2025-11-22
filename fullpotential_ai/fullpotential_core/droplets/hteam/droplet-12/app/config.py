"""
Configuration Management
Per TECH_STACK.md and SECURITY_REQUIREMENTS.md
"""

from pydantic_settings import BaseSettings
from pydantic import SecretStr, validator
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    """
    Application settings with validation.
    Per SECURITY_REQUIREMENTS.md - all secrets via environment variables.
    """
    
    # ==================== AI Configuration ====================
    gemini_api_key: SecretStr
    
    # ==================== Droplet Configuration ====================
    id: str = "12"
    droplet_id: str = "droplet-12"
    droplet_name: str = "Chat Orchestrator"
    droplet_steward: str = "Zainab"
    droplet_url: str = "http://127.0.0.1:8012"
    
    # ==================== Registry Configuration ====================
    registry_url: str = "http://127.0.0.1:8010"
    jwt_key: SecretStr  # JWT token for heartbeats/registration (get from Registry)
    registry_public_key: SecretStr  # Public key for verifying tokens from other droplets
    droplet_secret: SecretStr
    
    
    # JWT Configuration (per SECURITY_REQUIREMENTS.md)
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "registry.fullpotential.ai"
    jwt_audience: str = "fullpotential.droplets"
    
    # ==================== Orchestrator Configuration ====================
    orchestrator_url: str = "https://drop10.fullpotential.ai"
    orchestrator_jwt: SecretStr
    orchestrator_secret_key: SecretStr
    
    # ==================== Server Configuration ====================
    port: int = 8012
    host: str = "0.0.0.0"
    workers: int = 4
    
    # ==================== Environment ====================
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # ==================== Session Configuration ====================
    session_max_history: int = 10
    session_timeout_minutes: int = 30
    
    # ==================== API Timeouts ====================
    orchestrator_timeout: int = 5
    registry_timeout: int = 10
    gemini_timeout: int = 30
    
    # ==================== Rate Limiting ====================
    rate_limit_chat: int = 100
    rate_limit_websocket: int = 200
    rate_limit_process: int = 50
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting"""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    def get_gemini_api_key(self) -> str:
        """Safely get Gemini API key"""
        return self.gemini_api_key.get_secret_value()
    
    def get_droplet_secret(self) -> str:
        """Safely get droplet secret"""
        return self.droplet_secret.get_secret_value()
    
    def get_orchestrator_jwt(self) -> str:
        """Safely get orchestrator JWT"""
        return self.orchestrator_jwt.get_secret_value()

    def get_orchestrator_secret_key(self) -> str:
        """Safely get orchestrator secret key"""
        return self.orchestrator_secret_key.get_secret_value()

    def set_orchestrator_jwt(self, token: str):
        """Safely set the orchestrator JWT after fetching it."""
        self.orchestrator_jwt = SecretStr(token)
    
    def set_jwt_key(self, token: str):
        """Safely set the JWT key after fetching it."""
        self.jwt_key = SecretStr(token)
    
    def load_registry_public_key(self) -> str:
        """
        Load Registry's public key from settings.
        Per SECURITY_REQUIREMENTS.md - never hardcode keys.
        
        Handles escaped newlines in environment variables (\\n -> \n)
        and fixes common PEM formatting issues.
        """
        key = self.registry_public_key.get_secret_value()
        # Replace escaped newlines with actual newlines
        # This handles cases where the key is stored in env vars with \\n
        key = key.replace('\\n', '\n')
        
        # Fix malformed PEM headers (e.g., "-----BEGIN PUBLIC KEY---- -" -> "-----BEGIN PUBLIC KEY-----")
        key = key.replace('-----BEGIN PUBLIC KEY---- -', '-----BEGIN PUBLIC KEY-----')
        key = key.replace('-----BEGIN PUBLIC KEY----\n-', '-----BEGIN PUBLIC KEY-----\n')
        key = key.replace('-----END PUBLIC KEY---- -', '-----END PUBLIC KEY-----')
        key = key.replace('-----END PUBLIC KEY----\n-', '-----END PUBLIC KEY-----\n')
        
        # Ensure proper line endings
        key = key.strip()
        if not key.endswith('\n'):
            key += '\n'
        
        return key
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()