#!/usr/bin/env python3
"""
ARIA RATE LIMITER
==================

Per-user rate limiting to prevent abuse and control costs.
Different limits for different authority levels.
"""

import os
import logging
import time
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger("aria.rate_limiter")


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    max_requests: int
    window_seconds: int
    name: str


# Rate limits by operation type
RATE_LIMITS = {
    "message": RateLimitConfig(max_requests=60, window_seconds=3600, name="messages per hour"),
    "tool_call": RateLimitConfig(max_requests=30, window_seconds=3600, name="tool calls per hour"),
    "voice": RateLimitConfig(max_requests=10, window_seconds=86400, name="voice messages per day"),
    "file_write": RateLimitConfig(max_requests=20, window_seconds=3600, name="file writes per hour"),
}

# Stewards have no limits
STEWARD_MULTIPLIER = float('inf')

# In-memory storage for rate limits (could be Redis in production)
# Structure: {user_id: {operation: [(timestamp, count), ...]}}
_rate_data: Dict[int, Dict[str, list]] = defaultdict(lambda: defaultdict(list))


class RateLimiter:
    """
    Rate limiter for API and tool calls.
    
    Uses sliding window algorithm for accurate rate limiting.
    """
    
    def __init__(self):
        self.limits = RATE_LIMITS
        
        # Import authority checks
        try:
            from access.authority import is_steward
            self._is_steward = is_steward
            self._enabled = True
        except ImportError:
            self._enabled = False
            logger.warning("Authority module not available - rate limiting disabled")
    
    def check_rate_limit(
        self,
        user_id: int,
        operation: str = "message"
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Check if a user is within their rate limit.
        
        Args:
            user_id: Telegram user ID
            operation: Type of operation (message, tool_call, voice, file_write)
            
        Returns:
            (allowed, message, retry_after_seconds)
        """
        if not self._enabled:
            return True, "Rate limiting disabled", None
        
        # Stewards have no limits
        if self._is_steward(user_id):
            return True, "Steward - no limits", None
        
        # Get limit config
        config = self.limits.get(operation)
        if not config:
            return True, f"Unknown operation: {operation}", None
        
        now = time.time()
        window_start = now - config.window_seconds
        
        # Get user's data for this operation
        user_data = _rate_data[user_id][operation]
        
        # Clean old entries outside the window
        user_data[:] = [(ts, count) for ts, count in user_data if ts > window_start]
        
        # Count requests in current window
        total_requests = sum(count for _, count in user_data)
        
        if total_requests >= config.max_requests:
            # Find when the window will clear enough
            oldest_in_window = min(ts for ts, _ in user_data) if user_data else now
            retry_after = int(oldest_in_window + config.window_seconds - now) + 1
            
            return (
                False,
                f"⏳ You've hit the limit of {config.max_requests} {config.name}.\n"
                f"Please wait {self._format_time(retry_after)} before trying again.",
                retry_after
            )
        
        return True, "Within limits", None
    
    def record_request(self, user_id: int, operation: str = "message") -> None:
        """
        Record a request for rate limiting.
        
        Args:
            user_id: Telegram user ID
            operation: Type of operation
        """
        if not self._enabled:
            return
        
        # Stewards aren't tracked
        if self._is_steward(user_id):
            return
        
        now = time.time()
        _rate_data[user_id][operation].append((now, 1))
    
    def get_remaining(self, user_id: int, operation: str = "message") -> Tuple[int, int]:
        """
        Get remaining requests in current window.
        
        Returns:
            (remaining_requests, seconds_until_reset)
        """
        if not self._enabled:
            return float('inf'), 0
        
        if self._is_steward(user_id):
            return float('inf'), 0
        
        config = self.limits.get(operation)
        if not config:
            return float('inf'), 0
        
        now = time.time()
        window_start = now - config.window_seconds
        
        user_data = _rate_data[user_id][operation]
        current_requests = sum(
            count for ts, count in user_data if ts > window_start
        )
        
        remaining = max(0, config.max_requests - current_requests)
        
        # Calculate reset time
        if user_data:
            oldest = min(ts for ts, _ in user_data if ts > window_start)
            reset_in = int(oldest + config.window_seconds - now)
        else:
            reset_in = config.window_seconds
        
        return remaining, max(0, reset_in)
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds into human-readable time."""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
    
    def get_status(self, user_id: int) -> Dict[str, Dict]:
        """Get rate limit status for all operations."""
        status = {}
        
        for operation, config in self.limits.items():
            remaining, reset_in = self.get_remaining(user_id, operation)
            status[operation] = {
                "limit": config.max_requests,
                "remaining": remaining if remaining != float('inf') else "unlimited",
                "reset_in_seconds": reset_in,
                "window": config.name
            }
        
        return status


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the singleton RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit(user_id: int, operation: str = "message") -> Tuple[bool, str, Optional[int]]:
    """Convenience function to check rate limit."""
    return get_rate_limiter().check_rate_limit(user_id, operation)


def record_request(user_id: int, operation: str = "message") -> None:
    """Convenience function to record a request."""
    get_rate_limiter().record_request(user_id, operation)


