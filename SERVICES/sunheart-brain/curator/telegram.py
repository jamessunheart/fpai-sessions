"""curator/telegram.py — proactive notifications for pending proposals.

Outbound-only. We don't poll the bot, so this coexists with any other system
that uses the same bot token (e.g. concierge).

Configured via env vars (loaded from /etc/sh-brain/curator.env):
    TELEGRAM_BOT_TOKEN     — bot token (required to send anything)
    TELEGRAM_CHAT_ID       — numeric chat id of the human owner (required)
    SH_QUEUE_VIEW_URL      — direct link to '07 · Curator Queue' in AppFlowy
                             (defaults to https://brain.sunheart.com)

If either of the first two is missing, all functions silently no-op so jobs
never fail just because Telegram is misconfigured.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

import httpx

log = logging.getLogger("curator.telegram")


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
QUEUE_URL = os.environ.get(
    "SH_QUEUE_VIEW_URL",
    "https://brain.sunheart.com",
)


def enabled() -> bool:
    return bool(BOT_TOKEN and CHAT_ID)


def _esc(s: str) -> str:
    """Escape characters that have meaning in Telegram HTML mode."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


async def send(text: str, *, parse_mode: str = "HTML", reply_markup: dict | None = None) -> bool:
    """Send a message. `text` is expected to already be HTML-safe (use _esc on
    user-supplied substrings; <b>, <i>, <a href="...">…</a>, <code> are fine).
    `reply_markup` accepts a Telegram inline keyboard dict.
    """
    if not enabled():
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload: dict = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            if r.status_code != 200:
                log.warning("telegram send %s: %s", r.status_code, r.text[:200])
                return False
            return True
    except Exception as e:
        log.warning("telegram send error: %s", e)
        return False


async def send_voice(audio_bytes: bytes, *, caption: str | None = None,
                     filename: str = "reply.ogg", mime: str = "audio/ogg") -> bool:
    """Send a voice message via Telegram's sendVoice endpoint.

    Telegram requires OGG Opus for the native voice-bubble UX. If audio is in
    another format (e.g. MP3 from OpenAI tts-1), the caller should transcode
    first OR fall back to sendAudio (still playable, but renders as a file).
    """
    if not enabled():
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
    data: dict = {"chat_id": CHAT_ID}
    if caption:
        data["caption"] = caption[:1024]
        data["parse_mode"] = "HTML"
    files = {"voice": (filename, audio_bytes, mime)}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, data=data, files=files)
            if r.status_code != 200:
                log.warning("telegram send_voice %s: %s", r.status_code, r.text[:300])
                return False
            return True
    except Exception as e:
        log.warning("telegram send_voice error: %s", e)
        return False


async def send_audio(audio_bytes: bytes, *, caption: str | None = None,
                     filename: str = "reply.mp3", mime: str = "audio/mpeg") -> bool:
    """Fallback for non-OGG formats (MP3). Renders as audio player in TG."""
    if not enabled():
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
    data: dict = {"chat_id": CHAT_ID, "title": "Brain reply"}
    if caption:
        data["caption"] = caption[:1024]
        data["parse_mode"] = "HTML"
    files = {"audio": (filename, audio_bytes, mime)}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, data=data, files=files)
            if r.status_code != 200:
                log.warning("telegram send_audio %s: %s", r.status_code, r.text[:300])
                return False
            return True
    except Exception as e:
        log.warning("telegram send_audio error: %s", e)
        return False


async def edit_message(chat_id: int | str, message_id: int, text: str, *, parse_mode: str = "HTML") -> bool:
    """Edit an existing message (used after a button is tapped to reflect new state)."""
    if not BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
            return r.status_code == 200
    except Exception as e:
        log.warning("telegram edit error: %s", e)
        return False


async def answer_callback(callback_id: str, text: str = "", *, alert: bool = False) -> bool:
    """Acknowledge a button press so Telegram dismisses the spinner."""
    if not BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={
                "callback_query_id": callback_id,
                "text": text,
                "show_alert": alert,
            })
            return r.status_code == 200
    except Exception as e:
        log.warning("telegram answer_callback error: %s", e)
        return False


async def notify_job_summary(
    job_name: str,
    pending: Iterable[tuple[str, str]] | Iterable[str],
    *,
    run_id: str | None = None,
    extra: str | None = None,
) -> bool:
    """One message per job run summarising what's awaiting human approval.
    `pending` is a list of (row_id, title) tuples; plain strings are accepted
    for backwards compatibility (in which case no per-row buttons are shown).
    Each row gets ✅ Approve / ❌ Reject inline buttons.
    """
    rows: list[tuple[str | None, str]] = []
    for item in pending:
        if isinstance(item, str):
            rows.append((None, item))
        elif item:
            rid, title = item
            rows.append((rid, title))
    rows = [r for r in rows if r[1]]
    if not rows and not extra:
        return False
    icon = {
        "council":  "🧠",
        "dedup":    "🔗",
        "summarize":"📝",
        "cluster-tag": "🏷️",
        "triage":   "🛡️",
        "digest":   "📊",
    }.get(job_name, "🟡")
    lines = [f"{icon} <b>Brain · {_esc(job_name)}</b> — {len(rows)} pending"]
    keyboard: list[list[dict]] = []
    for idx, (rid, title) in enumerate(rows[:8], start=1):
        lines.append(f"<b>{idx}.</b> {_esc(title[:120])}")
        if rid:
            keyboard.append([
                {"text": f"✅ {idx}", "callback_data": f"r:{rid}:approve"},
                {"text": f"❌ {idx}", "callback_data": f"r:{rid}:reject"},
            ])
    if len(rows) > 8:
        lines.append(f"<i>…and {len(rows) - 8} more</i>")
    if extra:
        lines.append("")
        lines.append(_esc(extra))
    lines.append("")
    lines.append(f'<a href="{_esc(QUEUE_URL)}">Open queue →</a>')
    if run_id:
        lines.append(f"<i>run {_esc(run_id)}</i>")
    if run_id and rows:
        keyboard.append([
            {"text": "✅ Approve all low-risk", "callback_data": f"b:{run_id}:approve_low"},
            {"text": "❌ Reject all", "callback_data": f"b:{run_id}:reject_all"},
        ])
    keyboard.append([{"text": "Open queue in AppFlowy", "url": QUEUE_URL}])
    return await send(
        "\n".join(lines),
        reply_markup={"inline_keyboard": keyboard} if keyboard else None,
    )
