#!/usr/bin/env python3
"""Send one Telegram-CTA follow-up for silent email probe sessions."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.hermes import email_adapter
from tools.probe import rate_governor

FOLLOWUP_SUBJECT = "Still here if you want to talk"
DEFAULT_REPLY_TO = "probe-replies@fullpotential.ai"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class FollowupSession:
    id: int
    probe_id: str
    email: str
    name: str
    initiated_at: datetime
    notes: str
    message_id: str | None = None


@dataclass(frozen=True)
class FollowupResult:
    scanned: int
    eligible: int
    sent: int
    dry_run: int
    failed: int
    disabled: bool
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def connect_from_env() -> Any:
    return rate_governor.connect_from_env()


def first_name(name: str | None, email: str) -> str:
    return email_adapter.first_name(name, email)


def followup_body(*, name: str) -> str:
    return (
        f"Hi {name},\n\n"
        "Just checking in - the easiest way to continue is actually on Telegram, where I can\n"
        "respond instantly. Just message @sunheartbrain_bot and say hi.\n\n"
        "Or reply here if you prefer email - I read both.\n\n"
        "-- Sunheart AI"
    )


def _notes_json(notes: Any) -> dict[str, Any]:
    if not isinstance(notes, str) or not notes.strip():
        return {}
    try:
        data = json.loads(notes.splitlines()[0])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _email_from_notes(notes: str) -> str:
    data = _notes_json(notes)
    for key in ("email", "handle", "to_email"):
        value = str(data.get(key) or "").strip().lower()
        if EMAIL_RE.match(value):
            return value
    match = re.search(r"[^@\s<>,]+@[^@\s<>,]+\.[^@\s<>,]+", notes or "")
    return match.group(0).lower() if match else ""


def _name_from_notes(notes: str, email: str) -> str:
    data = _notes_json(notes)
    return first_name(str(data.get("name") or data.get("first_name") or ""), email)


def select_due_sessions(conn: Any, *, now: datetime | None = None, limit: int = 100) -> list[FollowupSession]:
    current = now or utc_now()
    cutoff = current - timedelta(days=3)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, probe_id, initiated_at, notes, message_id
              FROM brain_index.probe_sessions
             WHERE initiated_at < %s
               AND (engaged IS NULL OR engaged = false)
               AND COALESCE(notes, '') NOT LIKE %s
             ORDER BY initiated_at ASC
             LIMIT %s
            """,
            (cutoff, "%tg_cta_sent%", limit),
        )
        rows = list(cur.fetchall())
    sessions: list[FollowupSession] = []
    for row in rows:
        session_id, probe_id, initiated_at, notes = row[:4]
        message_id = row[4] if len(row) > 4 else None
        text_notes = str(notes or "")
        email = _email_from_notes(text_notes)
        if not email:
            continue
        sessions.append(
            FollowupSession(
                id=int(session_id),
                probe_id=str(probe_id),
                email=email,
                name=_name_from_notes(text_notes, email),
                initiated_at=initiated_at,
                notes=text_notes,
                message_id=str(message_id) if message_id else None,
            )
        )
    return sessions


