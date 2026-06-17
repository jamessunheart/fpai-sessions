#!/usr/bin/env python3
"""IMAP poller for sunheartai@fullpotential.ai — feeds replies into probe inbound handler."""
from __future__ import annotations

import email
import email.header
import email.utils
import imaplib
import os
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.probe.inbound_webhook import InboundReply, handle_inbound_reply
from tools.probe import rate_governor

IMAP_HOST = os.environ.get("SYSTEM_EMAIL_IMAP_HOST", "server1.outbounders.com")
IMAP_PORT = int(os.environ.get("SYSTEM_EMAIL_IMAP_PORT", "993"))
IMAP_USER = os.environ.get("SYSTEM_EMAIL_USER", "sunheartai@fullpotential.ai")
IMAP_PASS = os.environ.get("SYSTEM_EMAIL_PASSWORD", "")
PIPE_TOKEN = os.environ.get("PROBE_PIPE_TOKEN", "")
PIPE_ENABLED = os.environ.get("PROBE_PIPE_ENABLED", "0") == "1"
TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")

MARK_SEEN = True  # mark processed messages as \Seen


def _decode_header(raw: str | None) -> str:
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(chunk))
    return " ".join(decoded).strip()


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return ""


def _notify_telegram(subject: str, from_email: str, body: str) -> None:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    import urllib.request, json, urllib.parse
    text = (
        f"📬 <b>Reply to sunheartai@fullpotential.ai</b>\n"
        f"From: {from_email}\n"
        f"Subject: {subject}\n\n"
        f"{body[:400]}{'...' if len(body) > 400 else ''}"
    )
    payload = json.dumps({
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }).encode()
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[imap_poller] TG notify failed: {e}", file=sys.stderr)


def poll_once(dry_run: bool = False) -> int:
    """Poll INBOX for unseen messages, feed each into handle_inbound_reply. Returns count processed."""
    ctx = ssl.create_default_context()
    processed = 0
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ctx) as m:
            m.login(IMAP_USER, IMAP_PASS)
            m.select("INBOX")
            status, data = m.search(None, "UNSEEN")
            if status != "OK" or not data[0]:
                return 0
            msg_ids = data[0].split()
            print(f"[imap_poller] {len(msg_ids)} unseen message(s)", flush=True)
            for num in msg_ids:
                status, raw = m.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                raw_bytes = raw[0][1] if isinstance(raw[0], tuple) else b""
                msg = email.message_from_bytes(raw_bytes)
                from_raw = msg.get("From", "")
                from_addr = email.utils.parseaddr(from_raw)[1]
                subject = _decode_header(msg.get("Subject", ""))
                body = _extract_body(msg)
                message_id = msg.get("Message-ID", "")
                in_reply_to = msg.get("In-Reply-To", "")

                print(f"[imap_poller] from={from_addr} subject={subject[:60]}", flush=True)

                if dry_run:
                    print(f"[imap_poller] DRY RUN — would process", flush=True)
                    continue

                reply = InboundReply(
                    from_email=from_addr,
                    subject=subject,
                    body=body,
                    message_id=message_id,
                    in_reply_to=in_reply_to,
                    received_at=datetime.now(timezone.utc).isoformat(),
                )
                result = handle_inbound_reply(
                    reply,
                    connector=rate_governor.connect_from_env,
                    pipe_token=PIPE_TOKEN,
                )
                print(f"[imap_poller] result={result.reason} session={result.session_id}", flush=True)

                # Always notify James via Telegram for any reply
                _notify_telegram(subject, from_addr, body)

                if MARK_SEEN:
                    m.store(num, "+FLAGS", "\\Seen")
                processed += 1
    except Exception as e:
        print(f"[imap_poller] error: {e}", file=sys.stderr)
    return processed


def _load_env() -> None:
    for ef in ["/etc/sh-brain/curator.env", "/etc/sh-brain/index.env"]:
        p = Path(ef)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


if __name__ == "__main__":
    import argparse
    _load_env()
    parser = argparse.ArgumentParser(description="IMAP poller for probe replies")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--loop", action="store_true", help="Poll every 60s forever")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    if args.loop:
        print(f"[imap_poller] starting loop (interval={args.interval}s)", flush=True)
        while True:
            poll_once(dry_run=args.dry_run)
            time.sleep(args.interval)
    else:
        n = poll_once(dry_run=args.dry_run)
        print(f"[imap_poller] done — {n} processed")
