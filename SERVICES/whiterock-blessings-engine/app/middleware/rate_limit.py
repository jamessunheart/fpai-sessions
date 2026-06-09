"""
WhiteRock Blessings Engine - Rate Limiting Middleware
Uses slowapi with Redis backend for distributed rate limiting.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting.
    Uses authenticated user ID if available, otherwise IP address.
    """
    # Check for authenticated user in request state
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    
    if request.client:
        return f"ip:{request.client.host}"
    
    return "ip:unknown"


# Initialize limiter with Redis backend if available
if settings.RATE_LIMIT_ENABLED:
    try:
        limiter = Limiter(
            key_func=get_identifier,
            default_limits=[settings.RATE_LIMIT_DEFAULT],
            storage_uri=settings.REDIS_URL,
            strategy="fixed-window"
        )
    except Exception:
        # Fall back to memory storage if Redis unavailable
        limiter = Limiter(
            key_func=get_identifier,
            default_limits=[settings.RATE_LIMIT_DEFAULT],
            strategy="fixed-window"
        )
else:
    # Disabled limiter for testing
    limiter = Limiter(
        key_func=get_identifier,
        enabled=False
    )


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": f"Rate limit exceeded: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60)
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": str(exc.detail) if exc.detail else "unknown"
        }
    )


# Decorator helpers for common rate limits
def limit_register(func):
    """Rate limit for registration: 5/hour per IP."""
    return limiter.limit(settings.RATE_LIMIT_REGISTER)(func)


def limit_login(func):
    """Rate limit for login: 10/minute per IP."""
    return limiter.limit(settings.RATE_LIMIT_LOGIN)(func)


def limit_tithe(func):
    """Rate limit for tithe submission: 20/hour per user."""
    return limiter.limit(settings.RATE_LIMIT_TITHE)(func)


def limit_blessing(func):
    """Rate limit for blessing requests: 5/day per user."""
    return limiter.limit(settings.RATE_LIMIT_BLESSING)(func)



