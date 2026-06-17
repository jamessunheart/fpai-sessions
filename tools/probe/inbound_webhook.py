#!/usr/bin/env python3
"""Guarded inbound email webhook for probe replies."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from tools.probe import rate_governor

try:
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel
except Exception:  # pragma: no cover - production dependency, tests use handler directly.
    FastAPI = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]

    class BaseModel:  # type: ignore[no-redef]
        def __init__(self, **kwargs: Any) -> None:
            annotations = getattr(self, "__annotations__", {})
            for key, default in self.__class__.__dict__.items():
                if key.startswith("_") or callable(default):
                    continue
                setattr(self, key, kwargs.pop(key, default))
            for key in annotations:
                if key in kwargs:
                    setattr(self, key, kwargs.pop(key))

EMAIL_RE = re.compile(r"[^<>,\s]+@[^<>,\s]+\.[^<>,\s]+")


class InboundReply(BaseModel):  # type: ignore[misc, valid-type]
    from_email: str
    subject: str = ""
    body: str = ""
    message_id: str | None = None
    in_reply_to: str | None = None
    received_at: str | None = None


@dataclass(frozen=True)
class InboundResult:
    enabled: bool
    matched: bool
    session_id: int | None
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def pipe_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("PROBE_PIPE_ENABLED") == "1"


def expected_pipe_token(env: dict[str, str] | None = None) -> str:
    values = env if env is not None else os.environ
    return values.get("PROBE_PIPE_TOKEN", "").strip()


def pipe_token_valid(*, provided: str | None, env: dict[str, str] | None = None) -> tuple[bool, str]:
    expected = expected_pipe_token(env)
    if not expected:
        return False, "pipe_token_missing"
    if str(provided or "").strip() != expected:
        return False, "pipe_token_invalid"
    return True, "ok"


def connect_from_env() -> Any:
    return rate_governor.connect_from_env()


def normalize_email(value: str) -> str:
    match = EMAIL_RE.search(str(value or "").lower())
    return match.group(0) if match else ""


def normalize_message_id(value: str | None) -> str:
    return str(value or "").strip().strip("<>")


def _reply_tokens(reply: InboundReply) -> set[str]:
    return {token for token in (normalize_message_id(reply.message_id), normalize_message_id(reply.in_reply_to)) if token}


def _match_session(conn: Any, reply: InboundReply) -> int | None:
    from_email = normalize_email(reply.from_email)
    tokens = _reply_tokens(reply)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, message_id, notes
              FROM brain_index.probe_sessions
             WHERE engaged IS NULL OR engaged = false
             ORDER BY initiated_at DESC
             LIMIT 250
            """
        )
        rows = list(cur.fetchall())
    for session_id, message_id, notes in rows:
        known_ids = {normalize_message_id(str(message_id or ""))}
        if isinstance(notes, str):
            try:
                data = json.loads(notes.splitlines()[0])
            except json.JSONDecodeError:
                data = {}
            if isinstance(data, dict):
                known_ids.add(normalize_message_id(str(data.get("message_id") or data.get("brevo_message_id") or "")))
                handle = normalize_email(str(data.get("handle") or data.get("email") or ""))
                if from_email and handle == from_email:
                    return int(session_id)
        if tokens and any(token in known_ids for token in tokens if token):
            return int(session_id)
    return None


def mark_inbound_reply(conn: Any, *, session_id: int, reply: InboundReply, now: datetime | None = None) -> None:
    current = now or utc_now()
    body = str(reply.body or "")[:1000]
    note = {
        "from_email": normalize_email(reply.from_email),
        "subject": str(reply.subject or "")[:200],
        "message_id": normalize_message_id(reply.message_id),
        "in_reply_to": normalize_message_id(reply.in_reply_to),
        "queued_probe_reply": True,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE brain_index.probe_sessions
               SET engaged = true,
                   last_message_at = %s,
                   last_message = %s,
                   notes = COALESCE(notes, '') || %s
             WHERE id = %s
            """,
            (current, body, "\ninbound_reply=" + json.dumps(note, sort_keys=True), session_id),
        )


def queue_probe_reply(conn: Any, *, session_id: int, reply: InboundReply, now: datetime | None = None) -> int | None:
    current = now or utc_now()
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_index.probe_reply_queue (
                id SERIAL PRIMARY KEY,
                probe_session_id INT NOT NULL,
                from_email TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                message_id TEXT,
                in_reply_to TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                sent_at TIMESTAMPTZ
            )
            """
        )
        cur.execute(
            """
            INSERT INTO brain_index.probe_reply_queue
                (probe_session_id, from_email, subject, body, message_id, in_reply_to, status, queued_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
            RETURNING id
            """,
            (
                session_id,
                normalize_email(reply.from_email),
                str(reply.subject or "")[:500],
                str(reply.body or ""),
                normalize_message_id(reply.message_id),
                normalize_message_id(reply.in_reply_to),
                current,
            ),
        )
        row = cur.fetchone() if hasattr(cur, "fetchone") else None
    return int(row[0]) if row else None


def handle_inbound_reply(
    reply: InboundReply,
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = connect_from_env,
    env: dict[str, str] | None = None,
    pipe_token: str | None = None,
    now: datetime | None = None,
) -> InboundResult:
    if not pipe_enabled(env):
        return InboundResult(False, False, None, "pipe_disabled")
    valid_token, token_reason = pipe_token_valid(provided=pipe_token, env=env)
    if not valid_token:
        return InboundResult(True, False, None, token_reason)
    own_conn = conn is None
    try:
        db = conn or connector()
    except Exception:
        return InboundResult(True, False, None, "db_unavailable")
    try:
        session_id = _match_session(db, reply)
        if session_id is None:
            return InboundResult(True, False, None, "no_matching_session")
        queue_probe_reply(db, session_id=session_id, reply=reply, now=now)
        mark_inbound_reply(db, session_id=session_id, reply=reply, now=now)
        return InboundResult(True, True, session_id, "updated")
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()


app = FastAPI(title="FPAI Probe Inbound Reply Webhook") if FastAPI is not None else None

if app is not None:

    @app.post("/probe/inbound-reply")
    def inbound_reply(reply: InboundReply, x_fpai_pipe_token: str | None = Header(default=None, alias="X-FPAI-Pipe-Token")) -> dict[str, Any]:
        result = handle_inbound_reply(reply, pipe_token=x_fpai_pipe_token)
        if result.reason == "pipe_disabled":
            raise HTTPException(status_code=403, detail="probe pipe disabled")
        if result.reason == "pipe_token_missing":
            raise HTTPException(status_code=503, detail="probe pipe token missing")
        if result.reason == "pipe_token_invalid":
            raise HTTPException(status_code=401, detail="invalid probe pipe token")
        if result.reason == "db_unavailable":
            raise HTTPException(status_code=503, detail="database unavailable")
        return result.__dict__
