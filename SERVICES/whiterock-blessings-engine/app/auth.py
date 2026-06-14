"""
WhiteRock Blessings Engine - Authentication & Authorization
JWT-based auth with role-based access control.
v2.2 - With refresh tokens and token blacklist
"""

from datetime import datetime, timedelta
from typing import Optional, Set
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import Member

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)

# In-memory token blacklist (for logout)
# In production, use Redis for distributed blacklist
_token_blacklist: Set[str] = set()


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _get_token_hash(token: str) -> str:
    """Get a hash of the token for blacklist storage."""
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS))
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str, token_type: str = "access") -> dict:
    """Decode and validate a JWT token."""
    # Check blacklist
    token_hash = _get_token_hash(token)
    if token_hash in _token_blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


def blacklist_token(token: str) -> None:
    """Add a token to the blacklist (for logout)."""
    token_hash = _get_token_hash(token)
    _token_blacklist.add(token_hash)


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted."""
    token_hash = _get_token_hash(token)
    return token_hash in _token_blacklist


async def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    """
    Use a refresh token to get new access and refresh tokens.
    Returns (new_access_token, new_refresh_token)
    """
    payload = decode_access_token(refresh_token, token_type="refresh")
    
    # Blacklist the old refresh token (rotation)
    blacklist_token(refresh_token)
    
    # Create new tokens
    token_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "tier": payload.get("tier"),
        "is_admin": payload.get("is_admin"),
        "is_committee": payload.get("is_committee"),
        "is_auditor": payload.get("is_auditor")
    }
    
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)
    
    return new_access, new_refresh


async def get_current_member(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Member:
    """Get the current authenticated member from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(credentials.credentials)
    member_id = payload.get("sub")
    
    if not member_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    result = await db.execute(
        select(Member).where(Member.id == int(member_id), Member.is_active == True)
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Member not found or inactive"
        )
    
    return member


async def get_optional_member(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[Member]:
    """Get the current member if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        return await get_current_member(credentials, db)
    except HTTPException:
        return None


def require_role(required_role: str):
    """Dependency factory for role-based access control."""
    async def role_checker(
        member: Member = Depends(get_current_member)
    ) -> Member:
        roles = {
            "member": True,  # All authenticated users are members
            "admin": member.is_admin,
            "committee": member.is_committee or member.is_admin,
            "auditor": member.is_auditor or member.is_admin
        }
        
        if not roles.get(required_role, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required for this action"
            )
        
        return member
    
    return role_checker


# Convenience dependencies
require_admin = require_role("admin")
require_committee = require_role("committee")
require_auditor = require_role("auditor")


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request."""
    return request.headers.get("User-Agent", "unknown")
