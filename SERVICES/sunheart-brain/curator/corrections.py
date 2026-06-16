"""Correction capture for Telegram chat amnesia loops.

The correction loop is advisory memory: when James corrects a bot response, we
store the previous bot turn plus James's correction and inject recent failures
into future chat prompts. Capture must never block the bot's normal answer path.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("curator.corrections")

DEFAULT_LIMIT = int(os.environ.get("SH_CORRECTIONS_CONTEXT_LIMIT", "10"))
SUPABASE_TIMEOUT_SECONDS = float(os.environ.get("SH_CORRECTIONS_TIMEOUT_SECONDS", "2.0"))
_NEGATION_START = re.compile(
    r"^\s*(no|nope|nah|not quite|wrong|incorrect|actually|rather|instead)\b[\s,:;-]+(.+)",
    re.IGNORECASE | re.DOTALL,
)
_EXPLICIT_CORRECTION = re.compile(
    r"\b(you forgot|you said|you told me|you missed|you keep forgetting|"
    r"that's not|that is not|i already told you|i said)\b",
    re.IGNORECASE,
)
_NEGATION_RESTATEMENT = re.compile(
    r"\b(?:not|isn't|wasn't|aren't|weren't|don't|didn't|doesn't)\b.+"
    r"\b(?:it is|it's|its|i am|i'm|we are|we're|the answer is|actually|instead|rather)\b",
    re.IGNORECASE | re.DOTALL,
)

_REPO_ROOT = Path(os.environ.get("FPAI_REPO", "/opt/fpai-build/FPAI_Cockpit"))
_manager_path = _REPO_ROOT / "curator" / "blueprints" / "manager.py"
try:
    _spec = importlib.util.spec_from_file_location("fpai_blueprint_manager", _manager_path)
    _manager = importlib.util.module_from_spec(_spec) if _spec and _spec.loader else None
    if _manager and _spec and _spec.loader:
        _spec.loader.exec_module(_manager)
        detect_module_from_text = _manager.detect_module_from_text
        update_blueprint_after_correction = _manager.update_blueprint_after_correction
    else:
        detect_module_from_text = None
        update_blueprint_after_correction = None
except Exception:
    detect_module_from_text = None
    update_blueprint_after_correction = None


@dataclass(frozen=True)
class CorrectionSignal:
    matched: bool
    reason: str = ""


@dataclass(frozen=True)
class BotTurn:
    id: str
    text: str


@dataclass(frozen=True)
class CorrectionPair:
    conversation_id: str
    bot_turn_id: str
    original_response: str
    james_correction: str
    captured_at: str | None = None


def detect_correction_signal(text: str) -> CorrectionSignal:
    """Detect explicit or common conversational correction shapes."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return CorrectionSignal(False)
    if _EXPLICIT_CORRECTION.search(cleaned):
        return CorrectionSignal(True, "explicit")
    if _NEGATION_RESTATEMENT.search(cleaned):
        return CorrectionSignal(True, "negation_restatement")
    match = _NEGATION_START.search(cleaned)
    if match and len(match.group(2).strip()) >= 8:
        return CorrectionSignal(True, "negation_prefix")
    return CorrectionSignal(False)


async def capture_if_correction(
    *,
    conversation_id: str,
    james_message: str,
    bot_turn: BotTurn | None = None,
) -> CorrectionPair | None:
    """Capture James's correction against the previous bot turn if detected."""
    signal = detect_correction_signal(james_message)
    if not signal.matched:
        return None
    if bot_turn is None:
        bot_turn = await fetch_previous_bot_turn(conversation_id)
    if not bot_turn or not bot_turn.text.strip():
        return None
    pair = CorrectionPair(
        conversation_id=str(conversation_id),
        bot_turn_id=str(bot_turn.id),
        original_response=bot_turn.text[:8000],
        james_correction=james_message[:8000],
    )
    await write_correction(pair)
    _update_blueprint_gap(james_message, context=bot_turn.text)
    log.info("captured correction conversation=%s bot_turn=%s reason=%s", conversation_id, bot_turn.id, signal.reason)
    return pair


def _update_blueprint_gap(correction_text: str, *, context: str = "") -> None:
    if os.environ.get("BLUEPRINTS_DISABLE") == "1" or not update_blueprint_after_correction:
        return
    try:
        module = detect_module_from_text(f"{context}\n{correction_text}") if detect_module_from_text else ""
        update_blueprint_after_correction(module or "ember", correction_text)
    except Exception as e:
        log.warning("blueprint correction update failed: %s", e)


