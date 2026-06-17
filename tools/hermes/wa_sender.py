#!/usr/bin/env python3
"""Guarded Meta WhatsApp Cloud API sender for Hermes."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

GRAPH_VERSION = "v19.0"
WA_ID_RE = re.compile(r"^\+?[1-9]\d{6,15}$")
DEFAULT_TEMPLATE_RATE_LOG = Path.home() / ".config" / "fpai" / "wa_template_sends.jsonl"


@dataclass(frozen=True)
class WhatsAppSendResult:
    sent: bool
    dry_run: bool
    disabled: bool
    message_id: str | None
    sent_at: str | None
    reason: str
    payload: dict[str, Any]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_wa_id(value: str) -> str:
    wa_id = re.sub(r"[^\d+]", "", str(value or "").strip())
    if wa_id.startswith("+"):
        wa_id = wa_id[1:]
    if not WA_ID_RE.match(wa_id):
        raise ValueError("invalid WhatsApp id")
    return wa_id


def disabled_by_env(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("PROBE_DISABLE") == "1" or values.get("WHATSAPP_DISABLE") == "1"


def is_live_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("WHATSAPP_LIVE") == "1" and values.get("DRY_RUN", "1") != "1"


def graph_messages_url(phone_number_id: str, *, graph_version: str = GRAPH_VERSION) -> str:
    return f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages"


def _request_payload(payload: dict[str, Any], env: dict[str, str]) -> tuple[urllib.request.Request | None, str | None]:
    token = env.get("WA_ACCESS_TOKEN", "").strip()
    phone_number_id = env.get("WA_PHONE_NUMBER_ID", "").strip()
    if not token:
        return None, "missing_wa_access_token"
    if not phone_number_id:
        return None, "missing_wa_phone_number_id"
    request = urllib.request.Request(
        graph_messages_url(phone_number_id),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
        },
        method="POST",
    )
    return request, None


def _post_payload(
    payload: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
    urlopen: Any = urllib.request.urlopen,
) -> WhatsAppSendResult:
    values = env if env is not None else os.environ
    if disabled_by_env(values):
        return WhatsAppSendResult(False, False, True, None, None, "disabled", payload)
    if not is_live_enabled(values):
        return WhatsAppSendResult(False, True, False, None, None, "dry_run", payload)
    request, missing = _request_payload(payload, values)
    if missing:
        return WhatsAppSendResult(False, False, False, None, None, missing, payload)
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return WhatsAppSendResult(False, False, False, None, None, f"wa_error:{exc.__class__.__name__}", payload)
    try:
        data = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError:
        data = {}
    messages = data.get("messages") if isinstance(data, dict) else None
    first = messages[0] if isinstance(messages, list) and messages else {}
    message_id = str(first.get("id") or data.get("message_id") or "").strip() or None
    return WhatsAppSendResult(True, False, False, message_id, utc_stamp(), "sent", payload)


def send_session_message(
    to_wa_id: str,
    text: str,
    *,
    env: dict[str, str] | None = None,
    urlopen: Any = urllib.request.urlopen,
) -> WhatsAppSendResult:
    """Send a plain-text WhatsApp session reply, or return a dry-run result."""
    body = " ".join(str(text or "").split())
    if not body:
        raise ValueError("message text is required")
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalize_wa_id(to_wa_id),
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }
    return _post_payload(payload, env=env, urlopen=urlopen)


def _recent_template_count(history: Sequence[datetime], *, now: datetime) -> int:
    cutoff = now - timedelta(hours=1)
    return sum(1 for stamp in history if stamp >= cutoff)


def _template_rate_log_path(env: dict[str, str]) -> Path:
    return Path(env.get("WA_TEMPLATE_RATE_LOG") or DEFAULT_TEMPLATE_RATE_LOG)


def _prepare_template_rate_log(path: Path) -> str | None:
    parent = path.parent
    if parent.exists():
        if parent.stat().st_mode & 0o077:
            return "unsafe_template_rate_log_parent"
    else:
        parent.mkdir(parents=True, mode=0o700)
    if path.exists() and path.stat().st_mode & 0o077:
        return "unsafe_template_rate_log"
    return None


def _read_template_history(path: Path) -> list[datetime]:
    if not path.exists():
        return []
    stamps: list[datetime] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            data = json.loads(line)
            stamp = datetime.fromisoformat(str(data.get("sent_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        stamps.append(stamp)
    return stamps


def _append_template_send(path: Path, *, sent_at: datetime) -> None:
    row = {"sent_at": sent_at.strftime("%Y-%m-%dT%H:%M:%SZ")}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    os.chmod(path, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def send_template_message(
    to_wa_id: str,
    template_name: str,
    params: Sequence[str] | None = None,
    *,
    language: str = "en_US",
    env: dict[str, str] | None = None,
    template_history: Sequence[datetime] = (),
    now: datetime | None = None,
    urlopen: Any = urllib.request.urlopen,
) -> WhatsAppSendResult:
    """Send a pre-approved template only when WhatsApp live mode is explicitly enabled."""
    current = now or datetime.now(timezone.utc)
    values = env if env is not None else os.environ
    normalized_to = normalize_wa_id(to_wa_id)
    components: list[dict[str, Any]] = []
    if params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(param)} for param in params],
        })
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized_to,
        "type": "template",
        "template": {
            "name": str(template_name or "").strip(),
            "language": {"code": language},
            "components": components,
        },
    }
    if not payload["template"]["name"]:
        raise ValueError("template_name is required")
    if disabled_by_env(values) or not is_live_enabled(values):
        return _post_payload(payload, env=values, urlopen=urlopen)
    history = list(template_history)
    rate_log = _template_rate_log_path(values)
    if not template_history:
        unsafe_rate_log = _prepare_template_rate_log(rate_log)
        if unsafe_rate_log:
            return WhatsAppSendResult(False, False, False, None, None, unsafe_rate_log, payload)
        history.extend(_read_template_history(rate_log))
    if values.get("WA_BUSINESS_VERIFIED") != "1" and _recent_template_count(history, now=current) >= 10:
        return WhatsAppSendResult(False, False, False, None, None, "template_rate_limited", payload)
    unsafe_rate_log = _prepare_template_rate_log(rate_log)
    if unsafe_rate_log:
        return WhatsAppSendResult(False, False, False, None, None, unsafe_rate_log, payload)
    result = _post_payload(payload, env=values, urlopen=urlopen)
    if result.sent and values.get("WA_BUSINESS_VERIFIED") != "1":
        _append_template_send(rate_log, sent_at=current)
    return result


def generate_wa_link(pre_filled_text: str, *, phone_number: str | None = None, env: dict[str, str] | None = None) -> str:
    values = env if env is not None else os.environ
    number = phone_number or values.get("WA_LINK_NUMBER") or values.get("WA_PHONE_NUMBER") or values.get("WA_BUSINESS_PHONE")
    if not number:
        raise ValueError("WhatsApp link phone number is required")
    encoded = urllib.parse.quote(str(pre_filled_text or ""), safe="")
    return f"https://wa.me/{normalize_wa_id(number)}?text={encoded}"