def build_followup_payload(session: FollowupSession, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    values = env if env is not None else os.environ
    sender = values.get("OUTREACH_EMAIL_FROM") or email_adapter.DEFAULT_FROM
    reply_to = values.get("PROBE_REPLY_TO") or values.get("OUTREACH_REPLY_TO") or DEFAULT_REPLY_TO
    return {
        "sender": {"email": sender, "name": "Sunheart AI"},
        "to": [{"email": session.email, "name": session.name}],
        "replyTo": {"email": reply_to, "name": "Sunheart AI"},
        "subject": FOLLOWUP_SUBJECT,
        "textContent": followup_body(name=session.name),
        "headers": {
            "X-FPAI-Outreach": "probe_followup",
            "X-FPAI-Probe-Id": session.probe_id,
        },
    }


def send_followup_email(
    session: FollowupSession,
    *,
    env: dict[str, str] | None = None,
    urlopen: Any = urllib.request.urlopen,
) -> email_adapter.EmailSendResult:
    values = env if env is not None else os.environ
    payload = build_followup_payload(session, env=values)
    if email_adapter.disabled_by_env(values):
        return email_adapter.EmailSendResult(False, False, True, None, None, "disabled", payload)
    if not email_adapter.is_live_enabled(values):
        return email_adapter.EmailSendResult(False, True, False, None, None, "dry_run", payload)
    api_key = values.get("BREVO_API_KEY", "").strip()
    if not api_key:
        return email_adapter.EmailSendResult(False, False, False, None, None, "missing_brevo_api_key", payload)
    request = urllib.request.Request(
        email_adapter.BREVO_TRANSACTIONAL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return email_adapter.EmailSendResult(False, False, False, None, None, f"brevo_error:{exc.__class__.__name__}", payload)
    try:
        data = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        data = {}
    message_id = str(data.get("messageId") or data.get("message_id") or "").strip() or None
    return email_adapter.EmailSendResult(True, False, False, message_id, email_adapter.utc_stamp(), "sent", payload)


def mark_tg_cta_sent(conn: Any, *, session_id: int, delivery: email_adapter.EmailSendResult) -> None:
    meta = {"reason": delivery.reason}
    if delivery.message_id:
        meta["message_id"] = delivery.message_id
    if delivery.sent_at:
        meta["sent_at"] = delivery.sent_at
    extra = "\ntg_cta_sent=" + json.dumps(meta, sort_keys=True)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE brain_index.probe_sessions SET notes = COALESCE(notes, '') || %s WHERE id = %s",
            (extra, session_id),
        )


def claim_tg_cta_send(conn: Any, *, session_id: int, now: datetime | None = None) -> str | None:
    """Reserve a live follow-up send so overlapping runs do not double-send."""
    current = now or utc_now()
    claim = "\ntg_cta_claimed=" + json.dumps({"at": current.isoformat(), "run_id": uuid.uuid4().hex}, sort_keys=True)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE brain_index.probe_sessions
               SET notes = COALESCE(notes, '') || %s
             WHERE id = %s
               AND COALESCE(notes, '') NOT LIKE %s
               AND COALESCE(notes, '') NOT LIKE %s
             RETURNING id
            """,
            (claim, session_id, "%tg_cta_sent%", "%tg_cta_claimed%"),
        )
        row = cur.fetchone() if hasattr(cur, "fetchone") else None
    return claim if row is not None else None


def release_tg_cta_claim(conn: Any, *, session_id: int, claim: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE brain_index.probe_sessions SET notes = replace(COALESCE(notes, ''), %s, '') WHERE id = %s",
            (claim, session_id),
        )



def run_followups(
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = connect_from_env,
    sender: Callable[[FollowupSession], email_adapter.EmailSendResult] = send_followup_email,
    now: datetime | None = None,
    limit: int = 100,
) -> FollowupResult:
    if os.environ.get("PROBE_DISABLE") == "1" or os.environ.get("OUTREACH_EMAIL_DISABLE") == "1":
        return FollowupResult(0, 0, 0, 0, 0, True, "disabled")
    own_conn = conn is None
    try:
        db = conn or connector()
    except Exception:
        return FollowupResult(0, 0, 0, 0, 0, False, "db_unavailable")
    try:
        sessions = select_due_sessions(db, now=now, limit=limit)
        sent = dry_run = failed = 0
        for session in sessions:
            claim = None
            if email_adapter.is_live_enabled():
                claim = claim_tg_cta_send(db, session_id=session.id, now=now)
                if not claim:
                    continue
            delivery = sender(session)
            if delivery.sent:
                mark_tg_cta_sent(db, session_id=session.id, delivery=delivery)
                sent += 1
            elif delivery.dry_run:
                if claim:
                    release_tg_cta_claim(db, session_id=session.id, claim=claim)
                dry_run += 1
            else:
                if claim:
                    release_tg_cta_claim(db, session_id=session.id, claim=claim)
                failed += 1
        reason = "ok" if not failed else "partial_failure"
        return FollowupResult(len(sessions), len(sessions), sent, dry_run, failed, False, reason)
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send due Telegram CTA follow-ups for silent probe email sessions.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = run_followups(limit=args.limit)
    if args.json:
        print(json.dumps(result.__dict__, sort_keys=True))
    else:
        print(f"probe-followup: sent={result.sent} dry_run={result.dry_run} failed={result.failed} reason={result.reason}")
    return 0 if result.reason not in {"db_unavailable", "partial_failure"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
