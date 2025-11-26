#!/usr/bin/env python3
"""
🐋 WhaleTrack Bridge Service

Bridges live exchange data into the WhaleTrack Magnet Engine and echoes signals
back as paper trades (or real executions later).

Features:
- Fetch latest OHLCV candles from Binance (via CCXT)
- Push candles to WhaleTrack (`/api/whale/update`)
- Poll entry/exit signals and log simulated trades
- Designed for 1-minute cadence (adjustable)

Usage:
    pip install -r bridge/requirements.txt
    python bridge/bridge_service.py
"""
import os
import time
import json
import logging
from pathlib import Path
from typing import List, Dict

import ccxt  # type: ignore
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRIDGE] %(levelname)s - %(message)s",
)
logger = logging.getLogger("whaletrack-bridge")

# ---------------------------------------------------------------------------
# Configuration (env overrides available)
# ---------------------------------------------------------------------------
API_BASE = os.getenv("WHALETRACK_API_BASE", "http://localhost:8600")
EXCHANGE_ID = os.getenv("BRIDGE_EXCHANGE", "binance")
SYMBOL = os.getenv("BRIDGE_SYMBOL", "BTC/USDT")
TIMEFRAME = os.getenv("BRIDGE_TIMEFRAME", "1m")
CANDLE_BATCH = int(os.getenv("BRIDGE_CANDLES", "50"))
SLEEP_SECS = int(os.getenv("BRIDGE_INTERVAL", "60"))
TRADING_MODE = os.getenv("BRIDGE_MODE", "paper").lower()  # paper | live
PAPER_LOG = Path(os.getenv("BRIDGE_PAPER_LOG", "bridge/paper_trades.json"))


def ensure_log():
    PAPER_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not PAPER_LOG.exists():
        PAPER_LOG.write_text("[]")


def fetch_candles(exchange, since=None) -> List[Dict]:
    """
    Fetch candles and convert them into WhaleTrack payload shape.
    """
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=CANDLE_BATCH, since=since)
    candles = []
    for ts, op, high, low, close, vol in ohlcv:
        candles.append(
            {
                "timestamp": ts / 1000,  # convert ms -> s
                "open": op,
                "high": high,
                "low": low,
                "close": close,
                "volume": vol,
            }
        )
    return candles


def push_candles(candles: List[Dict]):
    url = f"{API_BASE}/api/whale/update"
    resp = requests.post(url, json=candles, timeout=10)
    resp.raise_for_status()
    return resp.json()


def poll_entry_signal():
    resp = requests.get(f"{API_BASE}/api/signals/entry", timeout=5)
    resp.raise_for_status()
    return resp.json()


def poll_exit_signal():
    resp = requests.get(f"{API_BASE}/api/signals/exit", timeout=5)
    resp.raise_for_status()
    return resp.json()


def log_paper_trade(event: Dict):
    ensure_log()
    data = json.loads(PAPER_LOG.read_text())
    data.append(event)
    PAPER_LOG.write_text(json.dumps(data, indent=2))


def handle_entry(signal: Dict):
    if not signal.get("active"):
        return

    logger.info(
        "ENTRY SIGNAL -> type=%s entry=%.2f stop=%.2f target=%.2f RR=%.2f conf=%.1f",
        signal.get("entry_type"),
        signal.get("entry_price"),
        signal.get("stop_loss"),
        signal.get("target_price"),
        signal.get("risk_reward"),
        signal.get("confidence"),
    )

    if TRADING_MODE == "paper":
        log_paper_trade(
            {
                "mode": "ENTRY",
                "timestamp": time.time(),
                "symbol": SYMBOL,
                "details": signal,
            }
        )
    else:
        logger.warning("LIVE trading not implemented yet. Skipping execution.")


def handle_exit(signal: Dict):
    if not signal.get("active"):
        return

    logger.info(
        "EXIT SIGNAL -> type=%s price=%.2f reason=%s",
        signal.get("exit_type"),
        signal.get("exit_price"),
        signal.get("reason"),
    )

    if TRADING_MODE == "paper":
        log_paper_trade(
            {
                "mode": "EXIT",
                "timestamp": time.time(),
                "symbol": SYMBOL,
                "details": signal,
            }
        )
    else:
        logger.warning("LIVE trading not implemented yet. Skipping execution.")


def bridge_loop():
    exchange_class = getattr(ccxt, EXCHANGE_ID)
    exchange = exchange_class({"enableRateLimit": True})
    logger.info("Bridge started: %s %s timeframe=%s mode=%s", EXCHANGE_ID, SYMBOL, TIMEFRAME, TRADING_MODE)

    while True:
        try:
            candles = fetch_candles(exchange)
            if len(candles) < 5:
                logger.warning("Not enough candles fetched, skipping cycle.")
            else:
                push_candles(candles)
                handle_entry(poll_entry_signal())
                handle_exit(poll_exit_signal())
        except Exception as exc:
            logger.exception("Bridge cycle failed: %s", exc)

        time.sleep(SLEEP_SECS)


if __name__ == "__main__":
    bridge_loop()

