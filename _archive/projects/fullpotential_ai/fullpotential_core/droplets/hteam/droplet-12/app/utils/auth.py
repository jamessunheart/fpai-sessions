"""
JWT Authentication
Per SECURITY_REQUIREMENTS.md - JWT verification required
"""

from jose import jwt, JWTError
from fastapi import HTTPException, Depends, Header
from typing import Dict, Optional

from app.config import settings
from app.utils.logging import get_logger

log = get_logger(__name__)


async def verify_jwt_token(authorization: str = Header(None)) -> Dict:
    """
    Verify JWT token from Authorization header.
    Per SECURITY_REQUIREMENTS.md and UDC_COMPLIANCE.md.
    Required on ALL endpoints except /health.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token payload dict
        
    Raises:
        HTTPException: If token is invalid, expired, or missing
        
    Example:
        @app.get("/protected")
        async def protected_endpoint(
            token_data: dict = Depends(verify_jwt_token)
        ):
            droplet_id = token_data["droplet_id"]
            # ... endpoint logic
    """
    # Check header presence
    if not authorization:
        log.warning("missing_authorization_header")
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check Bearer format
    if not authorization.startswith("Bearer "):
        log.warning("invalid_authorization_format", auth_header=authorization[:20])
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token
    token = authorization.replace("Bearer ", "")
    
    try:
        # Detect token algorithm
        import base64
        import json
        header_part = token.split('.')[0]
        header_part += '=' * (4 - len(header_part) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_part))
        algorithm = header.get('alg', 'RS256')
        print(algorithm)
        print(header)
        # Handle different algorithms
        if algorithm == 'HS256':
            # Orchestrator token (HS256) - use secret key
            log.warning("hs256_token_detected", message="Orchestrator using insecure HS256")
            secret_key = settings.get_orchestrator_secret_key()
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=['HS256'],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True
                }
            )
        else:
            # Registry token (RS256) - use public key
            public_key = settings.load_registry_public_key()
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True
                }
            )
        print(payload)
        # Additional validation
        if "sub" not in payload:
            log.warning("token_missing_droplet_id")
            raise HTTPException(
                status_code=401,
                detail="Token missing droplet_id claim"
            )
        
        log.info(
            "token_verified",
            droplet_id=payload.get("sub"),
            exp=payload.get("exp")
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        log.warning("token_expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
        
    except jwt.JWTClaimsError as e:
        log.warning("token_claims_error", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token claims: {e}"
        )
        
    except JWTError as e:
        log.warning("token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {e}"
        )
    
    except Exception as e:
        log.error("token_verification_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Token verification failed"
        )


async def verify_jwt_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict]:
    """
    Optional JWT verification (returns None if no token).
    
    Args:
        authorization: Optional Authorization header
        
    Returns:
        Token payload dict or None
    """
    if not authorization:
        return None
    
    try:
        return await verify_jwt_token(authorization)
    except HTTPException:
        return None