async def fetch_previous_bot_turn(conversation_id: str) -> BotTurn | None:
    """Return the latest bot row from brain_index.tg_messages for this chat."""
    try:
        from .db import connect

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id::text, text
                      FROM brain_index.tg_messages
                     WHERE chat_id = %s
                       AND role = 'bot'
                     ORDER BY at DESC
                     LIMIT 1
                    """,
                    (str(conversation_id),),
                )
                row = await cur.fetchone()
    except Exception as e:
        log.warning("previous bot turn lookup failed: %s", e)
        return None
    if not row:
        return None
    return BotTurn(id=str(row[0]), text=str(row[1] or ""))


async def write_correction(pair: CorrectionPair) -> None:
    """Write a correction pair to the local brain DB and optional Supabase REST."""
    try:
        from .db import connect

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.corrections
                        (conversation_id, bot_turn_id, original_response, james_correction)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        pair.conversation_id,
                        pair.bot_turn_id,
                        pair.original_response,
                        pair.james_correction,
                    ),
                )
    except Exception as e:
        log.warning("local correction write failed: %s", e)
    try:
        await _write_supabase_correction(pair)
    except Exception as e:
        log.warning("supabase correction write failed: %s", e)


async def recent_corrections(
    *,
    conversation_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[CorrectionPair]:
    """Return most recent correction pairs, preferring Supabase when configured."""
    rows = await _read_supabase_corrections(conversation_id=conversation_id, limit=limit)
    if rows:
        return rows
    try:
        from .db import connect
    except ImportError:
        return []

    try:
        clauses = []
        params: list[Any] = []
        if conversation_id:
            clauses.append("conversation_id = %s")
            params.append(str(conversation_id))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, limit))
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT conversation_id, bot_turn_id::text, original_response,
                           james_correction, captured_at::text
                      FROM brain_index.corrections
                      {where}
                     ORDER BY captured_at DESC
                     LIMIT %s
                    """,
                    params,
                )
                db_rows = await cur.fetchall()
    except Exception as e:
        log.warning("recent corrections lookup failed: %s", e)
        return []
    return [_pair_from_row(row) for row in db_rows]


def render_corrections_block(pairs: list[CorrectionPair], *, max_chars: int = 1400) -> str:
    if not pairs:
        return ""
    shown = pairs[:DEFAULT_LIMIT]
    lines = [
        "Recent corrections James made to this bot:",
        "Use these as failure memory. If a new question touches one, prefer James's correction over the old answer.",
    ]
    fixed_len = len("\n".join(lines)) + (len(shown) * len("\n- Bot said: \n  James corrected: "))
    per_field_limit = min(260, max(40, (max_chars - fixed_len - 24) // max(2, len(shown) * 2)))
    for pair in shown:
        lines.append(f"- Bot said: {_clean(pair.original_response, per_field_limit)}")
        lines.append(f"  James corrected: {_clean(pair.james_correction, per_field_limit)}")
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


async def _write_supabase_correction(pair: CorrectionPair) -> None:
    url, key, table = _supabase_settings()
    if not url or not key:
        return
    payload = {
        "conversation_id": pair.conversation_id,
        "bot_turn_id": pair.bot_turn_id,
        "original_response": pair.original_response,
        "james_correction": pair.james_correction,
    }
    async with httpx.AsyncClient(timeout=SUPABASE_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{url}/rest/v1/{table}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "content-type": "application/json",
                "Prefer": "return=minimal",
            },
            json=payload,
        )
        response.raise_for_status()


async def _read_supabase_corrections(
    *,
    conversation_id: str | None,
    limit: int,
) -> list[CorrectionPair]:
    url, key, table = _supabase_settings()
    if not url or not key:
        return []
    params: dict[str, str] = {
        "select": "conversation_id,bot_turn_id,original_response,james_correction,captured_at",
        "order": "captured_at.desc",
        "limit": str(max(1, limit)),
    }
    if conversation_id:
        params["conversation_id"] = f"eq.{conversation_id}"
    try:
        async with httpx.AsyncClient(timeout=SUPABASE_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{url}/rest/v1/{table}",
                params=params,
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
            )
            response.raise_for_status()
            rows = response.json()
    except Exception as e:
        log.warning("supabase corrections read failed: %s", e)
        return []
    if not isinstance(rows, list):
        return []
    return [_pair_from_mapping(row) for row in rows if isinstance(row, dict)]


def _supabase_configured() -> bool:
    url, key, _ = _supabase_settings()
    return bool(url and key)


def _supabase_settings() -> tuple[str, str, str]:
    url = os.environ.get("FPAI_SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("FPAI_SUPABASE_KEY", "") or os.environ.get("SUPABASE_ANON_KEY", "")
    table = os.environ.get("FPAI_CORRECTIONS_TABLE", "corrections")
    return url, key, table


def _pair_from_row(row: Any) -> CorrectionPair:
    return CorrectionPair(
        conversation_id=str(row[0]),
        bot_turn_id=str(row[1]),
        original_response=str(row[2] or ""),
        james_correction=str(row[3] or ""),
        captured_at=str(row[4] or "") or None,
    )


def _pair_from_mapping(row: dict[str, Any]) -> CorrectionPair:
    return CorrectionPair(
        conversation_id=str(row.get("conversation_id") or ""),
        bot_turn_id=str(row.get("bot_turn_id") or ""),
        original_response=str(row.get("original_response") or ""),
        james_correction=str(row.get("james_correction") or ""),
        captured_at=str(row.get("captured_at") or "") or None,
    )


def _clean(text: str, limit: int) -> str:
    return " ".join((text or "").split())[:limit]
