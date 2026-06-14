"""Self-serve onboarding router — mounts under /onboarding on tenant-api.

Flow (matches `SPEC.md` §self-serve):
  POST /onboarding/start               → create tenant (plan=starter, status=trial)
  POST /onboarding/{tid}/knowledge     → register URL(s) for crawl
  POST /onboarding/{tid}/persona       → set voice prompt pack from template
  POST /onboarding/{tid}/phone-trial   → allocate a Twilio trial number (stub)
  POST /onboarding/{tid}/checkout      → delegate to User Service for Stripe URL
  GET  /onboarding/{tid}/status        → progress summary
"""
from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from shared.auth import hash_password
from shared.config import settings
from shared.db import SessionLocal, tenant_session
from shared.tenant_context import TenantContext, get_tenant_context

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


TEMPLATES = {
    "home_services.hvac": {
        "name": "HVAC Concierge",
        "system_prompt": (
            "You are the AI Concierge for an HVAC service company. "
            "Answer warmly, disclose you are an AI assistant on the first exchange. "
            "Qualify the job (heating vs cooling, urgency, address), and book a visit. "
            "Never invent prices; use get_service_estimate. On human request or low "
            "confidence, call escalate_to_human."
        ),
        "tools": [
            {
                "name": "book_appointment",
                "description": "Book a service visit",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string"},
                        "window": {"type": "string"},
                        "address": {"type": "string"},
                        "phone": {"type": "string"},
                        "notes": {"type": "string"},
                    },
                    "required": ["service", "window", "phone"],
                },
            },
            {
                "name": "get_service_estimate",
                "description": "Ballpark estimate for a service",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string"},
                        "details": {"type": "string"},
                    },
                    "required": ["service"],
                },
            },
            {
                "name": "escalate_to_human",
                "description": "Warm-transfer to a human agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"},
                        "skills_required": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["reason"],
                },
            },
        ],
    },
    "home_services.plumbing": {
        "name": "Plumbing Concierge",
        "system_prompt": (
            "You are the AI Concierge for a plumbing service. Answer warmly, disclose you are "
            "an AI assistant on the first exchange. Qualify the job (emergency vs scheduled, "
            "fixture type, address), and book a visit. On human request, escalate."
        ),
        "tools": [],  # fall back to the HVAC set on first save if empty
    },
    "legal.personal_injury_intake": {
        "name": "Legal Intake Concierge",
        "system_prompt": (
            "You are the AI Intake specialist for a personal injury firm. Empathetic, clear, "
            "disclose AI on the first exchange. Capture incident type, date, injuries, "
            "insurance, and contact info. Always escalate on liability questions."
        ),
        "tools": [],
    },
}


class OnboardStart(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    name: str
    industry: str
    timezone: str = "America/Denver"
    admin_email: str
    admin_password: str | None = None
    admin_name: str | None = None


class OnboardStartOut(BaseModel):
    tenant_id: str
    slug: str
    next_steps: list[str]


@router.post("/start", response_model=OnboardStartOut, status_code=201)
async def onboard_start(body: OnboardStart):
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO tenants (slug, name, plan, status, industry, timezone, metadata)
                    VALUES (:slug, :name, 'starter', 'trial', :ind, :tz, CAST(:md AS jsonb))
                    RETURNING id::text
                    """
                ),
                {
                    "slug": body.slug,
                    "name": body.name,
                    "ind": body.industry,
                    "tz": body.timezone,
                    "md": json.dumps({"onboarding_started": True}),
                },
            )
        ).first()
        tid = row[0]

        # Default feature flags for starter trial
        for key, enabled in {
            "inbound_voice": True,
            "inbound_sms": True,
            "booking": True,
            "human_escalation": True,
            "realtime_voice": True,
            "ai_qa": True,
            "auto_training": True,
        }.items():
            await session.execute(
                text(
                    """
                    INSERT INTO tenant_features (tenant_id, feature_key, enabled)
                    VALUES (CAST(:tid AS uuid), :k, :en)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"tid": tid, "k": key, "en": enabled},
            )

        # Seed admin user
        await session.execute(
            text(
                """
                INSERT INTO client_users (tenant_id, email, name, role, password_hash)
                VALUES (CAST(:tid AS uuid), :e, :n, 'admin', :pw)
                ON CONFLICT DO NOTHING
                """
            ),
            {
                "tid": tid,
                "e": body.admin_email,
                "n": body.admin_name,
                "pw": hash_password(body.admin_password) if body.admin_password else None,
            },
        )

        # If the template exists, seed the prompt pack immediately
        tmpl = TEMPLATES.get(body.industry) or TEMPLATES.get("home_services.hvac")
        await session.execute(
            text(
                """
                INSERT INTO prompt_packs (tenant_id, name, kind, system_prompt, tools, active)
                VALUES (CAST(:tid AS uuid), :name, 'voice', :sp, CAST(:tools AS jsonb), true)
                """
            ),
            {
                "tid": tid,
                "name": tmpl["name"],
                "sp": tmpl["system_prompt"],
                "tools": json.dumps(
                    tmpl["tools"] or TEMPLATES["home_services.hvac"]["tools"]
                ),
            },
        )
        await session.commit()

    return OnboardStartOut(
        tenant_id=tid,
        slug=body.slug,
        next_steps=[
            "POST /onboarding/{tid}/knowledge with one or more URLs",
            "POST /onboarding/{tid}/phone-trial to get a trial Twilio number",
            "POST /onboarding/{tid}/checkout to start paid plan",
        ],
    )


