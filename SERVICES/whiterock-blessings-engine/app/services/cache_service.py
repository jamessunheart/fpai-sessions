"""
WhiteRock Blessings Engine - Cache Service
Redis-based caching for frequently accessed data.
"""

import json
from typing import Optional, Any, TypeVar, Callable
from datetime import datetime
import asyncio

from app.config import settings

T = TypeVar('T')

# Try to import aioredis, fallback to in-memory cache
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """
    Async Redis caching service with fallback to in-memory cache.
    """
    
    def __init__(self):
        self._redis: Optional[Any] = None
        self._memory_cache: dict = {}
        self._memory_expiry: dict = {}
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if self._initialized:
            return self._redis is not None
        
        self._initialized = True
        
        if not REDIS_AVAILABLE:
            print("[CACHE] Redis library not available, using in-memory cache")
            return False
        
        try:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self._redis.ping()
            print("[CACHE] Redis connection established")
            return True
        except Exception as e:
            print(f"[CACHE] Redis connection failed: {e}, using in-memory cache")
            self._redis = None
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception:
                pass
        
        # In-memory fallback
        if key in self._memory_cache:
            expiry = self._memory_expiry.get(key)
            if expiry and datetime.utcnow().timestamp() > expiry:
                del self._memory_cache[key]
                del self._memory_expiry[key]
                return None
            return self._memory_cache[key]
        
        return None
    
    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set a value in cache with TTL in seconds."""
        if self._redis:
            try:
                await self._redis.setex(key, ttl, value)
                return True
            except Exception:
                pass
        
        # In-memory fallback
        self._memory_cache[key] = value
        self._memory_expiry[key] = datetime.utcnow().timestamp() + ttl
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if self._redis:
            try:
                await self._redis.delete(key)
                return True
            except Exception:
                pass
        
        # In-memory fallback
        self._memory_cache.pop(key, None)
        self._memory_expiry.pop(key, None)
        return True
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON-serialized value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set a JSON-serializable value in cache."""
        try:
            serialized = json.dumps(value, default=str)
            return await self.set(key, serialized, ttl)
        except (TypeError, ValueError):
            return False
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: int = 300
    ) -> Any:
        """
        Get value from cache or compute and cache it.
        
        Args:
            key: Cache key
            factory: Async function to compute value if not cached
            ttl: Time-to-live in seconds
        """
        cached = await self.get_json(key)
        if cached is not None:
            return cached
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Cache it
        await self.set_json(key, value, ttl)
        return value
    
    # Convenience methods for specific cache keys
    
    async def get_capacity(self) -> Optional[dict]:
        """Get cached community capacity."""
        return await self.get_json("whiterock:capacity")
    
    async def set_capacity(self, level: str, updated_at: str) -> bool:
        """Cache community capacity."""
        return await self.set_json(
            "whiterock:capacity",
            {"level": level, "updated_at": updated_at},
            settings.CACHE_TTL_CAPACITY
        )
    
    async def invalidate_capacity(self) -> bool:
        """Invalidate capacity cache."""
        return await self.delete("whiterock:capacity")
    
    async def get_tiers(self) -> Optional[list]:
        """Get cached membership tiers."""
        return await self.get_json("whiterock:tiers")
    
    async def set_tiers(self, tiers: list) -> bool:
        """Cache membership tiers."""
        return await self.set_json(
            "whiterock:tiers",
            tiers,
            settings.CACHE_TTL_TIERS
        )
    
    async def get_current_disclosure(self) -> Optional[dict]:
        """Get cached current disclosure."""
        return await self.get_json("whiterock:disclosure:current")
    
    async def set_current_disclosure(self, disclosure: dict) -> bool:
        """Cache current disclosure."""
        return await self.set_json(
            "whiterock:disclosure:current",
            disclosure,
            settings.CACHE_TTL_DISCLOSURE
        )
    
    async def get_cora_stats(self) -> Optional[dict]:
        """Get cached CORA circulation stats."""
        return await self.get_json("whiterock:cora:stats")
    
    async def set_cora_stats(self, stats: dict) -> bool:
        """Cache CORA circulation stats."""
        return await self.set_json(
            "whiterock:cora:stats",
            stats,
            settings.CACHE_TTL_STATS
        )


# Singleton instance
cache = CacheService()


async def get_cache() -> CacheService:
    """FastAPI dependency to get cache service."""
    if not cache._initialized:
        await cache.initialize()
    return cache



