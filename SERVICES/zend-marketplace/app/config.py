"""
Configuration for zend-marketplace P2P service.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    service_name: str = "zend-marketplace"
    service_version: str = "1.0.0"
    service_port: int = int(os.getenv("PORT", "8584"))

    # Connected services
    zend_wallet_url: str = os.getenv("ZEND_WALLET_URL", "http://localhost:8580")
    zend_ton_url: str = os.getenv("ZEND_TON_URL", "http://localhost:8583")
    credits_gateway_url: str = os.getenv("CREDITS_GATEWAY_URL", "http://localhost:8765")
    credits_api_key: Optional[str] = os.getenv("CREDITS_API_KEY")

    # Escrow account for P2P trades
    marketplace_escrow_account: str = os.getenv("MARKETPLACE_ESCROW_ACCOUNT", "system:marketplace_escrow")

    # Trade settings
    default_rate: float = 1.0  # 1 UC = $1 USD
    order_expiry_hours: int = int(os.getenv("ORDER_EXPIRY_HOURS", "24"))
    trade_timeout_hours: int = int(os.getenv("TRADE_TIMEOUT_HOURS", "1"))
    min_trade_uc: float = float(os.getenv("MIN_TRADE_UC", "10"))
    max_trade_uc: float = float(os.getenv("MAX_TRADE_UC", "10000"))

    # Liquidity provider settings
    lp_auto_match_max_uc: float = float(os.getenv("LP_AUTO_MATCH_MAX_UC", "500"))

    # Persistence
    data_dir: Path = Path(os.getenv("MARKETPLACE_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data")))
    db_path: Optional[Path] = None

    def model_post_init(self, __context) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        env_db_path = os.getenv("MARKETPLACE_DB_PATH")
        if env_db_path:
            self.db_path = Path(env_db_path)
        if self.db_path is None:
            self.db_path = self.data_dir / "marketplace.db"


settings = Settings()




