"""tg_capture — compress recent Telegram conversation turns into a brain note.

Pipeline (one run):
    1. Pull all unprocessed, non-private rows from brain_index.tg_messages,
       grouped by chat_id, ordered by `at`.
    2. If a chat has < MIN_TURNS turns and the most recent turn is < MIN_AGE_MIN
       old, skip it (let the conversation finish before compressing).
    3. Otherwise, hand the transcript to an LLM with a fixed compression prompt
       and parse a JSON object: { title, summary, key_insights[], tags[],
       sensitivity }.
    4. POST the compressed note to brain-index `/ingest/add_note` (which writes
       a row in `01 · Notes` AND embeds it into `note_chunks`).
    5. Mark all included tg_messages rows as processed (and stamp note_row_id).

Cadence: hourly. On-demand via `/capture` in tgbot.

Env knobs:
    SH_TG_CAPTURE_MIN_TURNS    (default 4)
    SH_TG_CAPTURE_MIN_AGE_MIN  (default 30)  — wait this long after last turn
    SH_TG_CAPTURE_MAX_TURNS    (default 60)  — hard cap per note
    BRAIN_INDEX_INGEST_TOKEN   — bearer token with `ingest` scope
    BRAIN_INDEX_URL            — defaults to http://127.0.0.1:28090
    SH_TG_CAPTURE_SENSITIVITY  — default sensitivity label (default "🟡 Personal")
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .. import llm
from ..db import connect
from ..telegram import send as tg_send, _esc as tg_esc

log = logging.getLogger("curator.tg_capture")


MIN_TURNS = int(os.environ.get("SH_TG_CAPTURE_MIN_TURNS") or "4")
MIN_AGE_MIN = int(os.environ.get("SH_TG_CAPTURE_MIN_AGE_MIN") or "30")
MAX_TURNS = int(os.environ.get("SH_TG_CAPTURE_MAX_TURNS") or "60")
DEFAULT_SENSITIVITY = os.environ.get("SH_TG_CAPTURE_SENSITIVITY") or "🟡 Personal"
BRAIN_INDEX_URL = os.environ.get("BRAIN_INDEX_URL") or "http://127.0.0.1:28090"


def _load_ingest_token() -> str | None:
    explicit = os.environ.get("BRAIN_INDEX_INGEST_TOKEN")
    if explicit:
        return explicit.strip()
    token_file = Path("/root/sh-brain-secrets/token-ingest.txt")
    if token_file.exists():
        return token_file.read_text().strip()
    return None


SYSTEM_PROMPT = """You are the Sunheart Brain's conversation compressor. The
owner (James) chats with you via Telegram about ideas, decisions, plans,
emotions, work, and life. Your job is to compress a chunk of conversation into
ONE durable memory the brain can retrieve later.

Output a single JSON object:
{
  "title": "≤10 words, action/topic-oriented",
  "summary": "3-7 short bullets capturing what happened. Use second person ('You said…') for the human's contributions and third person for the bot's. Plain English.",
  "key_insights": ["≤4 distinct durable insights worth remembering long-term — decisions made, frameworks named, contradictions surfaced, follow-ups committed to. Each ≤2 sentences."],
  "tags": ["3-6 short kebab-case tags relevant to the content"],
  "sensitivity": "personal" | "public",
  "skip": false
}

Rules:
- If the conversation is just small talk (greetings, jokes, no substance), set
  "skip": true and leave other fields empty. Don't waste the brain.
- Default sensitivity is "personal". Mark "public" only if it's purely an
  abstract/technical/philosophical discussion that contains nothing about
  James's private life, finances, relationships, health, or business specifics.
- Never fabricate. If the conversation references something you don't see in
  the transcript, say so in the summary.
"""


async def _gather_unprocessed() -> dict[str, list[dict]]:
    """Return dict of chat_id -> list of {at, role, text, id}."""
    grouped: dict[str, list[dict]] = {}
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, chat_id, at, role, text
                  FROM brain_index.tg_messages
                 WHERE processed_at IS NULL
                   AND NOT private_flag
                 ORDER BY chat_id, at
                """
            )
            for row in await cur.fetchall():
                rid, chat_id, at, role, text = row
                grouped.setdefault(str(chat_id), []).append(
                    {"id": rid, "at": at, "role": role, "text": text}
                )
    return grouped


def _ready_for_compress(turns: list[dict]) -> bool:
    if len(turns) < MIN_TURNS:
        return False
    last = turns[-1]["at"]
    age_min = (datetime.now(timezone.utc) - last).total_seconds() / 60.0
    return age_min >= MIN_AGE_MIN


def _format_transcript(turns: list[dict]) -> str:
    lines = []
    for t in turns:
        ts = t["at"].strftime("%Y-%m-%d %H:%M")
        speaker = "JAMES" if t["role"] == "user" else "BOT"
        lines.append(f"[{ts}] {speaker}: {t['text']}")
    return "\n".join(lines)


