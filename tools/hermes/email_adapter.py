#!/usr/bin/env python3
"""Dry-run-first Brevo transactional email adapter for FP Game outreach."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BREVO_TRANSACTIONAL_URL = "https://api.brevo.com/v3/smtp/email"
CANONICAL_SUBJECT = "What does your full potential actually look like?"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTREACH_VOICE_PATH = REPO_ROOT / "core" / "STATE" / "OUTREACH_VOICE.md"
FALLBACK_CANONICAL_MESSAGE = (
    "I'm Sunheart AI. Sunheart built me around one question: what does your full potential "
    "actually look like - and what's in the way? I grow from every real conversation. Want to "
    "find out what yours looks like?"
)
DEFAULT_FROM = "james@fullpotential.com"
DEFAULT_REPLY_TO = "james@fullpotential.com"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
QUOTED_RE = re.compile(r'"([^"]+)"')
SECTION_QUOTE_RE = re.compile(r"^## (?P<heading>[^\n]+)\n+\"(?P<body>.*?)\"", re.M | re.S)


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    dry_run: bool
    disabled: bool
    message_id: str | None
    sent_at: str | None
    reason: str
    payload: dict[str, Any]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def first_name(name: str | None, email: str = "") -> str:
    source = (name or "").strip() or email.split("@", 1)[0].replace(".", " ").replace("_", " ")
    token = next((part for part in source.split() if part), "there")
    return token[:1].upper() + token[1:]


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(str(email or "").strip()))


def canonical_message(path: Path = OUTREACH_VOICE_PATH) -> str:
    if not path.exists():
        return FALLBACK_CANONICAL_MESSAGE
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = QUOTED_RE.findall(text)
    if matches:
        return max((" ".join(match.split()) for match in matches), key=len)
    return " ".join(text.split()) or FALLBACK_CANONICAL_MESSAGE


def canonical_section(path: Path, heading: str) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    for match in SECTION_QUOTE_RE.finditer(text):
        if match.group("heading").strip().lower() == heading.lower():
            return match.group("body").strip()
    return None


def canonical_subject(path: Path = OUTREACH_VOICE_PATH) -> str:
    return canonical_section(path, "Email Subject") or CANONICAL_SUBJECT


def canonical_email_body(*, name: str, link: str, path: Path = OUTREACH_VOICE_PATH) -> str:
    body = canonical_section(path, "Email Body")
    if not body:
        return FALLBACK_CANONICAL_MESSAGE
    return body.replace("[first_name]", name).replace("[link]", link)


def disabled_by_env(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("PROBE_DISABLE") == "1" or values.get("OUTREACH_EMAIL_DISABLE") == "1"


def is_live_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("OUTREACH_LIVE") == "1" and values.get("DRY_RUN", "1") != "1"


def build_payload(
    *,
    to_email: str,
    to_name: str | None = None,
    from_email: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    values = env if env is not None else os.environ
    email = str(to_email or "").strip()
    if not valid_email(email):
        raise ValueError("invalid recipient email")
    sender = from_email or values.get("OUTREACH_EMAIL_FROM") or DEFAULT_FROM
    name = first_name(to_name, email)
    link = values.get("OUTREACH_LINK", "@sunheartbrain_bot")
    message = canonical_email_body(name=name, link=link)
    return {
        "sender": {"email": sender, "name": "Sunheart AI"},
        "to": [{"email": email, "name": to_name or name}],
        "replyTo": {"email": values.get("OUTREACH_REPLY_TO", DEFAULT_REPLY_TO), "name": "Sunheart AI"},
        "subject": canonical_subject(),
        "textContent": f"{message}\n\nReply STOP to opt out.",
        "headers": {
            "X-FPAI-Outreach": "fp_game_champions",
        },
    }


def send_outreach_email(
    *,
    to_email: str,
    to_name: str | None = None,
    opener: str | None = None,
    env: dict[str, str] | None = None,
    opener_ignored: bool = True,
    urlopen: Any = urllib.request.urlopen,
) -> EmailSendResult:
    """Send the canonical outreach email through Brevo, or return a dry-run result.

    The `opener` argument is accepted so this can be used as a Probe sender, but
    the canonical James-approved email body is always used.
    """
    del opener, opener_ignored
    values = env if env is not None else os.environ
    payload = build_payload(to_email=to_email, to_name=to_name, env=values)
    if disabled_by_env(values):
        return EmailSendResult(False, False, True, None, None, "disabled", payload)
    if not is_live_enabled(values):
        return EmailSendResult(False, True, False, None, None, "dry_run", payload)
    api_key = values.get("BREVO_API_KEY", "").strip()
    if not api_key:
        return EmailSendResult(False, False, False, None, None, "missing_brevo_api_key", payload)
    request = urllib.request.Request(
        BREVO_TRANSACTIONAL_URL,
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
        return EmailSendResult(False, False, False, None, None, f"brevo_error:{exc.__class__.__name__}", payload)
    try:
        data = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        data = {}
    message_id = str(data.get("messageId") or data.get("message_id") or "").strip() or None
    return EmailSendResult(True, False, False, message_id, utc_stamp(), "sent", payload)


def send_member_email(handle: str, text: str = "", *, name: str | None = None) -> EmailSendResult:
    return send_outreach_email(to_email=handle, to_name=name, opener=text)
