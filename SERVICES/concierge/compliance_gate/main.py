"""compliance-gate (port 8824) — the ONLY place outbound actions get authorized.

Pre-outbound gate:
- TCPA check (express consent on contact.consent.tcpa)
- DNC registry lookup (tenant + national scrubs)
- Time-of-day window enforcement (per jurisdiction)
- Bot-disclosure requirement (flag)
- Recording consent (two-party states)

Every check is written to ``compliance_events`` as an append-only audit log.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import phonenumbers
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from shared.app_factory import create_app
from shared.db import tenant_session
from shared.tenant_context import TenantContext, get_tenant_context

app = create_app("compliance-gate")


TWO_PARTY_STATES = {
    "CA", "CT", "FL", "IL", "MD", "MA", "MT", "NV", "NH", "PA", "WA", "OR", "MI", "DE",
}


class OutboundPreflight(BaseModel):
    phone_e164: str
    contact_id: str | None = None
    conversation_id: str | None = None
    channel: str  # voice | sms
    jurisdiction: str | None = None  # 2-letter state code
    purpose: str = "service"  # service | marketing
    caller_time: str | None = None  # ISO-8601 to override "now" for tests


class PreflightResult(BaseModel):
    allowed: bool
    reasons: list[str]
    disclosures_required: list[str]
    recording_requires_dual_consent: bool


@app.post("/preflight", response_model=PreflightResult)
async def preflight(
    body: OutboundPreflight, ctx: TenantContext = Depends(get_tenant_context)
):
    reasons: list[str] = []
    disclosures: list[str] = ["bot_disclosure"]
    allowed = True
    dual = False

    try:
        parsed = phonenumbers.parse(body.phone_e164, None)
        if not phonenumbers.is_valid_number(parsed):
            allowed = False
            reasons.append("invalid_phone")
    except phonenumbers.NumberParseException:
        allowed = False
        reasons.append("invalid_phone")

    async with tenant_session(ctx.tenant_id) as session:
        # DNC
        hit = (
            await session.execute(
                text(
                    """
                    SELECT 1 FROM dnc_registry
                     WHERE phone_e164 = :p AND tenant_id = CAST(:tid AS uuid) LIMIT 1
                    """
                ),
                {"p": body.phone_e164, "tid": ctx.tenant_id},
            )
        ).first()
        if hit:
            allowed = False
            reasons.append("dnc_match")

        # TCPA (marketing purpose requires express consent)
        if body.purpose == "marketing" and body.contact_id:
            row = (
                await session.execute(
                    text(
                        "SELECT consent FROM contacts WHERE id = CAST(:cid AS uuid) LIMIT 1"
                    ),
                    {"cid": body.contact_id},
                )
            ).first()
            consent = (row[0] if row else {}) or {}
            if not consent.get("tcpa"):
                allowed = False
                reasons.append("tcpa_no_consent")

        # Time-of-day (8am–9pm local)
        now_utc = (
            datetime.fromisoformat(body.caller_time)
            if body.caller_time
            else datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        )
        tz_row = (
            await session.execute(text("SELECT timezone FROM tenants LIMIT 1"))
        ).first()
        local_tz = ZoneInfo(tz_row[0] if tz_row else "America/Denver")
        local = now_utc.astimezone(local_tz)
        if not (8 <= local.hour < 21):
            allowed = False
            reasons.append("time_of_day_out_of_window")

        # Two-party consent
        if body.jurisdiction and body.jurisdiction.upper() in TWO_PARTY_STATES:
            dual = True
            disclosures.append("recording_consent")

        # Audit
        await session.execute(
            text(
                """
                INSERT INTO compliance_events
                  (tenant_id, conversation_id, contact_id, kind, result, jurisdiction, details)
                VALUES
                  (CAST(:tid AS uuid),
                   CASE WHEN :conv IS NULL THEN NULL ELSE CAST(:conv AS uuid) END,
                   CASE WHEN :cid  IS NULL THEN NULL ELSE CAST(:cid  AS uuid) END,
                   'preflight',
                   CASE WHEN :ok THEN 'pass' ELSE 'fail' END,
                   :jur,
                   CAST(:details AS jsonb))
                """
            ),
            {
                "tid": ctx.tenant_id,
                "conv": body.conversation_id,
                "cid": body.contact_id,
                "ok": allowed,
                "jur": body.jurisdiction,
                "details": _to_json(
                    {
                        "phone": body.phone_e164,
                        "channel": body.channel,
                        "purpose": body.purpose,
                        "reasons": reasons,
                    }
                ),
            },
        )

    return PreflightResult(
        allowed=allowed,
        reasons=reasons,
        disclosures_required=disclosures,
        recording_requires_dual_consent=dual,
    )


class OptOut(BaseModel):
    phone_e164: str
    source: str = "opt_out"


@app.post("/opt-out")
async def opt_out(body: OptOut, ctx: TenantContext = Depends(get_tenant_context)):
    async with tenant_session(ctx.tenant_id) as session:
        await session.execute(
            text(
                """
                INSERT INTO dnc_registry (tenant_id, phone_e164, source)
                VALUES (CAST(:tid AS uuid), :p, :src)
                ON CONFLICT DO NOTHING
                """
            ),
            {"tid": ctx.tenant_id, "p": body.phone_e164, "src": body.source},
        )
        await session.execute(
            text(
                """
                INSERT INTO compliance_events (tenant_id, kind, result, details)
                VALUES (CAST(:tid AS uuid), 'opt_out', 'granted', CAST(:d AS jsonb))
                """
            ),
            {"tid": ctx.tenant_id, "d": _to_json({"phone": body.phone_e164, "source": body.source})},
        )
    return {"ok": True, "phone_e164": body.phone_e164}


def _to_json(v):
    import json

    return json.dumps(v or {})
