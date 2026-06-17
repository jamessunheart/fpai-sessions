#!/usr/bin/env python3
"""IMAP reply parser for FP Game outreach messages."""
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.probe import rate_governor

POSITIVE_RE = re.compile(r"\b(yes|yeah|yep|sure|ok|okay|interested)\b", re.I)
NEGATIVE_RE = re.compile(r"\b(no|nope|not interested|unsubscribe|stop|don't|do not)\b", re.I)
BOT_LINK = "t.me/sunheartbrain_bot"


@dataclass(frozen=True)
class ReplyResult:
    engaged: int
    expired: int
    scanned: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def positive_reply(text: str) -> bool:
    body = str(text or "")
    return bool(POSITIVE_RE.search(body)) and not bool(NEGATIVE_RE.search(body))


def message_text(message: Message) -> str:
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_type() not in {"text/plain", "text/html"}:
                continue
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
        return "\n".join(parts)
    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(message.get_content_charset() or "utf-8", errors="replace")
    return str(message.get_payload() or "")


def extract_message_ids(message: Message) -> set[str]:
    ids = set()
    for header in ("In-Reply-To", "References", "Message-ID", "Message-Id"):
        value = message.get(header)
        if not value:
            continue
        ids.update(token.strip("<>") for token in re.findall(r"<([^>]+)>|([^\s<>]+)", value) for token in token if token)
    return {token for token in ids if token}


def extract_addresses(value: str | None) -> set[str]:
    if not value:
        return set()
    return {match.lower() for match in re.findall(r"[^<>,\s]+@[^<>,\s]+\.[^<>,\s]+", value)}


def table_columns(conn: Any, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'brain_index'
               AND table_name = %s
            """,
            (table,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def outreach_sessions(conn: Any, *, now: datetime) -> list[dict[str, Any]]:
    cutoff = now - timedelta(days=7)
    try:
        session_columns = table_columns(conn, "probe_sessions")
    except Exception:
        session_columns = set()
    message_expr = "message_id" if "message_id" in session_columns else "NULL AS message_id"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, probe_id, initiated_at, notes, {message_expr}
             FROM brain_index.probe_sessions
             WHERE initiated_at >= %s
               AND (engaged IS NULL OR engaged = false)
            """,
            (cutoff,),
        )
        rows = list(cur.fetchall())
    sessions = []
    for row in rows:
        session_id, probe_id, initiated_at, notes = row[:4]
        column_message_id = row[4] if len(row) > 4 else None
        data = {}
        if isinstance(notes, str):
            try:
                data = json.loads(notes.splitlines()[0])
            except json.JSONDecodeError:
                data = {}
        message_id = str(column_message_id or data.get("message_id") or data.get("brevo_message_id") or "").strip()
        handle = str(data.get("handle") or data.get("email") or "").strip().lower()
        if message_id or handle:
            sessions.append({
                "id": session_id,
                "probe_id": probe_id,
                "initiated_at": initiated_at,
                "message_id": message_id,
                "handle": handle,
                "notes": notes,
            })
    return sessions


def mark_engaged(conn: Any, *, session_id: int, reply_text: str, now: datetime) -> None:
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
            (now, reply_text[:1000], "\nreply_parser=positive", session_id),
        )


def mark_expired(conn: Any, *, session_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE brain_index.probe_sessions
               SET engaged = false,
                   notes = COALESCE(notes, '') || %s
             WHERE id = %s
            """,
            ("\nreply_parser=no_reply_72h", session_id),
        )


def default_send_bot_link(_session: dict[str, Any]) -> bool:
    """Placeholder for follow-up. Email thread continuation is safer for v1."""
    return True


def poll_imap_messages(
    *,
    host: str,
    username: str,
    password: str,
    mailbox: str = "INBOX",
    imap_factory: Callable[..., Any] = imaplib.IMAP4_SSL,
) -> list[Message]:
    client = imap_factory(host)
    try:
        client.login(username, password)
        client.select(mailbox)
        status, data = client.search(None, "ALL")
        if status != "OK":
            return []
        messages = []
        for num in data[0].split():
            fetch_status, fetched = client.fetch(num, "(RFC822)")
            if fetch_status != "OK":
                continue
            for item in fetched:
                if isinstance(item, tuple) and item[1]:
                    messages.append(email.message_from_bytes(item[1]))
        return messages
    finally:
        try:
            client.logout()
        except Exception:
            pass


def process_replies(
    *,
    conn: Any,
    messages: Iterable[Message],
    now: datetime | None = None,
    send_bot_link: Callable[[dict[str, Any]], bool] = default_send_bot_link,
) -> ReplyResult:
    current = now or utc_now()
    sessions = outreach_sessions(conn, now=current)
    by_message = {session["message_id"].strip("<>"): session for session in sessions if session.get("message_id")}
    by_handle = {str(session.get("handle")).lower(): session for session in sessions if session.get("handle")}
    engaged = 0
    engaged_session_ids: set[int] = set()
    scanned = 0
    for msg in messages:
        scanned += 1
        ids = extract_message_ids(msg)
        from_addresses = extract_addresses(msg.get("From"))
        session = next((by_message[mid] for mid in ids if mid in by_message), None)
        if not session:
            session = next((by_handle[address] for address in from_addresses if address in by_handle), None)
        if not session:
            continue
        text = message_text(msg)
        if not positive_reply(text):
            continue
        mark_engaged(conn, session_id=int(session["id"]), reply_text=f"{text}\n\nBot link: {BOT_LINK}", now=current)
        send_bot_link(session)
        engaged_session_ids.add(int(session["id"]))
        engaged += 1
    expired = 0
    cutoff = current - timedelta(hours=72)
    for session in sessions:
        if int(session["id"]) in engaged_session_ids:
            continue
        initiated = rate_governor.parse_time(session["initiated_at"])
        if initiated and initiated <= cutoff:
            mark_expired(conn, session_id=int(session["id"]))
            expired += 1
    return ReplyResult(engaged, expired, scanned)


def connect_imap_from_env() -> list[Message]:
    host = os.environ.get("OUTREACH_IMAP_HOST", "").strip()
    username = os.environ.get("OUTREACH_IMAP_USER", "").strip()
    password = os.environ.get("OUTREACH_IMAP_PASSWORD", "").strip()
    mailbox = os.environ.get("OUTREACH_IMAP_MAILBOX", "INBOX")
    if not host or not username or not password:
        return []
    return poll_imap_messages(host=host, username=username, password=password, mailbox=mailbox)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll outreach replies and update probe_sessions.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if os.environ.get("PROBE_DISABLE") == "1" or os.environ.get("OUTREACH_EMAIL_DISABLE") == "1":
        result = ReplyResult(0, 0, 0)
    else:
        conn = rate_governor.connect_from_env()
        try:
            result = process_replies(conn=conn, messages=connect_imap_from_env())
        finally:
            conn.close()
    if args.json:
        print(json.dumps(result.__dict__, sort_keys=True))
    else:
        print(f"email_replies: engaged={result.engaged} expired={result.expired} scanned={result.scanned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
