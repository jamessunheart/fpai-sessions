"""Conversational admin — inbound-SMS intent parser + propose/confirm loop.

Flow:
  Twilio → POST /admin-sms/inbound (Form: From, Body)
  → resolve tenant via admin_phones
  → if Body matches YES/NO, apply or reject the latest pending proposal
  → else LLM-parse intent → write config_proposals row → reply with diff + "YES/NO"
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import Response
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import text

from shared.config import settings
from shared.db import SessionLocal, tenant_session
from shared.logging import get_logger
from shared.tenant_context import TenantContext, get_tenant_context

log = get_logger("tenant-api.admin-sms")
router = APIRouter(prefix="/admin-sms", tags=["admin-sms"])


INTENT_SCHEMA = """You parse SMS commands for a small-business admin into a structured diff.

Return STRICT JSON:
{
  "intent": "set_hours" | "set_persona" | "toggle_feature" | "add_phone" | "noop",
  "summary": "one short human-readable sentence",
  "diff": {"path": "...", "new": ...}
}

If the request is ambiguous or unsupported, return intent "noop" with a summary
explaining what's unclear.

Examples:
- "We're closed Sundays" → intent=set_hours, diff.path=business_hours, diff.new={"sun": []}
- "Turn on outbound campaigns" → intent=toggle_feature, diff.path=outbound_campaigns, diff.new=true
- "Change greeting to: Thanks for calling Ace Plumbing, how can I help?" →
   intent=set_persona, diff.path=system_prompt, diff.new="Thanks for calling Ace Plumbing..."
- "Add admin phone +15551234567" → intent=add_phone, diff.path=admin_phones, diff.new="+15551234567"
"""


async def _parse_intent(body: str) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {"intent": "noop", "summary": "AI parser unavailable", "diff": {}}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    r = await client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {"role": "system", "content": INTENT_SCHEMA},
            {"role": "user", "content": body},
        ],
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(r.choices[0].message.content)
    except json.JSONDecodeError:
        return {"intent": "noop", "summary": "couldn't parse", "diff": {}}


async def _tenant_by_admin_phone(from_phone: str) -> str | None:
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text("SELECT tenant_id::text FROM admin_phones WHERE phone_e164 = :p LIMIT 1"),
                {"p": from_phone},
            )
        ).first()
    return row[0] if row else None


async def _latest_pending(tenant_id: str) -> tuple[str, str, dict] | None:
    async with tenant_session(tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT id::text, intent, diff FROM config_proposals
                     WHERE status = 'pending' AND expires_at > now()
                     ORDER BY created_at DESC LIMIT 1
                    """
                )
            )
        ).first()
    return (row[0], row[1], dict(row[2])) if row else None


async def _apply_proposal(tenant_id: str, proposal_id: str, intent: str, diff: dict) -> str:
    path = diff.get("path")
    new = diff.get("new")

    async with tenant_session(tenant_id) as session:
        if intent == "toggle_feature":
            await session.execute(
                text(
                    """
                    INSERT INTO tenant_features (tenant_id, feature_key, enabled)
                    VALUES (CAST(:tid AS uuid), :k, :en)
                    ON CONFLICT (tenant_id, feature_key) DO UPDATE
                      SET enabled = EXCLUDED.enabled, updated_at = now()
                    """
                ),
                {"tid": tenant_id, "k": path, "en": bool(new)},
            )
        elif intent == "set_hours":
            await session.execute(
                text(
                    """
                    UPDATE tenants
                       SET business_hours = business_hours || CAST(:h AS jsonb)
                     WHERE id = CAST(:tid AS uuid)
                    """
                ),
                {"tid": tenant_id, "h": json.dumps(new or {})},
            )
        elif intent == "set_persona":
            await session.execute(
                text(
                    """
                    UPDATE prompt_packs
                       SET system_prompt = :sp, updated_at = now()
                     WHERE kind = 'voice' AND active = true
                    """
                ),
                {"sp": str(new or "")},
            )
        elif intent == "add_phone":
            await session.execute(
                text(
                    """
                    INSERT INTO admin_phones (tenant_id, phone_e164)
                    VALUES (CAST(:tid AS uuid), :p)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"tid": tenant_id, "p": str(new or "")},
            )
        else:
            return "Unknown intent; nothing applied."

        await session.execute(
            text(
                """
                UPDATE config_proposals
                   SET status = 'confirmed', confirmed_at = now()
                 WHERE id = CAST(:id AS uuid)
                """
            ),
            {"id": proposal_id},
        )
    return "Applied."


def _twiml_message(msg: str) -> Response:
    from xml.sax.saxutils import escape as _esc

    xml = f"<Response><Message>{_esc(msg)}</Message></Response>"
    return Response(content=xml, media_type="application/xml")


@router.post("/inbound")
async def inbound_sms(From: str = Form(...), Body: str = Form(...)):
    tenant_id = await _tenant_by_admin_phone(From)
    if not tenant_id:
        return _twiml_message(
            "This number is not authorized to manage a Concierge tenant. Visit your dashboard to add it."
        )

    normalized = Body.strip().upper()

    if re.fullmatch(r"(YES|Y|CONFIRM|OK)", normalized):
        pending = await _latest_pending(tenant_id)
        if not pending:
            return _twiml_message("No pending change to confirm.")
        status_msg = await _apply_proposal(tenant_id, *pending)
        return _twiml_message(f"{status_msg} You can send another change anytime.")

    if re.fullmatch(r"(NO|N|CANCEL|STOP)", normalized):
        async with tenant_session(tenant_id) as session:
            await session.execute(
                text(
                    """
                    UPDATE config_proposals SET status = 'rejected'
                     WHERE status = 'pending'
                    """
                )
            )
        return _twiml_message("Cancelled. No changes applied.")

    parsed = await _parse_intent(Body)
    intent = parsed.get("intent", "noop")
    diff = parsed.get("diff", {}) or {}
    summary = parsed.get("summary", "").strip()

    if intent == "noop" or not diff:
        return _twiml_message(
            summary
            or "I didn't catch a specific change. Examples: 'We're closed Sundays', "
            "'Turn on outbound', 'Change greeting to: Hello from Ace Plumbing'."
        )

    async with tenant_session(tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO config_proposals
                      (tenant_id, proposed_by, channel, intent, diff, summary)
                    VALUES
                      (CAST(:tid AS uuid), :from, 'sms', :int, CAST(:d AS jsonb), :sum)
                    RETURNING id::text
                    """
                ),
                {
                    "tid": tenant_id,
                    "from": From,
                    "int": intent,
                    "d": json.dumps(diff),
                    "sum": summary,
                },
            )
        ).first()
    return _twiml_message(
        f"Proposal: {summary}\n\nReply YES to apply, NO to cancel. (expires in 10 min)"
    )


class ProposalOut(BaseModel):
    id: str
    intent: str
    summary: str
    diff: dict
    status: str
    expires_at: str
    created_at: str


@router.get("/proposals", response_model=list[ProposalOut])
async def list_proposals(ctx: TenantContext = Depends(get_tenant_context)):
    async with tenant_session(ctx.tenant_id) as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id::text, intent, summary, diff, status,
                           expires_at::text, created_at::text
                      FROM config_proposals
                     ORDER BY created_at DESC LIMIT 50
                    """
                )
            )
        ).all()
    return [
        ProposalOut(
            id=r[0], intent=r[1], summary=r[2], diff=dict(r[3] or {}),
            status=r[4], expires_at=r[5], created_at=r[6]
        )
        for r in rows
    ]
