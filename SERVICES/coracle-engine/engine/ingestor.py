"""
Coracle Signal Ingestor
========================
Fetches raw signal data from WhaleTrack API, Hyperliquid, and other sources.
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class SignalIngestor:
    """
    Ingests raw signals from multiple data sources.
    
    Data Sources:
    - WhaleTrack API: Coinglass data (funding, OI, liquidations, L/S ratio)
    - Hyperliquid: Real-time prices, trades, orderbook
    - Alternative.me: Fear & Greed Index
    - CoinGecko: Spot prices for premium calculation
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.whaletrack_url = settings.whaletrack_url
        self.hyperliquid_url = settings.hyperliquid_url
        
        # Cache for expensive calls
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._cache_ttl = {
            "whaletrack": 30,  # 30 seconds
            "orderbook": 5,   # 5 seconds
            "trades": 2,      # 2 seconds
            "fgi": 300        # 5 minutes
        }
    
    async def gather_signals(self, symbol: str) -> Dict[str, Any]:
        """
        Gather all available signals for a symbol.
        
        Returns raw signal data to be processed by SignalProcessor.
        """
        symbol = symbol.upper()
        
        # Parallel fetch from all sources
        tasks = [
            self._fetch_whaletrack(symbol),
            self._fetch_hyperliquid_price(symbol),
            self._fetch_hyperliquid_orderbook(symbol),
            self._fetch_hyperliquid_trades(symbol),
            self._fetch_fear_greed()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        whaletrack_data = results[0] if not isinstance(results[0], Exception) else {}
        price_data = results[1] if not isinstance(results[1], Exception) else {}
        orderbook_data = results[2] if not isinstance(results[2], Exception) else {}
        trades_data = results[3] if not isinstance(results[3], Exception) else {}
        fgi_data = results[4] if not isinstance(results[4], Exception) else {}
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": price_data.get("price", 0),
            "whaletrack": whaletrack_data,
            "orderbook": orderbook_data,
            "trades": trades_data,
            "fear_greed": fgi_data,
            "sources_available": {
                "whaletrack": bool(whaletrack_data),
                "hyperliquid_price": bool(price_data),
                "hyperliquid_orderbook": bool(orderbook_data),
                "hyperliquid_trades": bool(trades_data),
                "fear_greed": bool(fgi_data)
            }
        }
    
    async def _fetch_whaletrack(self, symbol: str) -> Dict[str, Any]:
        """Fetch signals from WhaleTrack Coracle API."""
        cache_key = f"whaletrack_{symbol}"
        cached = self._get_cached(cache_key, self._cache_ttl["whaletrack"])
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.whaletrack_url}/api/coracle/signals/{symbol}"
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    self._set_cache(cache_key, data)
                    return data
                else:
                    logger.warning(f"WhaleTrack API returned {resp.status_code}")
                    return {}
                    
        except Exception as e:
            logger.error(f"WhaleTrack fetch failed: {e}")
            return {}
    
    async def _fetch_hyperliquid_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch current price from Hyperliquid."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.hyperliquid_url,
                    json={"type": "allMids"}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    price = float(data.get(symbol, 0))
                    return {"price": price, "source": "hyperliquid"}
                    
        except Exception as e:
            logger.error(f"Hyperliquid price fetch failed: {e}")
        
        return {}
    
    async def _fetch_hyperliquid_orderbook(self, symbol: str) -> Dict[str, Any]:
        """Fetch L2 orderbook from Hyperliquid for BAI/OBS calculation."""
        cache_key = f"orderbook_{symbol}"
        cached = self._get_cached(cache_key, self._cache_ttl["orderbook"])
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.hyperliquid_url,
                    json={"type": "l2Book", "coin": symbol}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Process orderbook for BAI/OBS signals
                    levels = data.get("levels", [[], []])
                    bids = levels[0] if len(levels) > 0 else []
                    asks = levels[1] if len(levels) > 1 else []
                    
                    # Calculate bid/ask volumes
                    bid_volume = sum(float(b.get("sz", 0)) for b in bids[:20])
                    ask_volume = sum(float(a.get("sz", 0)) for a in asks[:20])
                    
                    # Calculate imbalance
                    total = bid_volume + ask_volume
                    imbalance = (bid_volume - ask_volume) / total if total > 0 else 0
                    
                    # Calculate slope (depth distribution)
                    bid_slope = self._calculate_slope(bids[:20])
                    ask_slope = self._calculate_slope(asks[:20])
                    
                    result = {
                        "bids": bids[:20],
                        "asks": asks[:20],
                        "bid_volume": bid_volume,
                        "ask_volume": ask_volume,
                        "imbalance": imbalance,
                        "bid_slope": bid_slope,
                        "ask_slope": ask_slope,
                        "source": "hyperliquid"
                    }
                    
                    self._set_cache(cache_key, result)
                    return result
                    
        except Exception as e:
            logger.error(f"Hyperliquid orderbook fetch failed: {e}")
        
        return {}
    
    async def _fetch_hyperliquid_trades(self, symbol: str) -> Dict[str, Any]:
        """Fetch recent trades for CVD and whale detection."""
        cache_key = f"trades_{symbol}"
        cached = self._get_cached(cache_key, self._cache_ttl["trades"])
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.hyperliquid_url,
                    json={"type": "recentTrades", "coin": symbol}
                )
                
                if resp.status_code == 200:
                    trades = resp.json()
                    
                    if not trades:
                        return {}
                    
                    # Analyze trades
                    buy_volume = 0
                    sell_volume = 0
                    large_trades = []  # > $100k for whale detection
                    
                    for t in trades:
                        size = float(t.get("sz", 0))
                        price = float(t.get("px", 0))
                        value = size * price
                        side = t.get("side", "").upper()
                        
                        if side == "B":
                            buy_volume += value
                        else:
                            sell_volume += value
                        
                        # Whale threshold: $100k+
                        if value >= 100000:
                            large_trades.append({
                                "size": size,
                                "price": price,
                                "value": value,
                                "side": "buy" if side == "B" else "sell",
                                "time": t.get("time")
                            })
                    
                    # CVD calculation
                    total_volume = buy_volume + sell_volume
                    cvd = buy_volume - sell_volume
                    cvd_ratio = cvd / total_volume if total_volume > 0 else 0
                    
                    result = {
                        "trade_count": len(trades),
                        "buy_volume": buy_volume,
                        "sell_volume": sell_volume,
                        "total_volume": total_volume,
                        "cvd": cvd,
                        "cvd_ratio": cvd_ratio,
                        "large_trades": large_trades,
                        "whale_buy_volume": sum(t["value"] for t in large_trades if t["side"] == "buy"),
                        "whale_sell_volume": sum(t["value"] for t in large_trades if t["side"] == "sell"),
                        "source": "hyperliquid"
                    }
                    
                    self._set_cache(cache_key, result)
                    return result
                    
        except Exception as e:
            logger.error(f"Hyperliquid trades fetch failed: {e}")
        
        return {}
    
    async def _fetch_fear_greed(self) -> Dict[str, Any]:
        """Fetch Fear & Greed Index from Alternative.me."""
        cache_key = "fgi"
        cached = self._get_cached(cache_key, self._cache_ttl["fgi"])
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("https://api.alternative.me/fng/")
                
                if resp.status_code == 200:
                    data = resp.json()
                    fng = data.get("data", [{}])[0]
                    
                    result = {
                        "value": int(fng.get("value", 50)),
                        "classification": fng.get("value_classification", "Neutral"),
                        "timestamp": fng.get("timestamp"),
                        "source": "alternative.me"
                    }
                    
                    self._set_cache(cache_key, result)
                    return result
                    
        except Exception as e:
            logger.error(f"Fear & Greed fetch failed: {e}")
        
        return {"value": 50, "classification": "Neutral", "source": "default"}
    
    def _calculate_slope(self, levels: List[Dict]) -> float:
        """
        Calculate orderbook slope (depth distribution).
        
        A steep slope means liquidity is concentrated near best price.
        A flat slope means liquidity is spread across levels.
        """
        if len(levels) < 2:
            return 0
        
        volumes = [float(l.get("sz", 0)) for l in levels]
        if not volumes or sum(volumes) == 0:
            return 0
        
        # Calculate cumulative distribution
        total = sum(volumes)
        cumsum = 0
        weighted_depth = 0
        
        for i, vol in enumerate(volumes):
            cumsum += vol
            weighted_depth += (i + 1) * vol
        
        # Normalize: 1 = all at best, 0 = evenly spread
        max_weighted = len(volumes) * total
        slope = 1 - (weighted_depth / max_weighted) if max_weighted > 0 else 0
        
        return slope
    
    def _get_cached(self, key: str, ttl: float) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if datetime.now(timezone.utc).timestamp() - timestamp < ttl:
                return value
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set cache value with timestamp."""
        self._cache[key] = (datetime.now(timezone.utc).timestamp(), value)


