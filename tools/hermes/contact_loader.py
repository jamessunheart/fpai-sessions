#!/usr/bin/env python3
"""Contact-pool loaders for Hermes outreach channels."""
from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ContactRecord:
    id: str
    name: str
    channel: str
    contact: str
    wa_id: str | None
    email: str | None
    tg_handle: str | None
    source: str
    notes: str
    status: str
    created_at: str


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_channel(value: str) -> str:
    channel = str(value or "").strip().lower()
    aliases = {"wa": "whatsapp", "telegram": "telegram", "tg": "telegram", "email": "email"}
    return aliases.get(channel, channel)


def _record_from_row(row: dict[str, Any], *, source: str, created_at: str) -> ContactRecord:
    channel = _normalize_channel(str(row.get("channel") or ""))
    contact = str(row.get("contact") or row.get("wa_id") or row.get("email") or row.get("tg_handle") or "").strip()
    if not channel:
        raise ValueError("channel is required")
    if not contact:
        raise ValueError("contact is required")
    return ContactRecord(
        id=str(row.get("id") or f"contact_{uuid.uuid4().hex[:12]}"),
        name=str(row.get("name") or "").strip(),
        channel=channel,
        contact=contact,
        wa_id=contact if channel == "whatsapp" else (str(row.get("wa_id") or "").strip() or None),
        email=contact if channel == "email" else (str(row.get("email") or "").strip() or None),
        tg_handle=contact if channel == "telegram" else (str(row.get("tg_handle") or "").strip() or None),
        source=str(row.get("source") or source),
        notes=str(row.get("notes") or ""),
        status=str(row.get("status") or "pending"),
        created_at=str(row.get("created_at") or created_at),
    )


def load_contacts_manual(list_of_dicts: Iterable[dict[str, Any]], *, source: str = "manual") -> list[ContactRecord]:
    created_at = utc_stamp()
    return [_record_from_row(row, source=source, created_at=created_at) for row in list_of_dicts]


def load_contacts_from_csv(path: str | Path, *, source: str = "csv") -> list[ContactRecord]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"name", "channel", "contact", "notes"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError("missing CSV columns: " + ", ".join(sorted(missing)))
        return load_contacts_manual(reader, source=source)


def insert_contact_pool(conn: Any, records: Iterable[ContactRecord]) -> int:
    inserted = 0
    with conn.cursor() as cur:
        for record in records:
            cur.execute(
                """
                INSERT INTO brain_index.contact_pool
                    (id, name, wa_id, email, tg_handle, channel, source, notes, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    record.id,
                    record.name,
                    record.wa_id,
                    record.email,
                    record.tg_handle,
                    record.channel,
                    record.source,
                    json.dumps({"private_notes": record.notes}, sort_keys=True),
                    record.status,
                    record.created_at,
                ),
            )
            inserted += int(getattr(cur, "rowcount", 1) != 0)
    return inserted
