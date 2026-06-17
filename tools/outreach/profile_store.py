#!/usr/bin/env python3
"""Persistence helpers for private pre-contact profiles."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any


def json_value(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, sort_keys=True)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def insert_contact_profile(conn: Any, *, profile: Any) -> int | None:
    """Insert a profile into brain_index.contact_profiles.

    The profile object may be a dict or dataclass with the schema fields from
    migrations/add_contact_profiles_table.sql. JSONB values are serialized here
    so fake cursors and psycopg both receive deterministic values.
    """
    data = asdict(profile) if is_dataclass(profile) else dict(profile)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.contact_profiles
                (contact_id, researched_at, sources, summary, resonance_points,
                 suggested_subject, suggested_body, raw_notes, confidence)
            VALUES (%s, COALESCE(%s, now()), %s::jsonb, %s, %s::jsonb, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data.get("contact_id"),
                data.get("researched_at"),
                json_value(data.get("sources") or {}),
                data.get("summary") or "",
                json_value(data.get("resonance_points") or []),
                data.get("suggested_subject") or "",
                data.get("suggested_body") or "",
                data.get("raw_notes") or "",
                data.get("confidence"),
            ),
        )
        if hasattr(cur, "fetchone"):
            row = cur.fetchone()
            if row:
                return int(row[0])
    return None


def fetch_contact(conn: Any, contact_id: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, channel, notes, url_hints
              FROM brain_index.contact_pool
             WHERE id = %s
            """,
            (contact_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    hints = row[5]
    if isinstance(hints, str):
        try:
            hints = json.loads(hints)
        except json.JSONDecodeError:
            hints = [hints]
    return {
        "id": int(row[0]),
        "name": row[1],
        "email": row[2],
        "channel": row[3],
        "notes": row[4],
        "url_hints": hints or [],
    }


def seed_contact(conn: Any, *, name: str, email: str | None = None, channel: str | None = None, notes: str | None = None, url_hints: Any = None) -> int | None:
    """Create a pending contact_pool row for the future seed endpoint."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.contact_pool
                (name, email, channel, notes, url_hints, status, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, 'pending', now())
            RETURNING id
            """,
            (name, email, channel, notes, json_value(url_hints or [])),
        )
        if hasattr(cur, "fetchone"):
            row = cur.fetchone()
            if row:
                return int(row[0])
    return None
