"""Configuration for Helper Management"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service
    service_name: str = "helper-management"
    service_port: int = 8026
    droplet_id: int = 26

    # Database
    database_url: str = "postgresql+asyncpg://fpai:password@localhost/helpers"

    # Credentials Manager
    credentials_manager_url: str = "http://localhost:8025"
    credentials_manager_token: str = ""

    # Job Platforms
    upwork_api_key: str = ""
    upwork_api_secret: str = ""

    # Crypto Payments
    crypto_wallet_address: str = ""
    crypto_private_key: str = ""
    web3_provider_url: str = "https://mainnet.infura.io/v3/YOUR_KEY"

    # AI Screening
    anthropic_api_key: str = ""

    # Payment Methods
    enable_crypto_payments: bool = True
    enable_upwork_payments: bool = True
    default_payment_method: str = "crypto"

    # Task Management
    auto_assign_tasks: bool = True
    auto_pay_on_completion: bool = True
    max_task_duration_hours: int = 48

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
