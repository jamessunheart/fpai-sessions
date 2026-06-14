"""Opportunities scan — daily proactive surface of 3 concrete deliverables.

Ported from Adam's find-opportunities.sh. The disciplined piece is silence:
the model is explicitly allowed to return "NONE — keeping quiet today" and
when it does, no Telegram message is sent. $0 is a valid output.

Signals (all cheap):
    1. NOW.md priority + goals + open-questions sections
    2. Recent owner messages on Telegram (last 48h)
    3. Yesterday's ROI row (if present)
    4. Brain digest counts (chunks added 24h)
    5. Game KPI snapshot (best-effort, optional)

One LLM call → if substantive, DM the owner via tg.send. Either way, append
a JSONL row to /var/lib/sh-brain/opportunities.jsonl for the audit trail.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .. import telegram as tg
from ..db import connect
from ..llm import complete

log = logging.getLogger("curator.opportunities")


LEDGER_PATH = Path(os.environ.get("SH_OPPORTUNITIES_LEDGER", "/var/lib/sh-brain/opportunities.jsonl"))
ROI_LEDGER_PATH = Path(os.environ.get("SH_ROI_LEDGER", "/var/lib/sh-brain/roi.jsonl"))
STATE_DIR = os.environ.get("FPAI_STATE_DIR", "/var/lib/sh-brain/state")
NOW_PATH = Path(STATE_DIR) / "NOW.md"
FPAI_BASE = os.environ.get("FPAI_BASE_URL", "https://fullpotential.com")
OWNER_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SYSTEM_PROMPT = """You are the Sunheart Brain's daily opportunities scanner.
Your job: read the signals below and surface the TOP 3 concrete deliverables
where YOU (the brain / a Claude session) can help James in the next 24-48h.

Each opportunity must be:
  - Aligned with James's stated 30-day priority (visible in NOW.md excerpt)
  - Something a Claude session can actually execute (draft, summarize,
    research, organize, prepare, draft outreach copy)
  - Small enough to complete in <2 hours of session time
  - Framed as a specific deliverable he can say yes/no to

OUTPUT FORMAT (strict, no markdown headers, no code fences):

Opportunity 1: <one-line title>
  What: <1 sentence: the deliverable>
  Why now: <1 sentence: which signal prompted this>
  Time: <estimate, e.g. "~30 min">

Opportunity 2: ...
Opportunity 3: ...

Ask James: <one short question to greenlight which to start with>

Silence rule: If no real opportunities exist, output exactly:
NONE — keeping quiet today.

Do not fabricate. Do not echo unrelated noise like Telegram service messages,
billing-page boilerplate, or generic encouragement. If the signals don't
support a concrete deliverable, say NONE."""


async def run(run_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    signals = await _gather_signals()

    user_prompt = _render_prompt(signals)
    text = ""
    error: str | None = None
    try:
        result = await complete(
            SYSTEM_PROMPT,
            user_prompt,
            max_tokens=700,
            temperature=0.4,
            force_json=False,
        )
        text = (result.text or "").strip()
        model = result.model
    except Exception as e:
        log.warning("opportunities llm call failed: %s", e)
        error = str(e)
        model = "(call_failed)"

    silent = (not text) or text.upper().startswith("NONE") or "keeping quiet" in text.lower()
    sent = False
    if not silent and not error:
        sent = await _send_to_owner(text)

    row = {
        "schema": "sh_brain_opportunities_v1",
        "ts_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "run_id": run_id,
        "model": model,
        "silent": silent,
        "sent": sent,
        "error": error,
        "signal_summary": signals.get("summary", {}),
        "text": text[:4000],
    }

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    log.info(
        "opportunities run=%s silent=%s sent=%s error=%s",
        run_id, silent, sent, error,
    )
    return row


async def _gather_signals() -> dict[str, Any]:
    now_excerpt = _read_now_excerpt()
    recent_james = await _recent_james_messages()
    yesterday_roi = _last_roi_row()
    digest = await _brain_digest()
    game_kpis = await _game_kpis()

    summary = {
        "now_present": bool(now_excerpt),
        "james_msg_count_48h": len(recent_james),
        "roi_present": yesterday_roi is not None,
        "digest_present": digest is not None,
        "game_present": game_kpis is not None,
    }
    return {
        "now": now_excerpt,
        "james_messages": recent_james,
        "roi": yesterday_roi,
        "digest": digest,
        "game": game_kpis,
        "summary": summary,
    }


def _read_now_excerpt() -> str:
    try:
        text = NOW_PATH.read_text(encoding="utf-8")
    except Exception as e:
        log.warning("opportunities NOW.md read failed: %s", e)
        return ""
    keep_sections = (
        "🎯 30-day goal",
        "CURRENT PRIORITY",
        "GOALS",
        "OPEN QUESTIONS",
    )
    out_lines: list[str] = []
    capturing = False
    section_lines = 0
    for line in text.splitlines():
        if line.startswith("## "):
            capturing = any(k in line for k in keep_sections)
            section_lines = 0
            if capturing:
                out_lines.append(line)
        elif capturing:
            section_lines += 1
            if section_lines > 30:
                continue
            out_lines.append(line)
    return "\n".join(out_lines)[:4000]


async def _recent_james_messages() -> list[str]:
    if not OWNER_CHAT_ID:
        return []
    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT text
                      FROM brain_index.tg_messages
                     WHERE chat_id = %s
                       AND role = 'user'
                       AND at > NOW() - INTERVAL '48 hours'
                     ORDER BY at DESC
                     LIMIT 20
                    """,
                    (OWNER_CHAT_ID,),
                )
                rows = await cur.fetchall()
        return [(r[0] or "")[:300] for r in rows if r and r[0]]
    except Exception as e:
        log.warning("opportunities tg_messages query failed: %s", e)
        return []


