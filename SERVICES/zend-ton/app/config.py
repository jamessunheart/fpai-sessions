"""
Configuration for zend-ton service.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class Settings(BaseModel):
    service_name: str = "zend-ton"
    service_version: str = "1.0.0"
    service_port: int = int(os.getenv("PORT", "8583"))

    # TON Network
    ton_network: str = os.getenv("TON_NETWORK", "mainnet")  # mainnet | testnet
    ton_api_key: Optional[str] = os.getenv("TON_API_KEY")
    ton_rpc_url: str = os.getenv(
        "TON_RPC_URL",
        "https://toncenter.com/api/v2/jsonRPC"
    )

    # USDT Jetton contract on TON mainnet
    usdt_jetton_master: str = os.getenv(
        "USDT_JETTON_MASTER",
        "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"
    )

    # TON Connect manifest (for bot integration)
    ton_connect_manifest_url: str = os.getenv(
        "TON_CONNECT_MANIFEST_URL",
        "https://fullpotential.ai/tonconnect-manifest.json"
    )

    # Persistence
    data_dir: Path = Path(os.getenv("ZEND_TON_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data")))
    db_path: Optional[Path] = None

    # Zend services
    zend_wallet_url: str = os.getenv("ZEND_WALLET_URL", "http://localhost:8580")
    zend_marketplace_url: str = os.getenv("ZEND_MARKETPLACE_URL", "http://localhost:8584")

    def model_post_init(self, __context) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        env_db_path = os.getenv("ZEND_TON_DB_PATH")
        if env_db_path:
            self.db_path = Path(env_db_path)
        if self.db_path is None:
            self.db_path = self.data_dir / "zend_ton.db"


settings = Settings()




