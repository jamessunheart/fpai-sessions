"""Tool execution — handlers for the function-calls our AI voice can invoke.

Each handler returns a dict that is echoed back to the model as a
``response.function_call_output``. Side effects (DB writes, external calls) are
performed in-handler so the audit trail stays inside the conversation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text

from shared.config import settings
from shared.db import tenant_session
from shared.events import Event, Topics, publish


async def book_appointment(tenant_id: str, conversation_id: str, args: dict[str, Any]) -> dict:
    """Create a ``bookings`` row. External calendar sync is deferred to a worker."""
    required = {"service", "window", "phone"}
    if not required.issubset(args):
        return {"ok": False, "error": f"missing: {sorted(required - set(args))}"}

    async with tenant_session(tenant_id) as session:
        contact_row = (
            await session.execute(
                text(
                    """
                    INSERT INTO contacts (tenant_id, phone_e164, name, metadata)
                    VALUES (CAST(:tid AS uuid), :p, :n, CAST(:md AS jsonb))
                    ON CONFLICT (tenant_id, phone_e164) DO UPDATE
                      SET name = COALESCE(EXCLUDED.name, contacts.name)
                    RETURNING id::text
                    """
                ),
                {
                    "tid": tenant_id,
                    "p": args["phone"],
                    "n": args.get("name"),
                    "md": json.dumps({"source": "voice_concierge"}),
                },
            )
        ).first()
        contact_id = contact_row[0]

        booking = (
            await session.execute(
                text(
                    """
                    INSERT INTO bookings
                      (tenant_id, conversation_id, contact_id, service_type,
                       address, scheduled_start, notes)
                    VALUES
                      (CAST(:tid AS uuid), CAST(:cid AS uuid), CAST(:cnt AS uuid),
                       :svc, CAST(:addr AS jsonb), :start, :notes)
                    RETURNING id::text
                    """
                ),
                {
                    "tid": tenant_id,
                    "cid": conversation_id,
                    "cnt": contact_id,
                    "svc": args["service"],
                    "addr": json.dumps({"raw": args.get("address", "")}),
                    "start": _parse_window(args["window"]),
                    "notes": args.get("notes", ""),
                },
            )
        ).first()
        booking_id = booking[0]

        await session.execute(
            text(
                """
                UPDATE conversations
                   SET outcome = 'booked', intent = COALESCE(intent, 'book_appointment')
                 WHERE id = CAST(:cid AS uuid)
                """
            ),
            {"cid": conversation_id},
        )
        await publish(
            session,
            Event(
                topic=Topics.BOOKING_CREATED,
                tenant_id=tenant_id,
                payload={"booking_id": booking_id, "conversation_id": conversation_id},
            ),
        )
    return {"ok": True, "booking_id": booking_id, "confirmation": f"Booked for {args['window']}"}


async def get_service_estimate(tenant_id: str, args: dict[str, Any]) -> dict:
    """Static ballpark estimate — replace with per-tenant pricing lookup later."""
    book = {
        "diagnostic":      "$89 trip charge, applied toward repair",
        "ac_tuneup":       "$129 flat",
        "furnace_tuneup":  "$149 flat",
        "ac_repair":       "$180-$650 depending on part",
        "furnace_repair":  "$200-$900 depending on part",
        "install_ac":      "$5,500-$9,000 typical range",
        "install_furnace": "$4,500-$8,500 typical range",
    }
    key = args.get("service", "").lower().replace(" ", "_").replace("-", "_")
    estimate = book.get(key, "Our technician will provide a precise estimate on site after diagnosis")
    return {"ok": True, "service": args.get("service"), "estimate": estimate}


async def escalate_to_human(
    tenant_id: str, conversation_id: str, args: dict[str, Any]
) -> dict:
    """Request a human pickup via handoff-broker. Returns escalation_id so the
    voice loop can wait/poll and issue a warm-transfer TwiML update."""
    reason = args.get("reason", "caller requested human")
    skills = args.get("skills_required") or ["voice_general"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            f"{settings.handoff_broker_url}/escalations",
            headers={
                "X-Internal-Token": settings.internal_service_token,
                "X-Tenant-Id": tenant_id,
            },
            json={
                "conversation_id": conversation_id,
                "reason": reason,
                "skills_required": skills,
                "priority": "high",
                "sla_seconds": 60,
            },
        )
        r.raise_for_status()
        return {"ok": True, **r.json()}


async def log_utterance(
    tenant_id: str,
    conversation_id: str,
    actor_type: str,
    text_payload: str,
) -> None:
    """Append a spoken line to conversation_events + transcripts."""
    async with tenant_session(tenant_id) as session:
        await session.execute(
            text(
                """
                INSERT INTO conversation_events
                  (tenant_id, conversation_id, event_type, actor_type, payload)
                VALUES
                  (CAST(:tid AS uuid), CAST(:cid AS uuid), 'utterance',
                   :at, CAST(:p AS jsonb))
                """
            ),
            {
                "tid": tenant_id,
                "cid": conversation_id,
                "at": actor_type,
                "p": json.dumps({"text": text_payload}),
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO transcripts (conversation_id, tenant_id, text)
                VALUES (CAST(:cid AS uuid), CAST(:tid AS uuid), :t)
                ON CONFLICT (conversation_id) DO UPDATE
                  SET text = transcripts.text || E'\n' || EXCLUDED.text,
                      updated_at = now()
                """
            ),
            {
                "cid": conversation_id,
                "tid": tenant_id,
                "t": f"[{actor_type}] {text_payload}",
            },
        )


def _parse_window(window: str) -> datetime:
    """Parse free-text scheduling hints. Heuristic; production parses via LLM.

    Falls back to now+1day if we can't make sense of the input.
    """
    from dateutil import parser

    try:
        dt = parser.parse(window, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        now = datetime.now(timezone.utc)
        return now.replace(hour=now.hour, minute=0)


TOOL_DISPATCH = {
    "book_appointment": lambda tid, cid, args: book_appointment(tid, cid, args),
    "get_service_estimate": lambda tid, cid, args: get_service_estimate(tid, args),
    "escalate_to_human": lambda tid, cid, args: escalate_to_human(tid, cid, args),
}


async def dispatch_tool(
    name: str, tenant_id: str, conversation_id: str, args: dict[str, Any]
) -> dict:
    if name not in TOOL_DISPATCH:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return await TOOL_DISPATCH[name](tenant_id, conversation_id, args)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
