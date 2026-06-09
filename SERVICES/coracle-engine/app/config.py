"""
Coracle Prediction Engine - Configuration
==========================================
Central configuration for all engine parameters.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    service_name: str = "coracle-engine"
    port: int = Field(default=8650, alias="CORACLE_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Data Sources
    whaletrack_url: str = Field(default="http://localhost:8600", alias="WHALETRACK_URL")
    hyperliquid_url: str = Field(default="https://api.hyperliquid.xyz/info", alias="HYPERLIQUID_URL")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/coracle",
        alias="DATABASE_URL"
    )
    
    # Redis Cache
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    # External APIs (optional)
    glassnode_api_key: Optional[str] = Field(default=None, alias="GLASSNODE_API_KEY")
    deribit_api_key: Optional[str] = Field(default=None, alias="DERIBIT_API_KEY")
    coinglass_api_key: Optional[str] = Field(default=None, alias="COIN_GLASS_API_KEY")
    
    # Signal Processing
    fast_signal_ttl_ms: int = 100  # Fast-path signals (BAI, OBS)
    medium_signal_ttl_s: int = 60  # Medium-path signals (WADI, FR)
    slow_signal_ttl_s: int = 3600  # Slow-path signals (FGI, regime)
    
    # Trading Assets
    tracked_assets: list[str] = ["BTC", "ETH", "XRP", "SOL"]
    
    # Sacred Gate Thresholds
    whale_threshold: float = 0.4  # WADI threshold for whale key
    liquidity_threshold: float = 2.5  # LCP threshold for liquidity key
    
    # Confluence Weights (from spec)
    weight_liquidity: float = 0.35
    weight_whale: float = 0.25
    weight_derivatives: float = 0.20
    weight_funding: float = 0.15
    weight_onchain: float = 0.10
    weight_technical: float = 0.10
    weight_sentiment: float = 0.05
    
    # Risk Management
    volatility_regimes: dict = {
        "LOW": 0.008,      # 0.8% base SL
        "NORMAL": 0.012,   # 1.2% base SL
        "HIGH": 0.018,     # 1.8% base SL
        "EXTREME": 0.025   # 2.5% base SL
    }
    
    # Take Profit Configuration
    tp1_size: float = 0.30  # 30% position
    tp2_size: float = 0.40  # 40% position
    tp3_size: float = 0.30  # 30% position
    tp1_rr: float = 1.0     # 1:1 R:R
    tp2_rr: float = 1.5     # 1.5:1 R:R
    tp3_rr: float = 2.5     # 2.5:1 R:R
    
    # Probability Decay per TP Level
    tp_probability_decay: dict = {
        "TP1": 1.0,
        "TP2": 0.85,
        "TP3": 0.65
    }
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Signal tier definitions
SIGNAL_TIERS = {
    "LIQUIDITY": {
        "weight": 0.35,
        "signals": ["BAI", "SDS", "BAR", "OBS", "LV", "LCP"],
        "update_frequency": "100ms-1min"
    },
    "WHALE": {
        "weight": 0.25,
        "signals": ["WADI", "WC", "SD", "ENF", "SFR"],
        "update_frequency": "1-5min"
    },
    "DERIVATIVES": {
        "weight": 0.20,
        "signals": ["GEX", "OID", "PCR", "CVD", "MP"],
        "update_frequency": "15min-1h"
    },
    "FUNDING": {
        "weight": 0.15,
        "signals": ["FR", "FRM", "CEFS", "FW"],
        "update_frequency": "1-8h"
    },
    "ON_CHAIN": {
        "weight": 0.10,
        "signals": ["SOPR", "MVRV", "NUPL", "DF"],
        "update_frequency": "1-24h"
    },
    "TECHNICAL": {
        "weight": 0.10,
        "signals": ["MS", "BOS", "VRC", "HHL"],
        "update_frequency": "1-60min"
    },
    "SENTIMENT": {
        "weight": 0.05,
        "signals": ["FGI", "BTCD"],
        "update_frequency": "1-24h"
    }
}

# Contract grade thresholds
GRADE_THRESHOLDS = {
    "A": 0.75,  # 75%+ confluence score
    "B": 0.60,  # 60-75%
    "C": 0.45,  # 45-60%
    "D": 0.30   # 30-45%
}


