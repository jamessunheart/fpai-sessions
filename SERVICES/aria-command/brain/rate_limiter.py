"""
ARIA RATE LIMITER
==================

Prevents API lockouts through proactive rate limit tracking.

Features:
1. Tracks API calls per provider
2. Preemptive slowdown before hitting limits
3. Auto-switch to fallback before rate limited
4. Sliding window rate tracking

Known limits (requests per minute):
- Claude: ~50/min (varies by tier)
- OpenAI: ~60/min (varies by tier)
- Gemini: ~60/min
- Telegram: ~30/sec

This ensures Aria never gets locked out of her AI providers.
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Any, Callable, Awaitable, TypeVar, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import functools

logger = logging.getLogger("aria.brain.rate_limiter")

T = TypeVar('T')

# Configuration - requests per minute
RATE_LIMITS = {
    "claude": int(os.getenv("CLAUDE_RATE_LIMIT", "50")),
    "openai": int(os.getenv("OPENAI_RATE_LIMIT", "60")),
    "gemini": int(os.getenv("GEMINI_RATE_LIMIT", "60")),
    "telegram": int(os.getenv("TELEGRAM_RATE_LIMIT", "30")),  # Per second, so 1800/min
}

# Thresholds for preemptive action
WARN_THRESHOLD = 0.7  # 70% of limit
SLOWDOWN_THRESHOLD = 0.85  # 85% of limit - start adding delays
SWITCH_THRESHOLD = 0.95  # 95% of limit - switch to fallback


class RateLimitStatus(str, Enum):
    """Rate limit status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    SLOWDOWN = "slowdown"
    CRITICAL = "critical"


@dataclass
class ProviderStats:
    """Statistics for a rate-limited provider."""
    name: str
    limit_per_minute: int
    calls: deque = field(default_factory=lambda: deque(maxlen=1000))
    total_calls: int = 0
    total_rate_limited: int = 0
    total_fallback_used: int = 0
    delays_added: int = 0
    
    def add_call(self):
        """Record a new call."""
        now = datetime.now()
        self.calls.append(now)
        self.total_calls += 1
    
    def get_calls_in_window(self, window_seconds: int = 60) -> int:
        """Get number of calls in the last N seconds."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        return sum(1 for call in self.calls if call > cutoff)
    
    def get_usage_percent(self) -> float:
        """Get current usage as a percentage of limit."""
        calls = self.get_calls_in_window()
        return (calls / self.limit_per_minute) * 100 if self.limit_per_minute > 0 else 0
    
    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        usage = self.get_usage_percent() / 100  # Convert to 0-1 scale
        
        if usage >= SWITCH_THRESHOLD:
            return RateLimitStatus.CRITICAL
        elif usage >= SLOWDOWN_THRESHOLD:
            return RateLimitStatus.SLOWDOWN
        elif usage >= WARN_THRESHOLD:
            return RateLimitStatus.WARNING
        else:
            return RateLimitStatus.HEALTHY
    
    def get_delay_seconds(self) -> float:
        """
        Calculate delay to add before next call.
        
        Returns 0 if no delay needed, or seconds to wait.
        """
        status = self.get_status()
        
        if status == RateLimitStatus.CRITICAL:
            # Critical: wait until window refreshes
            return 5.0
        elif status == RateLimitStatus.SLOWDOWN:
            # Slowdown: add small delays
            return 1.0
        else:
            return 0
    
    def should_use_fallback(self) -> bool:
        """Check if we should switch to fallback provider."""
        return self.get_status() == RateLimitStatus.CRITICAL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "limit_per_minute": self.limit_per_minute,
            "calls_in_window": self.get_calls_in_window(),
            "usage_percent": round(self.get_usage_percent(), 1),
            "status": self.get_status().value,
            "total_calls": self.total_calls,
            "total_rate_limited": self.total_rate_limited,
            "total_fallback_used": self.total_fallback_used,
            "delays_added": self.delays_added
        }


class RateLimiter:
    """
    Proactive rate limiter for API calls.
    
    Tracks usage and prevents hitting rate limits by:
    - Adding delays when approaching limit
    - Switching to fallback when near limit
    - Warning before problems occur
    """
    
    def __init__(self):
        self.providers: Dict[str, ProviderStats] = {}
        self._init_providers()
        
        logger.info("⏱️ Rate Limiter initialized")
    
    def _init_providers(self):
        """Initialize provider stats."""
        for name, limit in RATE_LIMITS.items():
            self.providers[name] = ProviderStats(
                name=name,
                limit_per_minute=limit
            )
    
    def get_provider(self, name: str) -> ProviderStats:
        """Get or create a provider."""
        if name not in self.providers:
            # Default limit for unknown providers
            self.providers[name] = ProviderStats(
                name=name,
                limit_per_minute=60
            )
        return self.providers[name]
    
    async def check_and_wait(self, provider_name: str) -> Tuple[bool, float]:
        """
        Check rate limit and wait if needed.
        
        Returns (should_proceed, delay_added).
        """
        provider = self.get_provider(provider_name)
        
        # Check if we should use fallback
        if provider.should_use_fallback():
            provider.total_rate_limited += 1
            return False, 0
        
        # Check if we need to add delay
        delay = provider.get_delay_seconds()
        if delay > 0:
            logger.info(f"⏱️ {provider_name}: Adding {delay}s delay (usage: {provider.get_usage_percent():.1f}%)")
            await asyncio.sleep(delay)
            provider.delays_added += 1
        
        # Record the call
        provider.add_call()
        
        return True, delay
    
    def record_call(self, provider_name: str):
        """Record an API call (for tracking without waiting)."""
        provider = self.get_provider(provider_name)
        provider.add_call()
    
    def should_use_fallback(self, provider_name: str) -> bool:
        """Check if we should use a fallback for this provider."""
        provider = self.get_provider(provider_name)
        return provider.should_use_fallback()
    
    def get_best_provider(self, primary: str, fallbacks: list) -> str:
        """
        Get the best available provider.
        
        Returns primary if available, otherwise first available fallback.
        """
        primary_provider = self.get_provider(primary)
        
        if not primary_provider.should_use_fallback():
            return primary
        
        primary_provider.total_fallback_used += 1
        
        for fallback in fallbacks:
            fallback_provider = self.get_provider(fallback)
            if not fallback_provider.should_use_fallback():
                logger.info(f"⏱️ Switching from {primary} to {fallback} due to rate limits")
                return fallback
        
        # All providers are at limit - use primary anyway
        logger.warning(f"⏱️ All providers at limit, using {primary} anyway")
        return primary
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            name: provider.to_dict()
            for name, provider in self.providers.items()
        }
    
    def get_warnings(self) -> list:
        """Get list of providers with warnings or worse."""
        warnings = []
        for name, provider in self.providers.items():
            status = provider.get_status()
            if status != RateLimitStatus.HEALTHY:
                warnings.append({
                    "provider": name,
                    "status": status.value,
                    "usage_percent": provider.get_usage_percent()
                })
        return warnings


# ============================================================================
# DECORATOR
# ============================================================================

def rate_limited(provider_name: str, fallback_func: Callable = None):
    """
    Decorator to apply rate limiting to a function.
    
    Usage:
        @rate_limited("claude", fallback_func=call_openai)
        async def call_claude(message):
            return await claude.messages.create(...)
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            limiter = get_rate_limiter()
            
            should_proceed, delay = await limiter.check_and_wait(provider_name)
            
            if not should_proceed and fallback_func:
                logger.info(f"⏱️ {provider_name} rate limited, using fallback")
                return await fallback_func(*args, **kwargs)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# SINGLETON
# ============================================================================

_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter









