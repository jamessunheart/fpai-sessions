#!/usr/bin/env python3
"""Meta WhatsApp webhook adapter for Hermes and the probe agent."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from tools.hermes.wa_sender import WhatsAppSendResult, send_session_message


@dataclass(frozen=True)
class IncomingWhatsAppMessage:
    sender_wa_id: str
    text: str
    message_id: str | None = None
    timestamp: str | None = None
    media: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class WhatsAppRouteResult:
    accepted: bool
    sender_wa_id: str | None
    contact_id: str | None
    probe_id: str | None
    reply: WhatsAppSendResult | None
    reason: str


def verify_meta_signature(body: bytes, signature_header: str | None, app_secret: str | None = None) -> bool:
    secret = (app_secret if app_secret is not None else os.environ.get("WA_APP_SECRET", "")).strip()
    header = str(signature_header or "").strip()
    if not secret or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def verify_webhook_challenge(query: dict[str, str], *, verify_token: str | None = None) -> tuple[int, str]:
    token = verify_token if verify_token is not None else os.environ.get("WA_VERIFY_TOKEN", "")
    mode = query.get("hub.mode") or query.get("mode")
    challenge = query.get("hub.challenge") or query.get("challenge") or ""
    incoming = query.get("hub.verify_token") or query.get("verify_token") or ""
    if mode == "subscribe" and token and hmac.compare_digest(incoming, token):
        return 200, challenge
    return 403, "forbidden"


def _message_text(message: dict[str, Any]) -> str:
    msg_type = message.get("type")
    if msg_type == "text":
        return str((message.get("text") or {}).get("body") or "").strip()
    if msg_type in {"button", "interactive"}:
        return json.dumps(message.get(msg_type) or {}, sort_keys=True)
    return ""


def _message_media(message: dict[str, Any]) -> list[dict[str, Any]]:
    media = []
    for key in ("image", "audio", "video", "document", "sticker"):
        if key in message and isinstance(message[key], dict):
            item = dict(message[key])
            item["type"] = key
            media.append(item)
    return media


def parse_incoming_messages(payload: dict[str, Any]) -> list[IncomingWhatsAppMessage]:
    messages: list[IncomingWhatsAppMessage] = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            contacts_by_wa_id = {
                str(contact.get("wa_id")): contact
                for contact in value.get("contacts", []) or []
                if contact.get("wa_id")
            }
            for message in value.get("messages", []) or []:
                sender = str(message.get("from") or "").strip()
                if not sender:
                    continue
                contact = contacts_by_wa_id.get(sender, {})
                text = _message_text(message)
                messages.append(IncomingWhatsAppMessage(
                    sender_wa_id=sender,
                    text=text,
                    message_id=str(message.get("id") or "") or None,
                    timestamp=str(message.get("timestamp") or "") or None,
                    media=_message_media(message),
                    raw={"message": message, "contact": contact, "value": value},
                ))
    return messages


def _fetchone(cur: Any) -> Any:
    return cur.fetchone() if hasattr(cur, "fetchone") else None


def ensure_contact_pool_entry(conn: Any, message: IncomingWhatsAppMessage, *, now: datetime | None = None) -> str | None:
    current = now or datetime.now(timezone.utc)
    name = None
    if message.raw:
        profile = ((message.raw.get("contact") or {}).get("profile") or {})
        name = profile.get("name")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM brain_index.contact_pool WHERE channel = %s AND wa_id = %s LIMIT 1",
            ("whatsapp", message.sender_wa_id),
        )
        row = _fetchone(cur)
        if row:
            contact_id = str(row[0])
            cur.execute(
                "UPDATE brain_index.contact_pool SET status = %s, updated_at = %s WHERE id = %s",
                ("replied", current, contact_id),
            )
            return contact_id
        contact_id = f"contact_{uuid.uuid4().hex[:12]}"
        cur.execute(
            """
            INSERT INTO brain_index.contact_pool
                (id, name, wa_id, channel, source, notes, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                contact_id,
                name,
                message.sender_wa_id,
                "whatsapp",
                "inbound_wa",
                json.dumps({"first_message_id": message.message_id, "media": message.media or []}, sort_keys=True),
                "replied",
                current,
                current,
            ),
        )
        row = _fetchone(cur)
        return str(row[0]) if row else contact_id


def create_probe_pool_entry(conn: Any, message: IncomingWhatsAppMessage, *, contact_id: str | None = None) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM brain_index.probe_pool WHERE platform = %s AND handle = %s LIMIT 1",
            ("whatsapp", message.sender_wa_id),
        )
        row = _fetchone(cur)
        if row:
            return int(row[0])
        cur.execute(
            """
            INSERT INTO brain_index.probe_pool
                (pool, handle, platform, added_by, source, topic_signal, discovery_score, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "warm",
                message.sender_wa_id,
                "whatsapp",
                "system",
                "inbound_wa",
                "whatsapp_inbound_reply",
                1.0,
                json.dumps({
                    "contact_pool_id": contact_id,
                    "message_id": message.message_id,
                    "first_text": message.text,
                    "media": message.media or [],
                }, sort_keys=True),
            ),
        )
        row = _fetchone(cur)
        return int(row[0]) if row else None


def record_probe_session_from_inbound(
    conn: Any,
    message: IncomingWhatsAppMessage,
    *,
    probe_pool_id: int | None,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(timezone.utc)
    probe_id = f"wa_{current.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    notes = {
        "pool_member_id": probe_pool_id,
        "platform": "whatsapp",
        "handle": message.sender_wa_id,
        "inbound_message_id": message.message_id,
        "last_message": message.text,
        "media": message.media or [],
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.probe_sessions
                (probe_id, pool, initiated_at, last_message_at, engaged, drop_off_message, completed_spark,
                 completed_onboarding, quality_score, corrections_triggered, last_message, notes)
            VALUES (%s, %s, %s, %s, true, %s, false, false, NULL, 0, %s, %s)
            """,
            (probe_id, "warm", current, current, 1, message.text[:1000], json.dumps(notes, sort_keys=True)),
        )
    return probe_id


def default_probe_reply(message: IncomingWhatsAppMessage) -> str:
    del message
    return "I'm here. What does your full potential look like to you right now, and what's most in the way?"


def route_incoming_message(
    message: IncomingWhatsAppMessage,
    *,
    conn: Any,
    reply_builder: Callable[[IncomingWhatsAppMessage], str] = default_probe_reply,
    sender: Callable[[str, str], WhatsAppSendResult] = send_session_message,
    now: datetime | None = None,
) -> WhatsAppRouteResult:
    contact_id = ensure_contact_pool_entry(conn, message, now=now)
    probe_pool_id = create_probe_pool_entry(conn, message, contact_id=contact_id)
    probe_id = record_probe_session_from_inbound(conn, message, probe_pool_id=probe_pool_id, now=now)
    reply = sender(message.sender_wa_id, reply_builder(message))
    return WhatsAppRouteResult(True, message.sender_wa_id, contact_id, probe_id, reply, "routed")


def handle_webhook_post(
    body: bytes,
    headers: dict[str, str],
    *,
    conn: Any,
    app_secret: str | None = None,
    sender: Callable[[str, str], WhatsAppSendResult] = send_session_message,
    reply_builder: Callable[[IncomingWhatsAppMessage], str] = default_probe_reply,
) -> tuple[int, dict[str, Any]]:
    signature = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256")
    if not verify_meta_signature(body, signature, app_secret):
        return 403, {"accepted": False, "reason": "bad_signature"}
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return 400, {"accepted": False, "reason": "bad_json"}
    results = [
        route_incoming_message(message, conn=conn, sender=sender, reply_builder=reply_builder)
        for message in parse_incoming_messages(payload)
    ]
    return 200, {
        "accepted": True,
        "routed": len(results),
        "send_reasons": [result.reply.reason if result.reply else None for result in results],
    }


def create_fastapi_app(connector: Callable[[], Any]):
    """Create a minimal FastAPI receiver mounted at /webhooks/whatsapp.

    FastAPI is imported only when this factory is used so tests and repo scans do
    not need the web stack installed.
    """
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import JSONResponse, PlainTextResponse

    app = FastAPI(title="Hermes WhatsApp Adapter")

    @app.get("/webhooks/whatsapp")
    async def verify(request: Request) -> Response:
        status, body = verify_webhook_challenge(dict(request.query_params))
        return PlainTextResponse(body, status_code=status)

    @app.post("/webhooks/whatsapp")
    async def receive(request: Request) -> JSONResponse:
        body = await request.body()
        conn = connector()
        try:
            status, data = handle_webhook_post(body, dict(request.headers), conn=conn)
        finally:
            if hasattr(conn, "close"):
                conn.close()
        return JSONResponse(data, status_code=status)

    return app
