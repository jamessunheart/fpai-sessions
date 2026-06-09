"""
Authentication & Authorization for Team Portal
- Magic link login (passwordless)
- JWT session tokens
- Role-based access (admin vs member)
"""

import secrets
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal
from . import models

settings = get_settings()
security = HTTPBearer(auto_error=False)


# --- JWT Utilities ---

def create_access_token(member_id: str, email: str, role: str) -> str:
    """Create a JWT access token for authenticated user."""
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": member_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# --- Magic Link ---

def generate_magic_token() -> str:
    """Generate a secure random token for magic link."""
    return secrets.token_urlsafe(32)


def create_magic_link(email: str, db: Session) -> Tuple[str, datetime]:
    """Create a magic link entry and return the token."""
    token = generate_magic_token()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)
    
    # Remove any existing magic links for this email
    db.query(models.MagicLink).filter(models.MagicLink.email == email).delete()
    
    link = models.MagicLink(
        token=token,
        email=email,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()
    
    return token, expires_at


def verify_magic_link(token: str, db: Session) -> Optional[models.TeamMember]:
    """Verify a magic link token and return the associated member."""
    link = db.query(models.MagicLink).filter(
        models.MagicLink.token == token,
        models.MagicLink.used == False,
        models.MagicLink.expires_at > datetime.utcnow(),
    ).first()
    
    if not link:
        return None
    
    # Mark as used
    link.used = True
    link.used_at = datetime.utcnow()
    db.commit()
    
    # Find or create member
    member = db.query(models.TeamMember).filter(
        models.TeamMember.email == link.email
    ).first()
    
    return member


# --- Role Helpers ---

def get_admin_emails() -> list:
    """Get list of admin emails from config."""
    if not settings.ADMIN_EMAILS:
        return []
    return [e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()]


def is_admin(email: str) -> bool:
    """Check if email is in admin list."""
    return email.lower() in get_admin_emails()


def get_role(email: str) -> str:
    """Determine role based on email."""
    return "admin" if is_admin(email) else "member"


# --- Auth Dependencies ---

class CurrentUser:
    """Represents the currently authenticated user."""
    def __init__(self, member_id: str, email: str, role: str):
        self.member_id = member_id
        self.email = email
        self.role = role
        self.is_admin = role == "admin"


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[CurrentUser]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    
    return CurrentUser(
        member_id=payload.get("sub"),
        email=payload.get("email"),
        role=payload.get("role", "member"),
    )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """Get current user, raise 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload:
        return CurrentUser(
            member_id=payload.get("sub"),
            email=payload.get("email"),
            role=payload.get("role", "member"),
        )
        
    # If NOT a valid local JWT, check if it's a Genesis Agent Key
    if token.startswith("agent-"):
        from .integrations import genesis_client
        result = await genesis_client.verify_key(token)
        if result and result.get("status") == "valid":
            return CurrentUser(
                member_id=result.get("agent_name", "unknown_agent"),
                email=f"{result.get('agent_name', 'agent')}@genesis.local",
                role=result.get("role", "agent"),
            )
            
    # If we got here, it's invalid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Require admin role, raise 403 if not admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# --- Invite Token ---

def create_invite_token(email: str, role: str, db: Session) -> str:
    """Create an invite token for a new team member."""
    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invite = models.Invitation(
        token=token,
        email=email,
        role=role,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    
    return token


def verify_invite_token(token: str, db: Session) -> Optional[models.Invitation]:
    """Verify an invite token."""
    invite = db.query(models.Invitation).filter(
        models.Invitation.token == token,
        models.Invitation.used == False,
        models.Invitation.expires_at > datetime.utcnow(),
    ).first()
    return invite


def consume_invite(invite: models.Invitation, db: Session) -> None:
    """Mark an invite as used."""
    invite.used = True
    db.commit()


