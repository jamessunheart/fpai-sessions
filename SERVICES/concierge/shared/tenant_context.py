"""Tenant resolution + FastAPI dependency.

Tenants can be resolved from (in order):
1. Explicit ``X-Tenant-Id`` header (internal service-to-service calls, with the
   ``X-Internal-Token`` header set to ``settings.internal_service_token``).
2. JWT claim ``tenant_id`` on the bearer token (client + agent tokens).
3. Path/query parameter ``tenant_id`` (dev/admin only, gated by env).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from jose import JWTError, jwt

from .config import settings


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    actor_type: str  # 'client' | 'agent' | 'system'
    actor_id: Optional[str] = None
    roles: tuple[str, ...] = ()
    is_superuser: bool = False


def _decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}") from e


async def get_tenant_context(
    request: Request,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    authorization: str | None = Header(default=None),
) -> TenantContext:
    # Internal service call
    if x_internal_token and x_internal_token == settings.internal_service_token:
        if not x_tenant_id:
            raise HTTPException(status_code=400, detail="X-Tenant-Id required for internal calls")
        return TenantContext(
            tenant_id=x_tenant_id, actor_type="system", is_superuser=False
        )

    # Bearer token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        claims = _decode_jwt(token)
        tid = claims.get("tenant_id") or x_tenant_id
        if not tid:
            raise HTTPException(status_code=401, detail="token missing tenant_id")
        return TenantContext(
            tenant_id=tid,
            actor_type=claims.get("actor_type", "client"),
            actor_id=claims.get("sub"),
            roles=tuple(claims.get("roles", [])),
            is_superuser=bool(claims.get("is_superuser", False)),
        )

    if settings.env == "development" and x_tenant_id:
        return TenantContext(tenant_id=x_tenant_id, actor_type="system")

    raise HTTPException(status_code=401, detail="no tenant context")


TenantDep = Depends(get_tenant_context)
