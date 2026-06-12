#!/usr/bin/env python3
"""
📂 HISTORICAL DATA MANAGER
============================

Manages historical price data for backtesting.

Features:
- Fetch data from Hyperliquid API
- Local SQLite caching for fast access
- Automatic gap filling
"""

import asyncio
import sqlite3
import logging
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

import aiohttp

logger = logging.getLogger("aria.trading.backtest.data")

# Data directory
DATA_DIR = Path("/opt/fpai/aria-command/data/backtest")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "historical_data.db"


@dataclass
class OHLCV:
    """OHLCV candlestick data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OHLCV":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data["volume"])
        )


class HistoricalDataManager:
    """
    Manages historical price data for backtesting.
    
    Data sources:
    - Hyperliquid historical API
    - Local cache (SQLite)
    """
    
    def __init__(self):
        self._db_path = DB_PATH
        self._init_db()
        
        # Hyperliquid API
        self._api_url = "https://api.hyperliquid.xyz/info"
        
        # Interval mapping (to milliseconds)
        self._interval_ms = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000
        }
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    symbol TEXT,
                    interval TEXT,
                    timestamp INTEGER,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (symbol, interval, timestamp)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candles_lookup
                ON candles(symbol, interval, timestamp)
            """)
    
    async def fetch_historical(
        self,
        symbol: str,
        interval: str = "15m",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[OHLCV]:
        """
        Fetch historical candles.
        
        Args:
            symbol: Trading symbol (e.g., "SOL", "BTC")
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            start: Start datetime
            end: End datetime
            limit: Maximum candles to fetch
            
        Returns:
            List of OHLCV candles
        """
        # Default to last 30 days
        if end is None:
            end = datetime.now()
        if start is None:
            start = end - timedelta(days=30)
        
        # First check cache
        cached = self.get_cached(symbol, interval, start, end)
        if len(cached) > 0:
            # Check if we have complete data
            expected_candles = self._expected_candles(start, end, interval)
            if len(cached) >= expected_candles * 0.95:  # 95% complete
                logger.info(f"📂 Using cached data for {symbol} ({len(cached)} candles)")
                return cached
        
        # Fetch from API
        logger.info(f"🌐 Fetching {symbol} {interval} data from API...")
        
        candles = await self._fetch_from_api(symbol, interval, start, end, limit)
        
        if candles:
            # Cache the data
            self.cache_data(symbol, interval, candles)
            logger.info(f"💾 Cached {len(candles)} candles for {symbol}")
        
        return candles
    
    def _expected_candles(self, start: datetime, end: datetime, interval: str) -> int:
        """Calculate expected number of candles."""
        duration_ms = (end - start).total_seconds() * 1000
        interval_ms = self._interval_ms.get(interval, 60000)
        return int(duration_ms / interval_ms)
    
    async def _fetch_from_api(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: int
    ) -> List[OHLCV]:
        """Fetch data from Hyperliquid API."""
        candles = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Convert to milliseconds
                start_ms = int(start.timestamp() * 1000)
                end_ms = int(end.timestamp() * 1000)
                
                payload = {
                    "type": "candleSnapshot",
                    "req": {
                        "coin": symbol,
                        "interval": interval,
                        "startTime": start_ms,
                        "endTime": end_ms
                    }
                }
                
                async with session.post(self._api_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for candle in data:
                            candles.append(OHLCV(
                                timestamp=datetime.fromtimestamp(candle["t"] / 1000),
                                open=float(candle["o"]),
                                high=float(candle["h"]),
                                low=float(candle["l"]),
                                close=float(candle["c"]),
                                volume=float(candle["v"])
                            ))
                    else:
                        logger.error(f"API error: {resp.status}")
        
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
        
        return sorted(candles, key=lambda c: c.timestamp)
    
    def cache_data(self, symbol: str, interval: str, candles: List[OHLCV]):
        """Cache candles to SQLite."""
        if not candles:
            return
        
        with sqlite3.connect(self._db_path) as conn:
            for candle in candles:
                conn.execute("""
                    INSERT OR REPLACE INTO candles
                    (symbol, interval, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    interval,
                    int(candle.timestamp.timestamp() * 1000),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume
                ))
    
    def get_cached(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> List[OHLCV]:
        """Get cached candles from SQLite."""
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE symbol = ? AND interval = ?
                AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            """, (symbol, interval, start_ms, end_ms))
            
            candles = []
            for row in cursor.fetchall():
                candles.append(OHLCV(
                    timestamp=datetime.fromtimestamp(row[0] / 1000),
                    open=row[1],
                    high=row[2],
                    low=row[3],
                    close=row[4],
                    volume=row[5]
                ))
            
            return candles
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol, interval, COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM candles
                GROUP BY symbol, interval
            """)
            
            stats = {}
            for row in cursor.fetchall():
                key = f"{row[0]}_{row[1]}"
                stats[key] = {
                    "symbol": row[0],
                    "interval": row[1],
                    "candles": row[2],
                    "start": datetime.fromtimestamp(row[3] / 1000).isoformat() if row[3] else None,
                    "end": datetime.fromtimestamp(row[4] / 1000).isoformat() if row[4] else None
                }
            
            return stats
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached data."""
        with sqlite3.connect(self._db_path) as conn:
            if symbol:
                conn.execute("DELETE FROM candles WHERE symbol = ?", (symbol,))
            else:
                conn.execute("DELETE FROM candles")


# Singleton
_data_manager: Optional[HistoricalDataManager] = None


def get_data_manager() -> HistoricalDataManager:
    """Get or create global data manager."""
    global _data_manager
    if _data_manager is None:
        _data_manager = HistoricalDataManager()
    return _data_manager









