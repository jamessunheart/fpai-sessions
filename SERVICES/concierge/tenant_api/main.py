"""tenant-api (port 8820) — Tenant CRUD + feature flag resolution + agent/client identity."""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.app_factory import create_app
from shared.db import SessionLocal, tenant_session
from shared.features import FEATURES, PLAN_DEFAULTS, get_feature
from shared.tenant_context import TenantContext, get_tenant_context

from .admin_sms import router as admin_sms_router
from .onboarding import router as onboarding_router

app = create_app("tenant-api")
app.include_router(onboarding_router)
app.include_router(admin_sms_router)


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name: str
    plan: str = "starter"
    industry: str | None = None
    timezone: str = "America/Denver"
    business_hours: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TenantOut(BaseModel):
    id: str
    slug: str
    name: str
    plan: str
    status: str
    industry: str | None
    timezone: str
    business_hours: dict
    metadata: dict


class FeatureToggle(BaseModel):
    feature_key: str
    enabled: bool
    config: dict[str, Any] = Field(default_factory=dict)


async def _su_session() -> AsyncSession:
    session = SessionLocal()
    await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
    return session


@app.post("/tenants", response_model=TenantOut, status_code=201)
async def create_tenant(body: TenantCreate):
    # Admin-only in prod; gated via internal token at the gateway.
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO tenants (slug, name, plan, industry, timezone, business_hours, metadata)
                    VALUES (:slug, :name, :plan, :industry, :tz, CAST(:bh AS jsonb), CAST(:md AS jsonb))
                    RETURNING id::text, slug, name, plan, status, industry, timezone, business_hours, metadata
                    """
                ),
                {
                    "slug": body.slug,
                    "name": body.name,
                    "plan": body.plan,
                    "industry": body.industry,
                    "tz": body.timezone,
                    "bh": _to_json(body.business_hours),
                    "md": _to_json(body.metadata),
                },
            )
        ).first()
        await session.commit()
    if not row:
        raise HTTPException(status_code=500, detail="failed to create tenant")
    return _row_to_tenant(row)


@app.get("/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    if ctx.tenant_id != tenant_id and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant read not allowed")
    async with tenant_session(tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT id::text, slug, name, plan, status, industry, timezone, business_hours, metadata
                    FROM tenants WHERE id = CAST(:tid AS uuid)
                    """
                ),
                {"tid": tenant_id},
            )
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="tenant not found")
    return _row_to_tenant(row)


@app.get("/tenants/{tenant_id}/features")
async def list_features(tenant_id: str, ctx: TenantContext = Depends(get_tenant_context)):
    if ctx.tenant_id != tenant_id and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant read not allowed")
    async with tenant_session(tenant_id) as session:
        plan_row = (
            await session.execute(
                text("SELECT plan FROM tenants WHERE id = CAST(:tid AS uuid)"),
                {"tid": tenant_id},
            )
        ).first()
        plan = plan_row[0] if plan_row else "starter"
        out = {}
        for key in sorted(FEATURES):
            state = await get_feature(session, key, plan=plan)
            out[key] = {"enabled": state.enabled, "config": state.config, "source": state.source}
    return {"tenant_id": tenant_id, "plan": plan, "features": out}


@app.put("/tenants/{tenant_id}/features")
async def set_feature(
    tenant_id: str, body: FeatureToggle, ctx: TenantContext = Depends(get_tenant_context)
):
    if ctx.tenant_id != tenant_id and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant write not allowed")
    if body.feature_key not in FEATURES:
        raise HTTPException(status_code=400, detail="unknown feature key")
    async with tenant_session(tenant_id) as session:
        await session.execute(
            text(
                """
                INSERT INTO tenant_features (tenant_id, feature_key, enabled, config)
                VALUES (CAST(:tid AS uuid), :k, :en, CAST(:cfg AS jsonb))
                ON CONFLICT (tenant_id, feature_key)
                DO UPDATE SET enabled = EXCLUDED.enabled,
                              config  = EXCLUDED.config,
                              updated_at = now()
                """
            ),
            {
                "tid": tenant_id,
                "k": body.feature_key,
                "en": body.enabled,
                "cfg": _to_json(body.config),
            },
        )
    return {"ok": True, "feature_key": body.feature_key, "enabled": body.enabled}


@app.get("/plans/{plan}/defaults")
async def plan_defaults(plan: str):
    return {"plan": plan, "defaults": PLAN_DEFAULTS.get(plan, {})}


def _row_to_tenant(row) -> TenantOut:
    return TenantOut(
        id=row[0],
        slug=row[1],
        name=row[2],
        plan=row[3],
        status=row[4],
        industry=row[5],
        timezone=row[6],
        business_hours=row[7] or {},
        metadata=row[8] or {},
    )


def _to_json(v: Any) -> str:
    import json

    return json.dumps(v or {})
