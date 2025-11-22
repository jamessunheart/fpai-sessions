"""Configuration for Credentials Manager"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service
    service_name: str = "credentials-manager"
    service_port: int = 8025
    droplet_id: int = 25

    # Database
    database_url: str = "postgresql+asyncpg://fpai:password@localhost/credentials"

    # Security - CRITICAL: Change these in production
    master_encryption_key: str  # Must be 32 bytes hex
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 24

    # Admin
    admin_username: str = "admin"
    admin_password_hash: str  # bcrypt hash

    # Features
    enable_audit_log: bool = True
    auto_revoke_hours: int = 24
    max_access_attempts: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
