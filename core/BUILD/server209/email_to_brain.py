#!/usr/bin/env python3
"""Pipe raw probe reply email to the brain inbound-reply webhook.

Deploy target, after explicit James authorization:
  /home/fpai/scripts/email_to_brain.py on server 209
  /etc/valiases/fullpotential.ai: probe-replies: |/home/fpai/scripts/email_to_brain.py
"""
from __future__ import annotations

import email
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from email.message import Message

DEFAULT_ENDPOINT = "https://brain.sunheart.com/probe/inbound-reply"


def message_body(message: Message) -> str:
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


def payload_from_raw(raw: bytes, *, received_at: str | None = None) -> dict[str, str | None]:
    message = email.message_from_bytes(raw)
    return {
        "from_email": message.get("From", ""),
        "subject": message.get("Subject", ""),
        "body": message_body(message),
        "message_id": message.get("Message-ID") or message.get("Message-Id"),
        "in_reply_to": message.get("In-Reply-To"),
        "received_at": received_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def post_payload(payload: dict[str, str | None], *, endpoint: str, pipe_token: str, timeout: int = 10) -> int:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", "accept": "application/json", "X-FPAI-Pipe-Token": pipe_token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()
        return int(getattr(response, "status", 200))


def main() -> int:
    if os.environ.get("PROBE_PIPE_ENABLED") != "1":
        print("email_to_brain: disabled; set PROBE_PIPE_ENABLED=1 after pipe verification", file=sys.stderr)
        return 75
    raw = sys.stdin.buffer.read()
    if not raw:
        print("email_to_brain: empty stdin", file=sys.stderr)
        return 65
    endpoint = os.environ.get("PROBE_INBOUND_URL", DEFAULT_ENDPOINT)
    if not endpoint.startswith("https://") and os.environ.get("PROBE_PIPE_ALLOW_INSECURE_HTTP") != "1":
        print("email_to_brain: refusing non-HTTPS endpoint without PROBE_PIPE_ALLOW_INSECURE_HTTP=1", file=sys.stderr)
        return 78
    pipe_token = os.environ.get("PROBE_PIPE_TOKEN", "").strip()
    if not pipe_token:
        print("email_to_brain: missing PROBE_PIPE_TOKEN", file=sys.stderr)
        return 78
    try:
        status = post_payload(payload_from_raw(raw), endpoint=endpoint, pipe_token=pipe_token)
    except Exception as exc:
        print(f"email_to_brain: post failed: {exc.__class__.__name__}", file=sys.stderr)
        return 75
    return 0 if 200 <= status < 300 else 75


if __name__ == "__main__":
    raise SystemExit(main())
