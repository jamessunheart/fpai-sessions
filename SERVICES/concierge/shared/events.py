"""Event bus.

v1: Postgres ``NOTIFY concierge_events, '<json>'`` + ``event_outbox`` for durability.
v2 upgrade path: Redis Streams — same publish API, different transport.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# --- Topic constants (keep in sync with docs/events.md) ---
class Topics:
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_UPDATED = "conversation.updated"
    CONVERSATION_CLOSED = "conversation.closed"
    UTTERANCE = "conversation.utterance"
    TOOL_CALL = "conversation.tool_call"
    ESCALATION_REQUESTED = "escalation.requested"
    ESCALATION_ACCEPTED = "escalation.accepted"
    ESCALATION_COMPLETED = "escalation.completed"
    BOOKING_CREATED = "booking.created"
    BOOKING_UPDATED = "booking.updated"
    COMPLIANCE_CHECK = "compliance.check"
    CAMPAIGN_TOUCH = "campaign.touch"
    AGENT_DRAFT_EDITED = "agent.draft_edited"
    AGENT_RATED = "agent.rated"


@dataclass
class Event:
    topic: str
    tenant_id: str | None
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_id": self.event_id,
                "topic": self.topic,
                "tenant_id": self.tenant_id,
                "occurred_at": self.occurred_at,
                "payload": self.payload,
            }
        )


async def publish(session: AsyncSession, event: Event) -> None:
    """Write to outbox + NOTIFY the channel. Safe within an RLS-scoped session."""
    await session.execute(
        text(
            """
            INSERT INTO event_outbox (tenant_id, topic, payload)
            VALUES (CAST(:tid AS uuid), :topic, CAST(:payload AS jsonb))
            """
        ),
        {
            "tid": event.tenant_id,
            "topic": event.topic,
            "payload": json.dumps(event.payload),
        },
    )
    await session.execute(text("SELECT pg_notify('concierge_events', :p)"), {"p": event.to_json()})