class KnowledgeIn(BaseModel):
    urls: list[str]


@router.post("/{tid}/knowledge")
async def add_knowledge(
    tid: str, body: KnowledgeIn, ctx: TenantContext = Depends(get_tenant_context)
):
    if ctx.tenant_id != tid and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant write not allowed")
    async with tenant_session(tid) as session:
        created = []
        for url in body.urls:
            row = (
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge_sources (tenant_id, kind, uri, title, status)
                        VALUES (CAST(:tid AS uuid), 'url', :u, :u, 'pending')
                        RETURNING id::text
                        """
                    ),
                    {"tid": tid, "u": url},
                )
            ).first()
            created.append(row[0])
    return {"ok": True, "source_ids": created, "note": "crawl will begin shortly"}


class PersonaIn(BaseModel):
    template: str | None = None
    system_prompt: str | None = None
    voice_id: str | None = None


@router.post("/{tid}/persona")
async def set_persona(
    tid: str, body: PersonaIn, ctx: TenantContext = Depends(get_tenant_context)
):
    if ctx.tenant_id != tid and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant write not allowed")

    system_prompt = body.system_prompt
    tools = None
    if body.template and body.template in TEMPLATES:
        t = TEMPLATES[body.template]
        system_prompt = system_prompt or t["system_prompt"]
        tools = t["tools"] or TEMPLATES["home_services.hvac"]["tools"]

    if not system_prompt:
        raise HTTPException(status_code=400, detail="system_prompt or template required")

    async with tenant_session(tid) as session:
        await session.execute(
            text(
                """
                UPDATE prompt_packs
                   SET active = false
                 WHERE kind = 'voice' AND active = true
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO prompt_packs (tenant_id, name, kind, system_prompt, tools, active)
                VALUES (CAST(:tid AS uuid), 'Custom Voice', 'voice', :sp,
                        CAST(:tools AS jsonb), true)
                """
            ),
            {
                "tid": tid,
                "sp": system_prompt,
                "tools": json.dumps(tools or []),
            },
        )
    return {"ok": True}


@router.post("/{tid}/phone-trial")
async def allocate_trial_phone(
    tid: str, ctx: TenantContext = Depends(get_tenant_context)
):
    """Reserve a Twilio trial number. In production this calls the Twilio
    AvailablePhoneNumbers API and purchases; for dev we stub an allocation and
    record it on tenant.metadata.phone_numbers[]."""
    if ctx.tenant_id != tid and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant write not allowed")

    fake_number = f"+1555{tid[:7].replace('-', '')}"
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        await session.execute(
            text(
                """
                UPDATE tenants
                   SET metadata = jsonb_set(
                         metadata,
                         '{phone_numbers}',
                         COALESCE(metadata->'phone_numbers', '[]'::jsonb) || to_jsonb(:p::text)
                       )
                 WHERE id = CAST(:tid AS uuid)
                """
            ),
            {"tid": tid, "p": fake_number},
        )
        await session.commit()
    return {"ok": True, "phone_e164": fake_number, "note": "Dev-stub number; real Twilio purchase lives in M1 deploy task"}


class CheckoutIn(BaseModel):
    sku: str = "concierge.starter.monthly"
    success_url: str
    cancel_url: str


@router.post("/{tid}/checkout")
async def start_checkout(
    tid: str, body: CheckoutIn, ctx: TenantContext = Depends(get_tenant_context)
):
    if ctx.tenant_id != tid and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant write not allowed")

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{settings.credits_gateway_url}/api/pricing/{body.sku}")
            r.raise_for_status()
            price = r.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"pricing lookup failed: {e}")

        try:
            # Delegate Stripe session creation to User Service (existing convention)
            r2 = await client.post(
                f"{settings.user_service_url}/checkout",
                headers={"X-Internal-Token": settings.internal_service_token},
                json={
                    "tenant_id": tid,
                    "sku": body.sku,
                    "cost_uc": price.get("cost_uc"),
                    "unit": price.get("unit"),
                    "success_url": body.success_url,
                    "cancel_url": body.cancel_url,
                },
            )
            r2.raise_for_status()
            return r2.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"user-service checkout: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"user-service unreachable: {e}")


@router.get("/{tid}/status")
async def onboarding_status(tid: str, ctx: TenantContext = Depends(get_tenant_context)):
    if ctx.tenant_id != tid and not ctx.is_superuser:
        raise HTTPException(status_code=403, detail="cross-tenant read not allowed")
    async with tenant_session(tid) as session:
        tenant = (
            await session.execute(
                text(
                    """
                    SELECT t.status, t.plan,
                           COALESCE(jsonb_array_length(t.metadata->'phone_numbers'), 0) AS num_phones,
                           (SELECT COUNT(*) FROM knowledge_sources) AS num_sources,
                           (SELECT COUNT(*) FROM knowledge_sources WHERE status = 'indexed') AS indexed_sources,
                           (SELECT COUNT(*) FROM prompt_packs WHERE active = true AND kind = 'voice') AS num_packs
                      FROM tenants t WHERE t.id = CAST(:tid AS uuid)
                    """
                ),
                {"tid": tid},
            )
        ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")

    return {
        "status": tenant[0],
        "plan": tenant[1],
        "phone_numbers_configured": int(tenant[2]),
        "knowledge_sources": {
            "total": int(tenant[3]),
            "indexed": int(tenant[4]),
        },
        "active_voice_pack": int(tenant[5]) > 0,
        "ready_for_calls": int(tenant[2]) > 0 and int(tenant[5]) > 0,
    }
