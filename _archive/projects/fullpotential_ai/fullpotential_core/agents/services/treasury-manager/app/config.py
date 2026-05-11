"""
Configuration for Autonomous Treasury Manager
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Autonomous Treasury Manager"
    version: str = "0.1.0"
    environment: str = "development"  # development, staging, production
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8003
    reload: bool = True

    # API Keys - Market Data
    coingecko_api_key: Optional[str] = None  # Free tier works
    coinmarketcap_api_key: Optional[str] = None  # Required for Fear/Greed
    glassnode_api_key: Optional[str] = None  # Optional ($500/mo)
    coinglass_api_key: Optional[str] = None  # Free tier works
    deribit_api_key: Optional[str] = None  # Free for market data

    # AI
    anthropic_api_key: str  # Required

    # Blockchain RPC
    ethereum_rpc_url: str = "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"
    arbitrum_rpc_url: str = "https://arb-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY"
    polygon_rpc_url: str = "https://polygon-rpc.com"

    # Wallet (NEVER COMMIT THESE - USE ENV VARS!)
    treasury_wallet_private_key: Optional[str] = None  # For automated transactions
    treasury_wallet_address: Optional[str] = None

    # Database
    database_url: str = "postgresql://user:password@localhost/treasury_manager"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Risk Parameters
    max_volatile_allocation: float = 0.40  # 40% max in BTC/ETH
    max_position_size: float = 0.25  # 25% max in any single position
    min_protocol_tvl: float = 1_000_000_000  # $1B minimum TVL
    max_gas_price_gwei: int = 100  # Don't transact if gas > 100 gwei

    # Rebalancing Thresholds
    rebalance_drift_threshold: float = 0.05  # Rebalance if >5% drift
    min_rebalance_interval_hours: int = 24  # Don't rebalance more than daily

    # Alert Thresholds
    alert_email: Optional[str] = None
    alert_telegram_token: Optional[str] = None
    alert_telegram_chat_id: Optional[str] = None

    # MVRV Thresholds (from strategy)
    mvrv_sell_25_percent: float = 3.5
    mvrv_sell_50_percent: float = 5.0
    mvrv_sell_67_percent: float = 7.0
    mvrv_exit_all: float = 9.0

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/treasury_manager.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
