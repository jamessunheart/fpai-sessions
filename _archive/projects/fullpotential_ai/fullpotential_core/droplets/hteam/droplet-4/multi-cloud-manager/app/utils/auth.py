"""
JWT authentication utilities
Handles JWKS verification for incoming tokens
"""

from typing import Optional
from fastapi import HTTPException, Header, Depends
from jose import jwt, jwk
from jose.exceptions import JWTError

from app.config import settings
from app.utils.logging import log
from app.services.jwt_service import fetch_jwks


async def fallback_simple_auth(token: str) -> dict:
    """
    Fallback authentication when JWKS is not available
    
    Args:
        token: Bearer token from Authorization header
    
    Returns:
        Token payload dictionary
    
    Raises:
        HTTPException: If token is invalid
    """
    # If simple tokens are allowed, check for API_TOKEN
    if settings.allow_simple_token and token == settings.api_token:
        log.info("auth_simple_token", message="Simple token authenticated")
        return {
            "droplet_id": 0,
            "permissions": ["*"],
            "iss": "fallback",
            "sub": "api_token"
        }

    # Try to decode as JWT (without verification since JWKS unavailable)
    try:
        unverified_payload = jwt.get_unverified_claims(token)

        # Check if it's from our trusted issuer
        if unverified_payload.get("iss") == settings.jwt_issuer:
            log.info(
                "auth_jwt_unverified",
                message=f"JWT accepted (unverified) from trusted issuer: {settings.jwt_issuer}",
                subject=unverified_payload.get("sub")
            )
            return unverified_payload
        else:
            log.warning(
                "auth_untrusted_issuer",
                issuer=unverified_payload.get("iss")
            )
            raise HTTPException(
                status_code=401,
                detail=f"Untrusted JWT issuer: {unverified_payload.get('iss')}"
            )

    except JWTError as e:
        log.error("auth_invalid_jwt", error=str(e))
        if settings.allow_simple_token:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: not a valid JWT or API token"
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="JWT token required. Provided token is not a valid JWT."
            )
    except Exception as e:
        log.error("auth_error", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")


def get_public_key_from_jwks(jwks_data: dict, token_header: dict):
    """
    Extract public key from JWKS (supports PEM and JWK formats)
    
    Args:
        jwks_data: JWKS data from Registry
        token_header: JWT header containing kid
    
    Returns:
        Public key for verification or None
    """
    try:
        kid = token_header.get("kid")
        keys = jwks_data.get("keys", [])
        
        if not keys:
            log.error("jwks_no_keys", message="No keys found in JWKS")
            return None
        
        # Select key
        key_data = None
        if kid:
            for k in keys:
                if k.get("kid") == kid:
                    key_data = k
                    log.info("jwks_key_found", kid=kid)
                    break
            if not key_data:
                log.error("jwks_key_not_found", kid=kid)
                return None
        else:
            log.info("jwks_no_kid", message="Token has no 'kid', using first available key")
            key_data = keys[0]
        
        # Convert key to usable format
        if "pem" in key_data:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            pem_str = key_data["pem"]
            public_key = serialization.load_pem_public_key(
                pem_str.encode('utf-8'),
                backend=default_backend()
            )
            log.info("jwks_pem_loaded", message="Loaded public key from PEM format")
            return public_key
        else:
            public_key = jwk.construct(key_data)
            log.info("jwks_jwk_loaded", message="Loaded public key from JWK format")
            return public_key
        
    except Exception as e:
        log.error("jwks_key_error", error=str(e))
        return None


async def verify_jwt_with_jwks(authorization: str = Header(None)) -> dict:
    """
    Verify JWT token using JWKS from Registry v2
    
    Args:
        authorization: Authorization header value
    
    Returns:
        Verified token payload
    
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Use: Bearer <token>"
        )
    
    token = authorization.replace("Bearer ", "")
    
    # Check if JWKS is available
    jwks_data = await fetch_jwks()
    jwks_available = jwks_data is not None
    
    # If JWKS available, require JWT tokens (unless override set)
    if jwks_available and not settings.allow_simple_token:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as e:
            log.error("auth_not_jwt", error=str(e))
            raise HTTPException(
                status_code=401,
                detail="JWT token required. Provided token is not a valid JWT."
            )
        
        # Verify JWT
        try:
            public_key = get_public_key_from_jwks(jwks_data, unverified_header)
            if not public_key:
                log.error(
                    "auth_key_not_found",
                    kid=unverified_header.get("kid")
                )
                raise HTTPException(
                    status_code=401,
                    detail="Invalid JWT: key not found in JWKS"
                )
            
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer
            )
            
            log.info(
                "auth_jwt_verified",
                droplet_id=payload.get("droplet_id")
            )
            return payload
            
        except JWTError as e:
            log.error("auth_jwt_failed", error=str(e))
            raise HTTPException(
                status_code=401,
                detail=f"Invalid JWT token: {e}"
            )
        except Exception as e:
            log.error("auth_unexpected_error", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Authentication error: {e}"
            )
    
    # JWKS not available - use fallback
    if not jwks_available:
        log.warning("auth_fallback", message="JWKS not available - using fallback authentication")
        return await fallback_simple_auth(token)
    
    # JWKS available but ALLOW_SIMPLE_TOKEN=true
    if settings.allow_simple_token:
        log.warning("auth_simple_allowed", message="Simple token accepted (ALLOW_SIMPLE_TOKEN=true)")
        return await fallback_simple_auth(token)


async def verify_jwt_token(authorization: Optional[str] = Header(None)) -> dict:
    """
    Main authentication dependency
    Use this in route dependencies: Depends(verify_jwt_token)
    """
    return await verify_jwt_with_jwks(authorization)
