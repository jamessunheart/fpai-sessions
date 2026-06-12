"""outbound-engine (port 8823) — campaigns, lead sourcing, cadence.

Every touch MUST pass compliance-gate.preflight() before dispatch.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from shared.app_factory import create_app
from shared.config import settings
from shared.db import tenant_session
from shared.logging import get_logger
from shared.tenant_context import TenantContext, get_tenant_context

app = create_app("outbound-engine")
log = get_logger("outbound-engine")


class CampaignCreate(BaseModel):
    name: str
    goal: str
    cadence: list[dict] = Field(default_factory=list)
    targeting: dict = Field(default_factory=dict)
    budget_uc: float | None = None


@app.post("/campaigns", status_code=201)
async def create_campaign(body: CampaignCreate, ctx: TenantContext = Depends(get_tenant_context)):
    async with tenant_session(ctx.tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO campaigns
                      (tenant_id, name, goal, cadence, targeting, budget_uc)
                    VALUES
                      (CAST(:tid AS uuid), :n, :g,
                       CAST(:cd AS jsonb), CAST(:tg AS jsonb), :b)
                    RETURNING id::text
                    """
                ),
                {
                    "tid": ctx.tenant_id,
                    "n": body.name,
                    "g": body.goal,
                    "cd": _to_json(body.cadence),
                    "tg": _to_json(body.targeting),
                    "b": body.budget_uc,
                },
            )
        ).first()
    return {"id": row[0]}


class TouchRequest(BaseModel):
    campaign_contact_id: str


