"""JWT issuance for client users and agents.

Service-to-service auth uses the ``X-Internal-Token`` header instead.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from .config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(pw: str) -> str:
    return _pwd.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    return _pwd.verify(pw, hashed)


def issue_token(
    *,
    subject: str,
    tenant_id: str | None,
    actor_type: str,
    roles: list[str] | None = None,
    ttl_minutes: int = 60 * 12,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "actor_type": actor_type,
        "roles": roles or [],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
