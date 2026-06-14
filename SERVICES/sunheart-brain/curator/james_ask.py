"""james_ask — the reverse channel.

The river needs decisions from James to flow. This module gives any agent a
file-drop interface to queue a question, and the TG bot delivers it + matches
his reply back to the asking agent.

Usage (from any agent):
    from curator.james_ask import create_ask
    create_ask(
        question="Send a test voice memo to @sunheartbrain_bot?",
        context="Phase 2 wire is LIVE but unverified end-to-end.",
        from_agent="ember-main",
        priority="rapid",  # rapid · active · slow · dormant
        options=["Y · I'll send", "N · skip", "Later"],
    )

Usage (from tgbot poller loop):
    from curator.james_ask import send_pending, try_match_reply
    # In poll loop (every cycle):
    await send_pending(tg_send_fn)
    # In _handle_message before normal processing:
    matched = await try_match_reply(text, message_id)
    if matched: return  # reply consumed by the ask queue

Queue layout:
    ~/.config/fpai/james_ask_queue/
        pending/        # not yet sent · created by agents
        sent/           # delivered to TG · awaiting reply
        answered/       # James replied · waiting for asking-agent to ingest
        expired/        # not answered within TTL · agent should re-decide

Each file is JSON. Filename = ask_id = `ask_{YYYYMMDD}_{HHMMSS}_{slug}.json`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Awaitable, Callable, Optional

log = logging.getLogger("curator.james_ask")

_QUEUE_BASE = Path(
    os.environ.get(
        "JAMES_ASK_QUEUE_PATH",
        str(Path.home() / ".config" / "fpai" / "james_ask_queue"),
    )
).expanduser()

_PENDING = _QUEUE_BASE / "pending"
_SENT = _QUEUE_BASE / "sent"
_ANSWERED = _QUEUE_BASE / "answered"
_EXPIRED = _QUEUE_BASE / "expired"

_DEFAULT_TTL_HOURS = int(os.environ.get("JAMES_ASK_TTL_HOURS", "72"))

# Match-reply tolerance: if user replies and there's exactly N open ask(s)
# within this window, assume the reply belongs to the most recent ask.
_REPLY_MATCH_WINDOW_MIN = int(os.environ.get("JAMES_ASK_REPLY_WINDOW_MIN", "180"))


def _ensure_dirs() -> None:
    for d in (_PENDING, _SENT, _ANSWERED, _EXPIRED):
        d.mkdir(parents=True, exist_ok=True)


def _slugify(s: str, max_len: int = 32) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (s or "").lower()).strip("-")
    return (s[:max_len] or "ask").rstrip("-")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_ask(
    question: str,
    context: str = "",
    from_agent: str = "unknown",
    priority: str = "rapid",
    options: list[str] | None = None,
    metadata: dict | None = None,
    callback_path: str | None = None,
) -> str:
    """Drop an ask into pending/. Returns ask_id.

    `callback_path` (optional) is a file path the asking agent watches — when
    James answers, the answered/ file is also copied there so the agent gets
    notified without polling the central queue.
    """
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ask_id = f"ask_{ts}_{_slugify(question, 32)}_{uuid.uuid4().hex[:6]}"
    payload = {
        "id": ask_id,
        "from_agent": from_agent,
        "priority": priority,
        "created_at": _now_iso(),
        "question": question,
        "context": context,
        "options": options or ["Y", "N", "Later"],
        "metadata": metadata or {},
        "callback_path": callback_path,
        "sent_at": None,
        "tg_message_id": None,
        "answered_at": None,
        "answer_text": None,
        "answer_tg_message_id": None,
    }
    path = _PENDING / f"{ask_id}.json"
    path.write_text(json.dumps(payload, indent=2))
    log.info("james_ask: queued %s · %s", ask_id, question[:60])
    return ask_id


def _load(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except Exception as e:
        log.warning("james_ask: failed to load %s: %s", path, e)
        return None


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def _format_for_tg(ask: dict, esc_fn: Callable[[str], str] | None = None) -> str:
    esc = esc_fn or (lambda x: x)
    priority_icon = {
        "rapid": "⚡",
        "active": "🌀",
        "slow": "🍃",
        "dormant": "💤",
    }.get(ask.get("priority", "rapid"), "⚡")
    parts = [
        f"🟡 <b>Need from you</b> {priority_icon} <i>{esc(ask.get('priority', 'rapid'))}</i>",
        "",
        f"<b>Q:</b> {esc(ask['question'])}",
    ]
    if ask.get("context"):
        parts += ["", f"<i>{esc(ask['context'])}</i>"]
    if ask.get("options"):
        parts += ["", "<b>Options:</b>"]
        for opt in ask["options"]:
            parts.append(f"  • {esc(opt)}")
    parts += [
        "",
        f"<i>Reply in plain text — first reply within {_REPLY_MATCH_WINDOW_MIN}m maps to this ask.</i>",
        f"<code>ask_id: {esc(ask['id'])}</code>",
        f"<i>from {esc(ask.get('from_agent', 'unknown'))}</i>",
    ]
    return "\n".join(parts)


async def send_pending(
    tg_send: Callable[..., Awaitable[Optional[dict]]],
    esc_fn: Callable[[str], str] | None = None,
    max_per_tick: int = 3,
) -> int:
    """Deliver pending asks to TG. Returns number sent.

    `tg_send` should accept a single text argument + optional parse_mode and
    return the Telegram response dict (so we can capture message_id).
    """
    _ensure_dirs()
    pending = sorted(_PENDING.glob("ask_*.json"))
    if not pending:
        return 0
    sent_count = 0
    for path in pending[:max_per_tick]:
        ask = _load(path)
        if not ask:
            continue
        text = _format_for_tg(ask, esc_fn=esc_fn)
        try:
            tg_response = await tg_send(text)
        except Exception as e:
            log.warning("james_ask: tg_send failed for %s: %s", ask["id"], e)
            continue
        tg_msg_id = None
        if isinstance(tg_response, dict):
            tg_msg_id = (tg_response.get("result") or tg_response).get("message_id")
        ask["sent_at"] = _now_iso()
        ask["tg_message_id"] = tg_msg_id
        _save(_SENT / path.name, ask)
        path.unlink(missing_ok=True)
        sent_count += 1
        log.info("james_ask: sent %s (tg msg %s)", ask["id"], tg_msg_id)
    return sent_count


def _open_asks() -> list[dict]:
    """Asks that are SENT but not yet ANSWERED, sorted newest-first."""
    _ensure_dirs()
    out: list[dict] = []
    for path in _SENT.glob("ask_*.json"):
        ask = _load(path)
        if ask:
            out.append(ask)
    out.sort(key=lambda a: a.get("sent_at") or "", reverse=True)
    return out


async def try_match_reply(
    text: str,
    message_id: int | None = None,
) -> Optional[dict]:
    """If `text` looks like a reply to an open ask, record it and return the
    matched ask dict. Otherwise return None.

    Match heuristic (v1):
      1. If text contains an `ask_id: ...` token, exact-match on that.
      2. Else if exactly ONE open ask exists, assume the reply is for it.
      3. Else if multiple open asks · the MOST RECENT within the reply
         window claims the reply (best-effort).
    """
    _ensure_dirs()
    text_str = (text or "").strip()
    if not text_str:
        return None

    open_asks = _open_asks()
    if not open_asks:
        return None

    # Explicit ask_id token
    m = re.search(r"ask_\d{8}_\d{6}_[a-z0-9-]+_[a-f0-9]{6}", text_str)
    matched: Optional[dict] = None
    if m:
        target_id = m.group(0)
        for a in open_asks:
            if a["id"] == target_id:
                matched = a
                break

    # Single-open shortcut
    if not matched and len(open_asks) == 1:
        matched = open_asks[0]

    # Newest-within-window
    if not matched:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=_REPLY_MATCH_WINDOW_MIN)
        for a in open_asks:
            try:
                sent_dt = datetime.fromisoformat(a.get("sent_at") or "")
                if sent_dt >= cutoff:
                    matched = a
                    break
            except Exception:
                continue

    if not matched:
        return None

    # Record + move to answered/
    matched["answered_at"] = _now_iso()
    matched["answer_text"] = text_str
    matched["answer_tg_message_id"] = message_id

    sent_path = _SENT / f"{matched['id']}.json"
    answered_path = _ANSWERED / f"{matched['id']}.json"
    _save(answered_path, matched)
    sent_path.unlink(missing_ok=True)

    # Callback for the asking agent (if specified)
    cb = matched.get("callback_path")
    if cb:
        try:
            Path(cb).expanduser().parent.mkdir(parents=True, exist_ok=True)
            Path(cb).expanduser().write_text(json.dumps(matched, indent=2))
        except Exception as e:
            log.warning("james_ask: callback write failed for %s: %s", matched["id"], e)

    log.info("james_ask: matched reply to %s · %s chars", matched["id"], len(text_str))
    return matched


def expire_old(ttl_hours: int | None = None) -> int:
    """Move stale sent/ asks to expired/. Returns count expired."""
    _ensure_dirs()
    ttl = ttl_hours or _DEFAULT_TTL_HOURS
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl)
    count = 0
    for path in _SENT.glob("ask_*.json"):
        ask = _load(path)
        if not ask:
            continue
        try:
            sent_dt = datetime.fromisoformat(ask.get("sent_at") or "")
            if sent_dt < cutoff:
                _save(_EXPIRED / path.name, ask)
                path.unlink(missing_ok=True)
                count += 1
        except Exception:
            continue
    if count:
        log.info("james_ask: expired %d stale asks", count)
    return count


def status() -> dict:
    """Quick counts for footer/dashboard rendering."""
    _ensure_dirs()
    return {
        "pending": len(list(_PENDING.glob("ask_*.json"))),
        "sent": len(list(_SENT.glob("ask_*.json"))),
        "answered_unread": len(list(_ANSWERED.glob("ask_*.json"))),
        "expired": len(list(_EXPIRED.glob("ask_*.json"))),
    }
