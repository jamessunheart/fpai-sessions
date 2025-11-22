"""Authentication and authorization"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .models import AccessToken, AccessScope
from .database import get_db

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.access_token_expire_hours)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get current authenticated user from token"""
    token = credentials.credentials
    payload = verify_token(token)

    # Check if it's admin token
    if payload.get("type") == "admin":
        return {
            "type": "admin",
            "username": payload.get("username"),
            "scope": AccessScope.ADMIN
        }

    # Check if it's helper token
    if payload.get("type") == "helper":
        token_id = payload.get("token_id")

        # Verify token not revoked
        result = await db.execute(
            select(AccessToken).where(AccessToken.id == token_id)
        )
        access_token = result.scalar_one_or_none()

        if not access_token or access_token.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        if access_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )

        return {
            "type": "helper",
            "token_id": token_id,
            "helper_name": access_token.helper_name,
            "credential_ids": access_token.credential_ids,
            "scope": AccessScope(access_token.scope)
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token type"
    )


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin access"""
    if current_user.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def check_credential_access(
    credential_id: int,
    current_user: dict = Depends(get_current_user)
) -> bool:
    """Check if user has access to credential"""
    # Admin has access to everything
    if current_user.get("type") == "admin":
        return True

    # Helpers only have access to specific credentials
    if current_user.get("type") == "helper":
        allowed_ids = current_user.get("credential_ids", [])
        if credential_id not in allowed_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this credential"
            )
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied"
    )
