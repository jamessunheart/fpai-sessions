"""Configuration for Verifier Droplet."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""

    # Service
    verifier_port: int = 8200

    # Job management
    work_dir: Path = Path("/tmp/verifier-jobs")
    max_concurrent_jobs: int = 3
    job_timeout_seconds: int = 600  # 10 minutes

    # Verification settings
    quick_mode_enabled: bool = True
    test_timeout_seconds: int = 120  # 2 minutes for pytest
    startup_timeout_seconds: int = 30  # 30 seconds for droplet startup

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