def _last_roi_row() -> dict[str, Any] | None:
    if not ROI_LEDGER_PATH.exists():
        return None
    try:
        with ROI_LEDGER_PATH.open(encoding="utf-8") as f:
            last = ""
            for line in f:
                if line.strip():
                    last = line
        if not last:
            return None
        return json.loads(last)
    except Exception as e:
        log.warning("opportunities roi tail failed: %s", e)
        return None


async def _brain_digest() -> dict[str, Any] | None:
    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)::int
                      FROM brain_index.note_chunks
                     WHERE created_at > NOW() - INTERVAL '24 hours'
                    """
                )
                (new_chunks,) = await cur.fetchone()
                await cur.execute("SELECT COUNT(*)::int FROM brain_index.note_chunks")
                (total_chunks,) = await cur.fetchone()
        return {"new_chunks_24h": int(new_chunks or 0), "total_chunks": int(total_chunks or 0)}
    except Exception as e:
        log.warning("opportunities digest query failed: %s", e)
        return None


async def _game_kpis() -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=6.0) as c:
            list_r, board_r, retreat_r = (
                await c.get(f"{FPAI_BASE}/api/champion/list"),
                await c.get(f"{FPAI_BASE}/api/champion/leaderboard"),
                await c.get(f"{FPAI_BASE}/api/champion/retreat/list"),
            )
        listing = list_r.json() if list_r.status_code == 200 else {}
        board = board_r.json() if board_r.status_code == 200 else {}
        retreats = retreat_r.json() if retreat_r.status_code == 200 else {}
        return {
            "champions": listing.get("count", 0),
            "retreat_interests": retreats.get("count", 0),
            "top_field_score": (board.get("top_champions") or [{}])[0].get("field_score", 0),
        }
    except Exception as e:
        log.warning("opportunities game kpi fetch failed: %s", e)
        return None


def _render_prompt(signals: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append("---SIGNALS---\n")

    parts.append("[NOW.md priority + goals + open questions excerpt]")
    parts.append(signals.get("now") or "(NOW.md unavailable)")
    parts.append("")

    msgs = signals.get("james_messages") or []
    parts.append(f"[Owner messages on Telegram, last 48h — {len(msgs)} msgs]")
    if msgs:
        for m in msgs[:15]:
            parts.append(f"  · {m}")
    else:
        parts.append("  (no recent owner messages)")
    parts.append("")

    roi = signals.get("roi")
    if roi:
        parts.append("[Yesterday's ROI row]")
        parts.append(json.dumps({
            k: roi.get(k) for k in (
                "date",
                "bot_replies_24h",
                "james_messages_24h",
                "est_cost_usd_24h",
                "alerts",
            )
        }))
        parts.append("")

    digest = signals.get("digest")
    if digest:
        parts.append("[Brain ingest activity]")
        parts.append(json.dumps(digest))
        parts.append("")

    game = signals.get("game")
    if game:
        parts.append("[Game KPIs]")
        parts.append(json.dumps(game))
        parts.append("")

    parts.append("---")
    parts.append(
        "Now produce the 3-opportunity scan, OR output exactly "
        "`NONE — keeping quiet today.` if no concrete deliverable is supported "
        "by the signals above."
    )
    return "\n".join(parts)


async def _send_to_owner(text: str) -> bool:
    if not tg.enabled():
        return False
    body = (
        "💡 <b>Daily opportunities scan</b>\n"
        "<i>Three concrete things I could help with — reply with the number to greenlight.</i>\n\n"
        f"{tg._esc(text)}"
    )
    return await tg.send(body)