async def _compress_with_llm(transcript: str) -> dict[str, Any]:
    user = (
        "Compress this Telegram conversation into a durable brain memory. "
        "Return ONLY the JSON object — no surrounding prose.\n\n"
        "Transcript:\n" + transcript[:18000]
    )
    result = await llm.complete(
        SYSTEM_PROMPT, user, max_tokens=900, temperature=0.3, force_json=True
    )
    raw = result.text.strip()
    # Strip code-fence if model wrapped it.
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].lstrip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("LLM did not return JSON; raw=%r", raw[:300])
        raise RuntimeError(f"compressor returned non-JSON: {e}")
    return obj


async def _ingest_note(payload: dict[str, Any], chat_id: str, span: tuple[datetime, datetime]) -> str | None:
    """Push the compressed note through brain-index /ingest/add_note. Returns row_id."""
    token = _load_ingest_token()
    if not token:
        log.warning("no BRAIN_INDEX_INGEST_TOKEN; skipping ingest")
        return None
    sens_label = "🟢 Public" if payload.get("sensitivity") == "public" else "🟡 Personal"
    title = (payload.get("title") or "Telegram chat").strip()
    summary_lines = payload.get("summary") or []
    if isinstance(summary_lines, str):
        summary_lines = [summary_lines]
    insights = payload.get("key_insights") or []
    if isinstance(insights, str):
        insights = [insights]
    body_parts: list[str] = []
    body_parts.append(f"# {title}\n")
    body_parts.append(f"_Captured from Telegram chat {chat_id} · {span[0].isoformat()} → {span[1].isoformat()}_\n")
    if summary_lines:
        body_parts.append("## Summary")
        for s in summary_lines:
            body_parts.append(f"- {s}")
        body_parts.append("")
    if insights:
        body_parts.append("## Durable insights")
        for s in insights:
            body_parts.append(f"- {s}")
        body_parts.append("")
    content = "\n".join(body_parts).strip()
    source_id = f"tg-{chat_id}-{int(span[1].timestamp())}"
    body = {
        "source": "telegram-chat",
        "source_id": source_id,
        "title": title,
        "content": content,
        "tags": list(payload.get("tags") or []),
        "note_type": "Conversation",
        "original_created_at": span[1].isoformat(),
        "sensitivity": sens_label,
        "prefer": "local",  # Personal-tier never goes to OpenAI anyway
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{BRAIN_INDEX_URL}/ingest/add_note",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        if r.status_code >= 400:
            log.error("ingest /add_note failed %s: %s", r.status_code, r.text[:300])
            r.raise_for_status()
        data = r.json()
    return data.get("note_row_id")


async def _mark_processed(message_ids: list[Any], note_row_id: str | None) -> None:
    if not message_ids:
        return
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE brain_index.tg_messages
                   SET processed_at = NOW(),
                       note_row_id  = COALESCE(%s, note_row_id)
                 WHERE id = ANY(%s)
                """,
                (note_row_id, message_ids),
            )


async def run(run_id: str) -> dict[str, Any]:
    grouped = await _gather_unprocessed()
    notes_created = 0
    skipped_chats = 0
    total_turns = 0

    for chat_id, turns in grouped.items():
        if not _ready_for_compress(turns):
            skipped_chats += 1
            continue
        # Cap to MAX_TURNS oldest (so large backlogs get split across runs).
        chunk = turns[:MAX_TURNS]
        ids = [t["id"] for t in chunk]
        span = (chunk[0]["at"], chunk[-1]["at"])
        transcript = _format_transcript(chunk)
        try:
            payload = await _compress_with_llm(transcript)
        except Exception as e:
            log.warning("compression failed for chat %s: %s", chat_id, e)
            continue
        if payload.get("skip"):
            log.info("compressor said skip for chat %s (%d turns)", chat_id, len(chunk))
            await _mark_processed(ids, None)
            continue
        try:
            row_id = await _ingest_note(payload, chat_id, span)
        except Exception as e:
            log.warning("ingest failed for chat %s: %s", chat_id, e)
            continue
        await _mark_processed(ids, row_id)
        notes_created += 1
        total_turns += len(chunk)
        log.info(
            "tg_capture chat=%s turns=%d → note %s (title=%r)",
            chat_id, len(chunk), row_id, payload.get("title", "")[:60],
        )
        # Send a one-line confirmation back to the chat itself.
        try:
            await tg_send(
                f"🧠 Captured <b>{tg_esc(payload.get('title', 'recent chat'))}</b> "
                f"into your brain ({len(chunk)} turns)."
            )
        except Exception:
            pass

    log.info(
        "tg_capture run=%s notes=%d skipped_chats=%d turns=%d",
        run_id, notes_created, skipped_chats, total_turns,
    )
    return {
        "notes_created": notes_created,
        "skipped_chats": skipped_chats,
        "turns_compressed": total_turns,
    }
