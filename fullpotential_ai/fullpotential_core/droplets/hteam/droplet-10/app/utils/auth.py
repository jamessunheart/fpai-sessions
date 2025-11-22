"""
JWT Authentication
Token verification and dependency injection for protected endpoints
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import structlog

from app.config import settings

log = structlog.get_logger()

# HTTP Bearer token scheme
security = HTTPBearer()


# ============================================================================
# TOKEN CREATION (for internal use)
# ============================================================================

def create_access_token(
    data: Dict[str, any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data to encode in token
        expires_delta: Token expiration time (defaults to settings)
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.jwt_expiration)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    if not settings.jwt_private_key:
            raise RuntimeError("RS256 signing requires jwt_private_key")
    signing_key = settings.jwt_private_key

    encoded_jwt = jwt.encode(
        to_encode,
        signing_key,
        algorithm=settings.jwt_algorithm
    )

    
    return encoded_jwt


# ============================================================================
# TOKEN VERIFICATION
# ============================================================================
def verify_token(token: str) -> Dict[str, any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,   # <-- PUBLIC KEY
            algorithms=[settings.jwt_algorithm]
        )

        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError as e:
        log.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, any]:
    """
    FastAPI dependency for JWT authentication
    
    Usage:
        @app.get("/protected")
        async def protected_endpoint(token_data: dict = Depends(verify_jwt_token)):
            droplet_id = token_data["droplet_id"]
            return {"message": "Authenticated"}
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If authentication fails
    """
    return verify_token(credentials.credentials)


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

async def optional_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, any]]:
    """
    Optional JWT authentication (doesn't fail if no token provided)
    
    Usage:
        @app.get("/public-or-private")
        async def endpoint(token_data: Optional[dict] = Depends(optional_jwt_token)):
            if token_data:
                # User is authenticated
                pass
            else:
                # Anonymous access
                pass
    
    Returns:
        Decoded token payload or None if no token provided
    """
    if credentials is None:
        return None
    
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None


# ============================================================================
# PERMISSION CHECKING
# ============================================================================

def check_droplet_permission(
    token_data: Dict[str, any],
    required_droplet_id: int = None,
    required_permission: str = None
) -> bool:
    """
    Check if token has required permissions
    
    Args:
        token_data: Decoded JWT payload
        required_droplet_id: Required droplet ID (if specific droplet only)
        required_permission: Required permission string
    
    Returns:
        True if permission granted, False otherwise
    """
    # Check droplet ID match
    if required_droplet_id:
        token_droplet_id = token_data.get("droplet_id")
        if token_droplet_id != required_droplet_id:
            return False
    
    # Check permission
    if required_permission:
        permissions = token_data.get("permissions", [])
        if required_permission not in permissions:
            return False
    
    return True


def require_droplet(droplet_id: int):
    """
    Dependency factory for requiring specific droplet authentication
    
    Usage:
        @app.post("/tasks/{task_id}/update")
        async def update_task(
            task_id: int,
            token_data: dict = Depends(require_droplet(8))  # Only Verifier can update
        ):
            pass
    """
    async def _require_droplet(token_data: Dict[str, any] = Depends(verify_jwt_token)) -> Dict[str, any]:
        if not check_droplet_permission(token_data, required_droplet_id=droplet_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Only droplet #{droplet_id} can access this endpoint."
            )
        return token_data
    
    return _require_droplet


def require_permission(permission: str):
    """
    Dependency factory for requiring specific permission
    
    Usage:
        @app.delete("/tasks/{task_id}")
        async def delete_task(
            task_id: int,
            token_data: dict = Depends(require_permission("admin"))
        ):
            pass
    """
    async def _require_permission(token_data: Dict[str, any] = Depends(verify_jwt_token)) -> Dict[str, any]:
        if not check_droplet_permission(token_data, required_permission=permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission: {permission}"
            )
        return token_data
    
    return _require_permission


# ============================================================================
# WEBSOCKET AUTHENTICATION
# ============================================================================

def verify_websocket_token(token: str) -> Dict[str, any]:
    """
    Verify JWT token for WebSocket connections
    
    WebSocket connections receive token as query parameter:
    ws://host/ws/tasks?token=eyJ...
    
    Args:
        token: JWT token from query parameter
    
    Returns:
        Decoded token payload
    
    Raises:
        ValueError: If token is invalid
    """
    try:
        return verify_token(token)
    except HTTPException as e:
        # Convert HTTPException to ValueError for WebSocket handling
        raise ValueError(f"Authentication failed: {e.detail}")


# ============================================================================
# TOKEN HELPERS
# ============================================================================

def get_droplet_id_from_token(token_data: Dict[str, any]) -> Optional[int]:
    """Extract droplet ID from token payload"""
    return token_data.get("droplet_id")


def get_steward_from_token(token_data: Dict[str, any]) -> Optional[str]:
    """Extract steward name from token payload"""
    return token_data.get("steward")


def get_permissions_from_token(token_data: Dict[str, any]) -> list[str]:
    """Extract permissions list from token payload"""
    return token_data.get("permissions", [])


def is_admin_token(token_data: Dict[str, any]) -> bool:
    """Check if token has admin permissions"""
    return "admin" in get_permissions_from_token(token_data)


# ============================================================================
# MOCK TOKEN (for testing)
# ============================================================================

def create_mock_token(
    droplet_id: int = 10,
    steward: str = "test",
    permissions: list[str] = None
) -> str:
    """
    Create a mock JWT token for testing
    
    Args:
        droplet_id: Droplet ID to encode
        steward: Steward name to encode
        permissions: List of permissions
    
    Returns:
        JWT token string
    """
    if permissions is None:
        permissions = ["read", "write"]
    
    return create_access_token({
        "droplet_id": droplet_id,
        "steward": steward,
        "permissions": permissions
    })