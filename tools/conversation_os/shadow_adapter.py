#!/usr/bin/env python3
"""Conversation OS — shadow Event ingestion adapter (proof-1).

Observes an email (fixture or live IMAP message dict), normalizes it into ONE
canonical, provider-agnostic, immutable, versioned Event, and appends it to an
append-only store. Emits a trace_id. Does NOT mutate rooms, reply, or promote
to Brain — those boundaries are intentionally absent here (see EMAIL_ARCHITECTURE
§5a and the two-gate promotion note).

Reversible + local by default: writes only to events.jsonl under the given store
dir. No network, no DNS, no live mailbox required for the fixture path.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
DEFAULT_STORE = Path(__file__).resolve().parent / "events.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dedup_key(source: str, message_id: str) -> str:
    """Stable idempotency key so the same message never yields two Events."""
    return hashlib.sha256(f"{source}:{message_id}".encode()).hexdigest()


@dataclass(frozen=True)
class Event:
    event_id: str
    schema_version: str
    source: str            # provider-agnostic FIELD, not shape ("gmail", "imap", ...)
    type: str              # "email.received"
    occurred_at: str       # from the message (Date header)
    ingested_at: str       # when we stored it
    trace_id: str
    dedup_key: str
    tenant_id: str | None
    payload: dict[str, Any] = field(default_factory=dict)


def normalize_email(msg: dict[str, Any], *, source: str = "imap",
                    tenant_id: str | None = None) -> Event:
    """Pure function: raw email dict -> canonical Event. No I/O."""
    message_id = str(msg.get("message_id") or msg.get("Message-ID") or uuid.uuid4())
    return Event(
        event_id=str(uuid.uuid4()),
        schema_version=SCHEMA_VERSION,
        source=source,
        type="email.received",
        occurred_at=str(msg.get("date") or msg.get("Date") or _utc()),
        ingested_at=_utc(),
        trace_id=f"trace-{uuid.uuid4().hex[:12]}",
        dedup_key=_dedup_key(source, message_id),
        tenant_id=tenant_id,
        payload={
            "original_recipient": msg.get("to") or msg.get("delivered_to"),
            "sender_identity": (msg.get("to") or "").split("@")[-1] or None,
            "from": msg.get("from"),
            "thread_id": msg.get("thread_id"),
            "message_id": message_id,
            "subject": msg.get("subject"),
            "labels": msg.get("labels", []),
            # Router-fillable, intentionally null at ingest:
            "project": None, "intent": None, "person": None,
        },
    )


def _already_ingested(store: Path, dedup_key: str) -> bool:
    if not store.exists():
        return False
    for line in store.read_text().splitlines():
        if not line.strip():
            continue
        try:
            if json.loads(line).get("dedup_key") == dedup_key:
                return True
        except json.JSONDecodeError:
            continue
    return False


def append_event(event: Event, store: Path = DEFAULT_STORE) -> tuple[bool, Event]:
    """Append-only + idempotent. Returns (written, event). Never mutates prior lines."""
    store.parent.mkdir(parents=True, exist_ok=True)
    if _already_ingested(store, event.dedup_key):
        return (False, event)  # exactly-once: same message never double-emits
    with store.open("a") as fh:
        fh.write(json.dumps(asdict(event)) + "\n")
    return (True, event)


def ingest(msg: dict[str, Any], *, source: str = "imap",
           tenant_id: str | None = None,
           store: Path = DEFAULT_STORE) -> tuple[bool, Event]:
    """Observe one message -> persist exactly one Event. The whole shadow path."""
    return append_event(normalize_email(msg, source=source, tenant_id=tenant_id), store)


def replay(store: Path = DEFAULT_STORE) -> list[dict[str, Any]]:
    """Rebuild a projection by replaying the stream — proves derived state is disposable."""
    if not store.exists():
        return []
    return [json.loads(l) for l in store.read_text().splitlines() if l.strip()]


if __name__ == "__main__":
    import sys
    # Fixture golden-trace: no live mail, no DNS. Proves the Event model end-to-end.
    fixture = {
        "message_id": "<golden-trace-001@example.com>",
        "date": "2026-07-10T18:00:00Z",
        "to": "james@jamesrickstinson.com",
        "from": "prospect@example.com",
        "subject": "Does the Conversation OS actually work?",
        "labels": ["inbound"],
    }
    store = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STORE
    written, ev = ingest(fixture, source="fixture", store=store)
    print("=== GOLDEN TRACE (proof-1) ===")
    print(json.dumps(asdict(ev), indent=2))
    print(f"written={written} (False = idempotent dedup hit)")
    print(f"store={store}  total_events={len(replay(store))}")
