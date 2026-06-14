from fastapi import HTTPException, Header
from typing import Dict, Any, Optional
import httpx
from ..config import settings
from ..utils.logging import get_logger

try:
    from jose import jwt, JWTError
except ImportError:
    import jwt
    JWTError = jwt.exceptions.InvalidTokenError

log = get_logger(__name__)

_registry_public_key: Optional[str] = None

async def get_registry_public_key() -> str:
    """Fetch Registry's public key for JWT verification"""
    global _registry_public_key
    if _registry_public_key:
        return _registry_public_key
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.registry_url}/.well-known/jwks.json")
            if response.status_code == 200:
                data = response.json()
                _registry_public_key = data.get("public_key")
                if _registry_public_key:
                    log.info("✅ Registry public key fetched successfully")
                    return _registry_public_key
    except Exception as e:
        log.error(f"Failed to fetch Registry public key: {e}")
    
    raise HTTPException(
        status_code=503,
        detail="Cannot verify tokens: Registry public key unavailable"
    )

async def verify_jwt_token(authorization: str = Header(None)) -> Dict[str, Any]:
    """Verify JWT token with Registry's public key"""
    if settings.debug:
        return {"droplet_id": settings.droplet_id, "scope": ["all"]}
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        public_key = await get_registry_public_key()
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="fullpotential.droplets",
            issuer="registry.fullpotential.ai"
        )
        
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def verify_jwt_token_string(token: str) -> Dict[str, Any]:
    """Verify JWT token from string (for UDC message signature)"""
    if not _registry_public_key:
        raise Exception("Registry public key not available")
    
    try:
        payload = jwt.decode(
            token,
            _registry_public_key,
            algorithms=["RS256"],
            audience="fullpotential.droplets",
            issuer="registry.fullpotential.ai"
        )
        return payload
    except JWTError as e:
        raise Exception(f"Invalid token: {str(e)}")
