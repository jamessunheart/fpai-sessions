"""handoff-broker (port 8821) — escalation queue + agent live channel.

Responsibilities:
- Accept escalation requests from voice-router or agent console
- Match escalations → available agent via skills-mesh
- Track SLA timers; re-offer on miss
- Serve a WebSocket to agents for live conversation feed
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import text

from shared.app_factory import create_app
from shared.config import settings
from shared.db import tenant_session
from shared.events import Event, Topics, publish
from shared.tenant_context import TenantContext, get_tenant_context

app = create_app("handoff-broker")


# In-memory agent sockets keyed by agent_id
_agent_sockets: dict[str, WebSocket] = {}
_offer_locks: dict[str, asyncio.Lock] = {}


class EscalationRequest(BaseModel):
    conversation_id: str
    reason: str
    skills_required: list[str] = Field(default_factory=list)
    priority: str = "normal"
    sla_seconds: int = 90


class EscalationOut(BaseModel):
    id: str
    status: str
    offered_to: str | None = None
    sla_deadline_at: str | None = None


@app.post("/escalations", response_model=EscalationOut, status_code=201)
async def create_escalation(
    body: EscalationRequest, ctx: TenantContext = Depends(get_tenant_context)
):
    deadline = datetime.now(timezone.utc) + timedelta(seconds=body.sla_seconds)

    async with tenant_session(ctx.tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO escalations
                      (tenant_id, conversation_id, reason, skills_required, priority, sla_deadline_at)
                    VALUES
                      (CAST(:tid AS uuid), CAST(:cid AS uuid), :r, :sk, :pri, :sla)
                    RETURNING id::text, status, sla_deadline_at
                    """
                ),
                {
                    "tid": ctx.tenant_id,
                    "cid": body.conversation_id,
                    "r": body.reason,
                    "sk": body.skills_required,
                    "pri": body.priority,
                    "sla": deadline,
                },
            )
        ).first()
        await publish(
            session,
            Event(
                topic=Topics.ESCALATION_REQUESTED,
                tenant_id=ctx.tenant_id,
                payload={
                    "escalation_id": row[0],
                    "conversation_id": body.conversation_id,
                    "skills_required": body.skills_required,
                    "priority": body.priority,
                },
            ),
        )

    asyncio.create_task(_try_match(ctx.tenant_id, row[0], body.skills_required))

    return EscalationOut(
        id=row[0],
        status=row[1],
        sla_deadline_at=row[2].isoformat() if row[2] else None,
    )


async def _try_match(tenant_id: str, escalation_id: str, skills: list[str]) -> None:
    """Ask skills-mesh for a candidate agent, then offer via WebSocket."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.skills_mesh_url}/match",
                headers={
                    "X-Internal-Token": settings.internal_service_token,
                    "X-Tenant-Id": tenant_id,
                },
                json={"skills_required": skills, "exclude": []},
            )
            r.raise_for_status()
            candidate = r.json().get("agent_id")
    except Exception:
        candidate = None

    if not candidate:
        return

    async with tenant_session(tenant_id) as session:
        await session.execute(
            text(
                """
                UPDATE escalations
                   SET status = 'offered', offered_to = CAST(:aid AS uuid)
                 WHERE id = CAST(:eid AS uuid)
                """
            ),
            {"aid": candidate, "eid": escalation_id},
        )

    sock = _agent_sockets.get(candidate)
    if sock is not None:
        try:
            await sock.send_text(
                json.dumps({"type": "offer", "escalation_id": escalation_id})
            )
        except Exception:
            pass


class EscalationAccept(BaseModel):
    escalation_id: str
    agent_id: str


@app.post("/escalations/{escalation_id}/accept")
async def accept_escalation(
    escalation_id: str,
    body: EscalationAccept,
    ctx: TenantContext = Depends(get_tenant_context),
):
    lock = _offer_locks.setdefault(escalation_id, asyncio.Lock())
    async with lock:
        async with tenant_session(ctx.tenant_id) as session:
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE escalations
                           SET status = 'accepted',
                               accepted_by = CAST(:aid AS uuid),
                               accepted_at = now()
                         WHERE id = CAST(:eid AS uuid)
                           AND status IN ('queued','offered')
                        RETURNING id::text, conversation_id::text
                        """
                    ),
                    {"aid": body.agent_id, "eid": escalation_id},
                )
            ).first()
            if not row:
                raise HTTPException(status_code=409, detail="already accepted or closed")
            await publish(
                session,
                Event(
                    topic=Topics.ESCALATION_ACCEPTED,
                    tenant_id=ctx.tenant_id,
                    payload={"escalation_id": row[0], "agent_id": body.agent_id},
                ),
            )
    return {"ok": True, "escalation_id": row[0], "conversation_id": row[1]}


@app.get("/escalations/{escalation_id}")
async def get_escalation(
    escalation_id: str, ctx: TenantContext = Depends(get_tenant_context)
):
    async with tenant_session(ctx.tenant_id) as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT e.id::text, e.status, e.offered_to::text, e.accepted_by::text,
                           a.phone AS agent_phone
                      FROM escalations e
                 LEFT JOIN agents a ON a.id = e.accepted_by
                     WHERE e.id = CAST(:eid AS uuid)
                     LIMIT 1
                    """
                ),
                {"eid": escalation_id},
            )
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="escalation not found")
    return {
        "id": row[0],
        "status": row[1],
        "offered_to": row[2],
        "accepted_by": row[3],
        "agent_phone": row[4],
    }


@app.websocket("/agents/{agent_id}/ws")
async def agent_socket(ws: WebSocket, agent_id: str):
    await ws.accept()
    _agent_sockets[agent_id] = ws
    try:
        await ws.send_text(json.dumps({"type": "hello", "agent_id": agent_id}))
        while True:
            msg = await ws.receive_text()
            # Agents can send typed events: set_status, accept, draft_edit, ...
            data = json.loads(msg)
            if data.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _agent_sockets.pop(agent_id, None)
