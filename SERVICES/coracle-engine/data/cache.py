"""
Coracle Signal Cache
=====================
Redis-based caching for high-frequency signal data.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import json
import logging

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.config import get_settings

logger = logging.getLogger(__name__)


class SignalCache:
    """
    Redis cache for signal data.
    
    TTL Tiers:
    - Fast signals (BAI, OBS): 100ms
    - Medium signals (WADI, FR): 60s
    - Slow signals (FGI): 300s
    """
    
    # TTL in seconds for each signal tier
    TTL_FAST = 1  # 1 second (Redis doesn't do sub-second)
    TTL_MEDIUM = 60  # 1 minute
    TTL_SLOW = 300  # 5 minutes
    
    def __init__(self, redis_url: str = None):
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.client: Optional[aioredis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - caching disabled")
            return
        
        try:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            self._connected = True
            logger.info("Redis cache connected")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} - using in-memory cache")
            self._connected = False
            self._memory_cache: Dict[str, tuple] = {}
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self.client = None
            self._connected = False
    
    def _get_key(self, symbol: str, signal_type: str) -> str:
        """Generate cache key."""
        return f"coracle:signal:{symbol}:{signal_type}"
    
    def _get_ttl(self, signal_type: str) -> int:
        """Get TTL for signal type."""
        fast_signals = {"bai", "obs", "cvd"}
        medium_signals = {"wadi", "fr", "oi", "lcp", "wc"}
        
        if signal_type.lower() in fast_signals:
            return self.TTL_FAST
        elif signal_type.lower() in medium_signals:
            return self.TTL_MEDIUM
        else:
            return self.TTL_SLOW
    
    async def get(self, symbol: str, signal_type: str) -> Optional[Dict]:
        """Get cached signal."""
        key = self._get_key(symbol, signal_type)
        
        if self._connected and self.client:
            try:
                data = await self.client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")
        
        elif hasattr(self, "_memory_cache"):
            # Fallback to memory cache
            if key in self._memory_cache:
                timestamp, data = self._memory_cache[key]
                ttl = self._get_ttl(signal_type)
                if datetime.now(timezone.utc).timestamp() - timestamp < ttl:
                    return data
        
        return None
    
    async def set(self, symbol: str, signal_type: str, data: Dict):
        """Set cached signal."""
        key = self._get_key(symbol, signal_type)
        ttl = self._get_ttl(signal_type)
        
        if self._connected and self.client:
            try:
                await self.client.setex(key, ttl, json.dumps(data))
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")
        
        elif hasattr(self, "_memory_cache"):
            self._memory_cache[key] = (datetime.now(timezone.utc).timestamp(), data)
    
    async def get_all_signals(self, symbol: str) -> Dict[str, Any]:
        """Get all cached signals for a symbol."""
        signals = {}
        signal_types = ["bai", "obs", "cvd", "wadi", "fr", "oi", "lcp", "wc", "fgi", "vrc"]
        
        for sig_type in signal_types:
            data = await self.get(symbol, sig_type)
            if data:
                signals[sig_type] = data
        
        return signals
    
    async def set_snapshot(self, symbol: str, snapshot: Dict):
        """Set complete signal snapshot."""
        key = f"coracle:snapshot:{symbol}"
        
        if self._connected and self.client:
            try:
                await self.client.setex(key, self.TTL_MEDIUM, json.dumps(snapshot))
            except Exception as e:
                logger.warning(f"Snapshot cache failed: {e}")
    
    async def get_snapshot(self, symbol: str) -> Optional[Dict]:
        """Get cached signal snapshot."""
        key = f"coracle:snapshot:{symbol}"
        
        if self._connected and self.client:
            try:
                data = await self.client.get(key)
                if data:
                    return json.loads(data)
            except Exception:
                pass
        
        return None
    
    async def invalidate(self, symbol: str, signal_type: Optional[str] = None):
        """Invalidate cached signal(s)."""
        if signal_type:
            key = self._get_key(symbol, signal_type)
            if self._connected and self.client:
                await self.client.delete(key)
            elif hasattr(self, "_memory_cache") and key in self._memory_cache:
                del self._memory_cache[key]
        else:
            # Invalidate all signals for symbol
            if self._connected and self.client:
                keys = await self.client.keys(f"coracle:signal:{symbol}:*")
                if keys:
                    await self.client.delete(*keys)