@app.post("/touch")
async def send_touch(body: TouchRequest, ctx: TenantContext = Depends(get_tenant_context)):
    """Dispatch the next step for a campaign contact (gated through compliance)."""
    async with tenant_session(ctx.tenant_id) as session:
        cc = (
            await session.execute(
                text(
                    """
                    SELECT id::text, campaign_id::text, contact_id::text, phone_e164, email, step_idx
                      FROM campaign_contacts
                     WHERE id = CAST(:cid AS uuid) AND status = 'pending'
                     LIMIT 1
                    """
                ),
                {"cid": body.campaign_contact_id},
            )
        ).first()
        if not cc:
            raise HTTPException(status_code=404, detail="campaign contact not found or not pending")

        camp = (
            await session.execute(
                text("SELECT cadence FROM campaigns WHERE id = CAST(:cid AS uuid)"),
                {"cid": cc[1]},
            )
        ).first()
        cadence = camp[0] or []
        if cc[5] >= len(cadence):
            await session.execute(
                text(
                    "UPDATE campaign_contacts SET status = 'complete' "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": cc[0]},
            )
            return {"ok": True, "status": "complete"}

        step = cadence[cc[5]]

    # Compliance gate — MANDATORY
    if step.get("channel") in ("sms", "voice") and cc[3]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.compliance_gate_url}/preflight",
                headers={
                    "X-Internal-Token": settings.internal_service_token,
                    "X-Tenant-Id": ctx.tenant_id,
                },
                json={
                    "phone_e164": cc[3],
                    "contact_id": cc[2],
                    "channel": step["channel"],
                    "purpose": step.get("purpose", "service"),
                    "jurisdiction": step.get("jurisdiction"),
                },
            )
            r.raise_for_status()
            result = r.json()
        if not result["allowed"]:
            async with tenant_session(ctx.tenant_id) as session:
                await session.execute(
                    text(
                        "UPDATE campaign_contacts SET status = 'unsubscribed', "
                        "metadata = metadata || CAST(:m AS jsonb) "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": cc[0], "m": _to_json({"blocked": result})},
                )
            return {"ok": False, "reason": result["reasons"]}

    # Dispatch through channel adapter
    dispatch_ok = True
    dispatch_note: dict = {}
    if step.get("channel") == "sms" and cc[3]:
        ok, note = await _send_sms(cc[3], step.get("body", ""))
        dispatch_ok = ok
        dispatch_note = note
    elif step.get("channel") == "email" and cc[4]:
        dispatch_note = {"skipped": "email adapter not yet implemented (M4)"}
    elif step.get("channel") == "voice" and cc[3]:
        dispatch_note = {"skipped": "voice dispatch wired through Twilio-outbound in M4"}

    async with tenant_session(ctx.tenant_id) as session:
        await session.execute(
            text(
                """
                UPDATE campaign_contacts
                   SET step_idx = step_idx + 1,
                       last_touch_at = :now,
                       status = CASE WHEN step_idx + 1 >= :total THEN 'complete' ELSE 'pending' END
                 WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": cc[0], "now": datetime.now(timezone.utc), "total": len(cadence)},
        )
    return {
        "ok": dispatch_ok,
        "next_step": cc[5] + 1,
        "dispatch": dispatch_note,
    }


# ---------------------- Lead sourcing ------------------------------

class LeadImport(BaseModel):
    campaign_id: str
    leads: list[dict]  # [{name, phone_e164, email, metadata}, ...]


@app.post("/lead-sources/import")
async def import_leads(
    body: LeadImport, ctx: TenantContext = Depends(get_tenant_context)
):
    """Bulk-insert leads into a campaign. Use this for Apollo/Hunter exports
    or any already-scraped contact list. Each lead becomes a contact +
    campaign_contact at step 0, ready for the scheduler to pick up."""
    if not body.leads:
        return {"imported": 0}
    async with tenant_session(ctx.tenant_id) as session:
        count = 0
        for lead in body.leads:
            phone = lead.get("phone_e164")
            email = lead.get("email")
            if not (phone or email):
                continue

            contact = (
                await session.execute(
                    text(
                        """
                        INSERT INTO contacts (tenant_id, phone_e164, email, name, metadata)
                        VALUES (CAST(:tid AS uuid), :p, :e, :n, CAST(:m AS jsonb))
                        ON CONFLICT (tenant_id, phone_e164) DO UPDATE
                          SET email = COALESCE(contacts.email, EXCLUDED.email),
                              name  = COALESCE(contacts.name,  EXCLUDED.name)
                        RETURNING id::text
                        """
                    ),
                    {
                        "tid": ctx.tenant_id,
                        "p": phone,
                        "e": email,
                        "n": lead.get("name"),
                        "m": json.dumps(lead.get("metadata", {"source": "lead-import"})),
                    },
                )
            ).first()

            await session.execute(
                text(
                    """
                    INSERT INTO campaign_contacts
                      (campaign_id, tenant_id, contact_id, phone_e164, email,
                       step_idx, next_run_at, status)
                    VALUES
                      (CAST(:cid AS uuid), CAST(:tid AS uuid), CAST(:ct AS uuid),
                       :p, :e, 0, now(), 'pending')
                    """
                ),
                {
                    "cid": body.campaign_id,
                    "tid": ctx.tenant_id,
                    "ct": contact[0],
                    "p": phone,
                    "e": email,
                },
            )
            count += 1
    return {"imported": count}


@app.post("/lead-sources/apollo/search")
async def apollo_search(
    query: dict, ctx: TenantContext = Depends(get_tenant_context)
):
    """Proxy an Apollo.io people-search and return raw results. The caller
    decides which to import via /lead-sources/import. Requires APOLLO_API_KEY."""
    if not settings.apollo_api_key:
        raise HTTPException(status_code=503, detail="apollo_api_key not configured")
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            "https://api.apollo.io/v1/mixed_people/search",
            json={**query, "api_key": settings.apollo_api_key},
        )
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"apollo: {r.text}")
        return r.json()


# ---------------------- Channel adapters ---------------------------

async def _send_sms(to_e164: str, body: str) -> tuple[bool, dict]:
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_default_from
        and body
    ):
        return False, {"skipped": "twilio not configured or empty body"}
    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(
            from_=settings.twilio_default_from, to=to_e164, body=body
        )
        return True, {"sid": msg.sid, "status": msg.status}
    except Exception as e:
        log.warn("twilio_sms_failed", err=str(e))
        return False, {"error": str(e)}


def _to_json(v):
    return json.dumps(v if v is not None else {})
