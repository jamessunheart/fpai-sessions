"""
JWT token service
Handles fetching tokens FROM Registry and JWKS for verification
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.utils.logging import log, log_event

# Cache for outgoing JWT tokens (for authenticating TO Registry)
_outgoing_jwt_token: Optional[str] = None
_outgoing_jwt_token_expiry: Optional[datetime] = None

# Cache for JWKS keys (for verifying incoming tokens FROM other droplets)
_jwks_cache: Optional[dict] = None
_jwks_cache_time: Optional[datetime] = None


async def fetch_registry_jwt_token() -> Optional[str]:
    """
    Fetch JWT token from Registry v2 (RS256)
    Token is valid for 24 hours (86400 seconds)
    This token is used for authenticating OUR requests TO the Registry
    
    Returns:
        JWT token string or None if failed
    """
    global _outgoing_jwt_token, _outgoing_jwt_token_expiry
    
    # Return cached token if still valid (with 5 min buffer)
    if _outgoing_jwt_token and _outgoing_jwt_token_expiry:
        if datetime.utcnow() < _outgoing_jwt_token_expiry - timedelta(minutes=5):
            return _outgoing_jwt_token
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.registry_url}/auth/token",
                params={"droplet_id": settings.droplet_domain},
                headers={"X-Registry-Key": settings.registry_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                _outgoing_jwt_token = data["token"]
                _outgoing_jwt_token_expiry = datetime.utcnow() + timedelta(hours=24)
                
                log.info(
                    "jwt_token_fetched",
                    message="Fetched JWT token from Registry v2 (RS256)",
                    expires_in=data.get("expires_in", 86400)
                )
                log_event("jwt_token_fetched", {
                    "expires_in": data.get("expires_in", 86400),
                    "algorithm": "RS256"
                })
                
                return _outgoing_jwt_token
            else:
                log.error(
                    "jwt_fetch_failed",
                    status_code=response.status_code,
                    response=response.text
                )
                return None
                
    except Exception as e:
        log.error("jwt_fetch_error", error=str(e))
        return None


async def fetch_jwks() -> Optional[dict]:
    """
    Fetch JWKS from Registry v2
    Used for verifying incoming JWT tokens FROM other droplets
    
    Returns:
        JWKS data dictionary or None if failed
    """
    global _jwks_cache, _jwks_cache_time
    
    # Return cached JWKS if still valid (refresh every 24 hours)
    if _jwks_cache and _jwks_cache_time:
        if datetime.utcnow() - _jwks_cache_time < timedelta(hours=24):
            return _jwks_cache
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(settings.jwks_url)
            
            if response.status_code == 200:
                jwks_data = response.json()
                _jwks_cache = jwks_data
                _jwks_cache_time = datetime.utcnow()
                log.info("jwks_fetched", url=settings.jwks_url)
                return jwks_data
            else:
                log.debug(
                    "jwks_unavailable",
                    status_code=response.status_code
                )
                return None
    except Exception as e:
        log.debug("jwks_fetch_error", error=str(e))
        return None


async def startup_fetch_jwks():
    """Fetch JWKS on startup if not using simple tokens"""
    if not settings.allow_simple_token:
        log.info("jwks_startup", message="Fetching JWKS from Registry v2...")
        jwks = await fetch_jwks()
        if jwks:
            log.info(
                "jwks_loaded",
                key_count=len(jwks.get("keys", []))
            )
        else:
            log.warning("jwks_load_failed", message="Could not fetch JWKS - JWT verification will fail")
    else:
        log.info("jwks_skipped", message="Simple token authentication enabled (JWKS verification skipped)")


def clear_token_cache():
    """Clear cached tokens (useful for testing or forced refresh)"""
    global _outgoing_jwt_token, _outgoing_jwt_token_expiry
    _outgoing_jwt_token = None
    _outgoing_jwt_token_expiry = None
    log.info("token_cache_cleared", message="JWT token cache cleared")
