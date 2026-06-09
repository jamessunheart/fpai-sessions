"""Configuration for Zend Payments service.

Canonical Spec: docs/protocols/ZEND_REGENERATIVE_SPEC.md (v2.0)
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "zend-payments"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8581
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./zend_payments.db"

    # Credits Gateway
    CREDITS_GATEWAY_URL: str = "http://localhost:8765"
    CREDITS_API_KEY: Optional[str] = None

    # Zend Wallet
    ZEND_WALLET_URL: str = "http://localhost:8580"

    # ==========================================================
    # SETTLEMENT RAILS
    # ==========================================================

    # Stripe (default rail for ubiquity)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_ENABLED: bool = True

    # Solana USDC (fast settlement, non-custodial)
    SOLANA_RPC_URL: str = "https://api.mainnet-beta.solana.com"
    SOLANA_ENABLED: bool = True
    SOLANA_USDC_MINT: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # Mainnet USDC

    # ==========================================================
    # ZENDLINK CONFIGURATION
    # ==========================================================
    
    ZENDLINK_BASE_URL: str = "https://zend.to"
    ZENDLINK_EXPIRY_HOURS: int = 72  # 3 days default

    # ==========================================================
    # GUARDRAILS (per ZEND_REGENERATIVE_SPEC.md Part 9)
    # ==========================================================
    
    MAX_INTENT_AMOUNT: float = 10000.0  # Max single payment intent
    MAX_DAILY_MERCHANT: float = 100000.0  # Max daily per merchant
    INTENT_EXPIRY_MINUTES: int = 30  # Payment intent expiry

    # ==========================================================
    # COMMONS CONTRIBUTION
    # ==========================================================
    
    DEFAULT_COMMONS_CONTRIBUTION_PCT: float = 0.0  # 0% default, opt-in
    MAX_COMMONS_CONTRIBUTION_PCT: float = 5.0  # 5% max per spec

    class Config:
        env_prefix = "ZEND_PAYMENTS_"
        env_file = ".env"


settings = Settings()




