"""sh-brain-tgbot — long-polling worker for @Adamclaw_bot.

Two responsibilities:

    1. Handle button taps on queue notifications:
       ✅ Approve / ❌ Reject → update AppFlowy + execute applier + edit msg.

    2. Handle natural-language messages from the owner:
       Any text DM → semantic search across the brain → LLM-synthesized answer
       with sources. Slash commands recognised:
            /help     — show commands
            /pending  — list 🟡 Proposed queue rows with buttons
            /digest   — show today's brain digest stats
            /search <q> — same as plain text query

    All non-owner messages are silently ignored.

Run with:
    python3 -m curator tgbot

Env (reads /etc/sh-brain/curator.env):
    TELEGRAM_BOT_TOKEN   — must be the @Adamclaw_bot token
    TELEGRAM_CHAT_ID     — owner's chat id; only this user is honored
    SH_TGBOT_OFFSET_FILE — file storing last update_id (default /var/lib/sh-brain/tgbot.offset)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import telegram as tg
from .appflowy import AppFlowy
from .proposals import SAFE_AUTO_APPLY

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("curator.tgbot")


OFFSET_FILE = Path(os.environ.get("SH_TGBOT_OFFSET_FILE", "/var/lib/sh-brain/tgbot.offset"))
OWNER_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# In-memory privacy mode: when active, neither inbound nor outbound messages are
# logged to brain_index.tg_messages. Toggle with /private and /public.
_PRIVATE_MODE: dict[str, bool] = {}


async def _log_tg_message(chat_id: str, role: str, text: str,
                           update_id: int | None = None,
                           private_flag: bool = False) -> None:
    """Persist a Telegram turn into brain_index.tg_messages."""
    if not text or not chat_id:
        return
    if _PRIVATE_MODE.get(str(chat_id)):
        private_flag = True
    try:
        from .db import connect
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.tg_messages
                        (chat_id, role, text, private_flag, update_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (str(chat_id), role, text[:8000], private_flag, update_id),
                )
    except Exception as e:
        log.warning("tg_messages log failed (role=%s): %s", role, e)


def _load_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip()) if OFFSET_FILE.exists() else 0
    except Exception:
        return 0


def _save_offset(offset: int) -> None:
    try:
        OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
        OFFSET_FILE.write_text(str(offset))
    except Exception as e:
        log.warning("offset save failed: %s", e)


async def _poll_updates(client: httpx.AsyncClient, offset: int) -> list[dict]:
    """Long-poll Telegram for callback_query and message updates."""
    url = f"https://api.telegram.org/bot{tg.BOT_TOKEN}/getUpdates"
    try:
        r = await client.get(url, params={
            "offset": offset,
            "timeout": 25,
            "allowed_updates": json.dumps(["callback_query", "message"]),
        }, timeout=35)
    except httpx.TimeoutException:
        return []
    except Exception as e:
        log.warning("getUpdates error: %s", e)
        await asyncio.sleep(2)
        return []
    if r.status_code != 200:
        log.warning("getUpdates %s: %s", r.status_code, r.text[:200])
        await asyncio.sleep(5)
        return []
    return r.json().get("result", []) or []


async def _apply_immediately(af: AppFlowy, row_id: str, ptype: str, diff: dict) -> str:
    """Best-effort instant apply for the row that was just approved.
    Returns a short status string to put in the edited message."""
    try:
        from .jobs.apply_approved import APPLIERS
        applier = APPLIERS.get(ptype)
        if not applier:
            return f"approved · type '{ptype}' will run on next 15-min cycle"
        _, notes_db_id = await af.find_database_id("01 · Notes")
        result = await applier(af, notes_db_id, diff)
        return f"applied · {result}"
    except Exception as e:
        log.warning("instant apply failed for %s: %s", row_id, e)
        return f"approved · apply error ({e}); will retry on next cycle"


def _parse_diff(cells: dict) -> dict:
    try:
        diff_payload = json.loads(cells.get("Diff") or "{}")
        diff = diff_payload.get("diff") if isinstance(diff_payload, dict) and "diff" in diff_payload else diff_payload
        return diff if isinstance(diff, dict) else {}
    except Exception:
        return {}


def _proposal_type(cells: dict) -> str:
    # Primary path: explicit Type field in AppFlowy queue.
    ptype = str(cells.get("Type") or "").strip().lower()
    if ptype:
        return ptype
    # Fallback: Diff payload metadata (schema-safe even if Type select is blank).
    try:
        payload = json.loads(cells.get("Diff") or "{}")
        if isinstance(payload, dict):
            ptype = str(payload.get("proposal_type") or "").strip().lower()
            if ptype:
                return ptype
            diff = payload.get("diff")
            if isinstance(diff, dict):
                ptype = str(diff.get("type") or "").strip().lower()
                if ptype:
                    return ptype
    except Exception:
        pass
    return ""


def _is_low_risk_row(cells: dict) -> bool:
    ptype = _proposal_type(cells)
    confidence = str(cells.get("Confidence") or "")
    return ptype in SAFE_AUTO_APPLY and confidence.startswith("🟢 High")


async def _bulk_decide(af: AppFlowy, queue_db_id: str, run_id: str, action: str) -> dict:
    stats = {"matched": 0, "approved": 0, "rejected": 0, "skipped": 0, "errors": 0}
    ids = await af.list_rows(queue_db_id, limit=500)
    rows: list[tuple[str, dict]] = []
    for row_summary in ids:
        rid = row_summary.get("id")
        if not rid:
            continue
        try:
            detail = await af.get(
                f"/api/workspace/{af.workspace_id}/database/{queue_db_id}/row/detail",
                ids=rid,
            )
            data_obj = detail.get("data") or []
            row = data_obj[0] if isinstance(data_obj, list) and data_obj else (data_obj if isinstance(data_obj, dict) else {})
            cells = row.get("cells") or {}
        except Exception:
            continue
        if str(cells.get("Run ID") or "") != run_id:
            continue
        if not str(cells.get("Status") or "").startswith("🟡 Proposed"):
            continue
        rows.append((rid, cells))

    stats["matched"] = len(rows)
    now = datetime.now(timezone.utc).isoformat()
    for rid, cells in rows:
        ptype = _proposal_type(cells)
        try:
            if action == "approve_low":
                if not _is_low_risk_row(cells):
                    stats["skipped"] += 1
                    continue
                apply_msg = await _apply_immediately(af, rid, ptype, _parse_diff(cells))
                await af.update_row(queue_db_id, rid, {
                    "Status": "✅ Applied",
                    "Decided At": now,
                    "Decided By": "telegram-bulk",
                })
                log.info("bulk approve row=%s type=%s msg=%s", rid, ptype, apply_msg[:120])
                stats["approved"] += 1
            elif action == "reject_all":
                await af.update_row(queue_db_id, rid, {
                    "Status": "❌ Rejected",
                    "Decided At": now,
                    "Decided By": "telegram-bulk",
                })
                stats["rejected"] += 1
            else:
                stats["errors"] += 1
        except Exception as e:
            log.warning("bulk %s failed row=%s: %s", action, rid, e)
            stats["errors"] += 1
    return stats


async def _handle_callback(cb: dict) -> None:
    cb_id = cb.get("id")
    data = cb.get("data") or ""
    from_user = str((cb.get("from") or {}).get("id") or "")

    if OWNER_CHAT_ID and from_user != OWNER_CHAT_ID:
        log.warning("ignoring callback from non-owner user %s", from_user)
        await tg.answer_callback(cb_id, "Not authorized.", alert=True)
        return

    if data.startswith("b:"):
        parts = data.split(":", 2)
        if len(parts) != 3:
            await tg.answer_callback(cb_id, "Malformed bulk action.")
            return
        _, run_id, bulk_action = parts
        if bulk_action not in ("approve_low", "reject_all"):
            await tg.answer_callback(cb_id, "Unknown bulk action.")
            return
        await tg.answer_callback(cb_id, "⏳ Processing bulk action…")
        async with AppFlowy() as af:
            _, queue_db_id = await af.find_database_id("07 · Curator Queue")
            stats = await _bulk_decide(af, queue_db_id, run_id, bulk_action)
        if bulk_action == "approve_low":
            await tg.send(
                "✅ <b>Bulk low-risk approval complete</b>\n"
                f"run <code>{tg._esc(run_id)}</code>\n"
                f"matched: <b>{stats['matched']}</b> · approved: <b>{stats['approved']}</b> · "
                f"skipped: <b>{stats['skipped']}</b> · errors: <b>{stats['errors']}</b>"
            )
        else:
            await tg.send(
                "❌ <b>Bulk reject complete</b>\n"
                f"run <code>{tg._esc(run_id)}</code>\n"
                f"matched: <b>{stats['matched']}</b> · rejected: <b>{stats['rejected']}</b> · "
                f"errors: <b>{stats['errors']}</b>"
            )
        return

    if not data.startswith("r:"):
        await tg.answer_callback(cb_id, "Unknown action.")
        return

    parts = data.split(":", 2)
    if len(parts) != 3:
        await tg.answer_callback(cb_id, "Malformed callback.")
        return
    _, row_id, action = parts

    log.info("callback row=%s action=%s from=%s", row_id, action, from_user)

    async with AppFlowy() as af:
        _, queue_db_id = await af.find_database_id("07 · Curator Queue")

        # Pull current row to read Type + Diff so we can apply if approved.
        try:
            detail = await af.get(
                f"/api/workspace/{af.workspace_id}/database/{queue_db_id}/row/detail",
                ids=row_id,
            )
            data_obj = detail.get("data") or []
            row = data_obj[0] if isinstance(data_obj, list) and data_obj else (data_obj if isinstance(data_obj, dict) else {})
            cells = row.get("cells") or {}
        except Exception as e:
            log.error("row fetch failed %s: %s", row_id, e)
            await tg.answer_callback(cb_id, "Couldn't read the row.", alert=True)
            return

        proposal = cells.get("Proposal") or "(unknown)"
        ptype = _proposal_type(cells)
        current_status = (cells.get("Status") or "").strip()
        if current_status and not current_status.startswith("🟡 Proposed"):
            await tg.answer_callback(
                cb_id,
                f"Already decided: {current_status[:32]}",
                alert=False,
            )
            return
        diff = _parse_diff(cells)

        now = datetime.now(timezone.utc).isoformat()
        if action == "approve":
            new_status = "✅ Applied"
            await tg.answer_callback(cb_id, "✅ Processing approval…")
            apply_msg = await _apply_immediately(af, row_id, ptype, diff)
            try:
                await af.update_row(queue_db_id, row_id, {
                    "Status": new_status,
                    "Decided At": now,
                    "Decided By": "telegram",
                })
            except Exception as e:
                log.warning("status update failed %s: %s", row_id, e)
            footer = f"\n\n✅ <b>Approved · {tg._esc(apply_msg)}</b> · {now[:16].replace('T', ' ')} UTC"
        elif action == "reject":
            new_status = "❌ Rejected"
            await tg.answer_callback(cb_id, "❌ Processing rejection…")
            try:
                await af.update_row(queue_db_id, row_id, {
                    "Status": new_status,
                    "Decided At": now,
                    "Decided By": "telegram",
                })
            except Exception as e:
                log.warning("status update failed %s: %s", row_id, e)
            footer = f"\n\n❌ <b>Rejected</b> · {now[:16].replace('T', ' ')} UTC"
        else:
            await tg.answer_callback(cb_id, "Unknown action.")
            return

    # Keep the original keyboard message intact so the user can decide multiple
    # queued items in one pass. Send outcome as a separate status message.
    await tg.send(
        f"<b>{tg._esc(proposal[:200])}</b>\n"
        f"<i>type: {tg._esc(ptype)}</i>"
        f"{footer}"
    )


# ─────────────────────────────── chat handler ─────────────────────────────────
SEARCH_TOP_K = int(os.environ.get("SH_TGBOT_TOP_K", "8"))
SEARCH_SENSITIVITIES = ("public", "personal")  # never expose 'private' over chat
CITATION_LIMIT = int(os.environ.get("SH_TGBOT_CITATION_LIMIT", "6"))


CHAT_SYSTEM_PROMPT = """You are the Sunheart Brain — a personal second-brain
assistant for James. You answer questions using only the snippets retrieved
from his notes, AI conversations, and papers. Style:
- Plain English, direct, high-signal.
- Use this format:
  1) one concise paragraph answering the question directly;
  2) a short "Next moves" list (2-4 bullets) when action is relevant.
- Cite sources inline as [1], [2], etc (numbers only).
- If the snippets don't cover the question, say so clearly and suggest what
  he could capture next time.
- Never fabricate. Never say "as an AI...". Speak as the brain itself.
- Never output raw JSON, XML tags, or code fences in normal answers.
"""


async def _embed_query(text: str) -> list[float] | None:
    """Embed a single query string. Defaults to local Ollama (nomic-embed-text,
    768-dim) to match stored chunk dimensions. Override with
    SH_EMBED_PROVIDER=openai if all chunks have been re-embedded to 1536-dim.
    """
    provider = (os.environ.get("SH_EMBED_PROVIDER") or "ollama").lower()
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        model = os.environ.get("SH_EMBED_MODEL", "text-embedding-3-small")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": model, "input": text},
                )
                r.raise_for_status()
                return r.json()["data"][0]["embedding"]
        except Exception as e:
            log.warning("openai embed failed: %s", e)
            return None
    # Default: Ollama (matches ingest pipeline)
    base = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
    model = os.environ.get("SH_EMBED_MODEL", "nomic-embed-text")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{base}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            r.raise_for_status()
            return r.json().get("embedding")
    except Exception as e:
        log.warning("ollama embed failed: %s", e)
        return None


async def _search_brain(question: str, k: int = SEARCH_TOP_K) -> list[dict]:
    """Vector search against brain_index.note_chunks. Returns list of dicts."""
    embedding = await _embed_query(question)
    if not embedding:
        return []
    from .db import connect
    sensitivities = list(SEARCH_SENSITIVITIES)
    sql = """
        SELECT content, source, sensitivity, tags, created_at,
               1 - (embedding <=> %s::vector) AS score
          FROM brain_index.note_chunks
         WHERE sensitivity = ANY(%s)
         ORDER BY embedding <=> %s::vector
         LIMIT %s
    """
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (embedding, sensitivities, embedding, k))
            return [
                {
                    "content": (c or "")[:1200],
                    "source": s,
                    "sensitivity": sens,
                    "tags": tags or [],
                    "added": ct.strftime("%b %-d") if ct else "",
                    "score": float(score),
                }
                for c, s, sens, tags, ct, score in await cur.fetchall()
            ]


async def _synthesize_answer(question: str, hits: list[dict]) -> str:
    """Hand the chunks to Claude/GPT and get a natural answer."""
    if not hits:
        return ("I couldn't find anything in your brain about that. "
                "Either it hasn't been ingested yet, or it lives in the 🔴 Private "
                "tier (which I never serve over chat).")
    from .llm import complete
    user = "Question:\n" + question + "\n\nRelevant snippets from your brain:\n\n"
    for i, h in enumerate(hits, 1):
        user += (
            f"[{i}] source={h['source']}/{h['sensitivity']} "
            f"score={h['score']:.2f} tags={','.join(h['tags'][:4])}\n"
            f"{h['content']}\n\n"
        )
    user += (
        "Now answer in this format:\n"
        "1) one concise paragraph that directly answers the question;\n"
        "2) if relevant, a 'Next moves' list with 2-4 bullet points.\n"
        "Use only citations like [1], [2], [3].\n"
        "Do not output markdown code fences, XML tags, or raw JSON.\n"
        "Keep response compact."
    )
    try:
        result = await complete(CHAT_SYSTEM_PROMPT, user, max_tokens=800, temperature=0.4, force_json=False)
        return result.text.strip() or "(no response)"
    except Exception as e:
        log.exception("synthesis failed: %s", e)
        return f"⚠️ Brain synthesis hit an error: {e}"


async def _handle_command(text: str, chat_id: int) -> str | None:
    """Return a reply string for slash commands, or None to fall through to chat."""
    cmd, _, rest = text.lstrip("/").partition(" ")
    cmd = cmd.lower()
    if cmd in ("help", "start"):
        return (
            "<b>Sunheart Brain</b>\n"
            "Send any question — I'll search your brain and answer with sources.\n"
            "Conversations are auto-captured + compressed into your brain hourly.\n\n"
            "<b>Commands</b>\n"
            "  /projects — what Claude sessions are active across your projects\n"
            "  /pending — list pending queue items with approve buttons\n"
            "  /digest  — today's brain stats\n"
            "  /cohere  — run coherence council now (~30-60s)\n"
            "  /council — alias of /cohere\n"
            "  /capture — compress recent chat into a note now\n"
            "  /private — start a private session (next msgs not captured)\n"
            "  /public  — end private session (resume capture)\n"
            "  /forget  — delete the last 10 unprocessed turns from capture buffer\n"
            "  /search &lt;q&gt; — explicit search (same as plain text)\n"
            "  /help    — this message\n"
        )
    if cmd == "private":
        _PRIVATE_MODE[str(chat_id)] = True
        return ("🔒 <b>Private mode on.</b> Your next messages won't be saved into "
                "the brain. Send /public to resume capture.")
    if cmd == "public":
        _PRIVATE_MODE[str(chat_id)] = False
        return "🔓 <b>Private mode off.</b> Capture resumed."
    if cmd == "forget":
        try:
            from .db import connect
            async with connect() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        DELETE FROM brain_index.tg_messages
                         WHERE id IN (
                           SELECT id FROM brain_index.tg_messages
                            WHERE chat_id = %s AND processed_at IS NULL
                            ORDER BY at DESC LIMIT 10
                         )
                        RETURNING id
                        """,
                        (str(chat_id),),
                    )
                    n = len(await cur.fetchall())
            return f"🗑 Forgot the last {n} unprocessed turn(s)."
        except Exception as e:
            return f"⚠️ forget failed: {e}"
    if cmd == "capture":
        await tg.send("⏳ Compressing recent chat into a note…")
        asyncio.create_task(_run_capture_async())
        return None
    if cmd in ("council", "cohere"):
        await tg.send(
            "🧠 <b>Running coherence council (Claude × GPT)…</b>\n"
            "I will optimize for goals/intentions alignment + execution + recruiting actions.\n"
            "Takes ~30-90s. I'll send the summary when it's done."
        )
        asyncio.create_task(_run_council_async())
        return None
    if cmd == "pending":
        async with AppFlowy() as af:
            _, db_id = await af.find_database_id("07 · Curator Queue")
            ids = await af.list_rows(db_id, limit=80)
            rows = []
            for i in ids:
                rid = i.get("id")
                if not rid:
                    continue
                d = await af.get(
                    f"/api/workspace/{af.workspace_id}/database/{db_id}/row/detail",
                    ids=rid,
                )
                data = d.get("data") or []
                row = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
                cells = row.get("cells") or {}
                status = cells.get("Status") or ""
                prop = cells.get("Proposal") or ""
                if status.startswith("🟡 Proposed") and prop and not prop.startswith("Council brief") and not prop.startswith("Daily digest"):
                    rows.append((rid, prop))
                if len(rows) >= 8:
                    break
        if not rows:
            return "✅ Nothing pending. Brain queue is clear."
        # Send a fresh notify_job_summary-style message with buttons
        await tg.notify_job_summary("queue", rows, run_id="manual",
                                    extra="Fetched on /pending command. Tap to decide.")
        return None  # already replied via notify_job_summary
    if cmd == "digest":
        from .jobs import digest as d
        try:
            run_id = uuid.uuid4().hex[:12]
            stats = await d.run(run_id)
            return (
                f"📊 <b>Brain digest</b>\n"
                f"  total chunks: <b>{stats['totals']['chunks']}</b>\n"
                f"  total concepts: <b>{stats['totals']['concepts']}</b>\n"
                f"  new (24h): {sum(stats['last_24h']['new_chunks_by_sensitivity'].values())} chunks\n"
                f"  auto-merges (24h): {stats['last_24h']['auto_merges']}\n"
                f"  blocked queries (24h): {stats['last_24h']['blocked_queries']}"
            )
        except Exception as e:
            return f"⚠️ digest failed: {e}"
    if cmd == "search":
        q = rest.strip()
        if not q:
            return "Usage: /search &lt;your question&gt;"
        hits = await _search_brain(q)
        return await _synthesize_answer(q, hits)
    if cmd == "projects":
        return await _cmd_projects()
    return f"Unknown command: /{tg._esc(cmd)}. Try /help."


async def _cmd_projects() -> str:
    """Show all active Claude session states from the Sessions API.

    Companion to The Practice of Signaling §1 (Field → Founder rhythm).
    Answers "what am I in the middle of?" without James querying me directly.
    """
    import os as _os
    import httpx as _httpx
    from datetime import datetime as _dt
    api_url = _os.environ.get("SESSIONS_API_URL", "https://fullpotential.com/api/sessions")
    token = _os.environ.get("SESSIONS_API_TOKEN", "")
    headers = {"X-Sessions-Token": token} if token else {}
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"{api_url.rstrip('/')}/list", headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"📡 <b>Projects</b>\n\nCould not reach the sessions API: {tg._esc(str(e))}"
    sessions = data.get("sessions", [])
    if not sessions:
        return (
            "📡 <b>Projects</b>\n\n"
            "<i>No active sessions tracked yet.</i>\n\n"
            "Push state from any Claude session:\n"
            "<code>python3 tools/session_state.py update --quest 'X' --next-move 'Y'</code>"
        )

    def _rel(iso: str) -> str:
        if not iso:
            return ""
        try:
            d = _dt.fromisoformat(iso)
            diff = (_dt.now() - d).total_seconds()
            if diff < 60: return f"{int(diff)}s ago"
            if diff < 3600: return f"{int(diff//60)}m ago"
            if diff < 86400: return f"{int(diff//3600)}h ago"
            return f"{int(diff//86400)}d ago"
        except Exception:
            return ""

    glyphs = {"active": "🟢", "paused": "⏸", "blocked": "🛑", "complete": "✓"}
    lines = ["📡 <b>Projects — what you're in the middle of</b>\n"]
    for s in sessions[:10]:
        glyph = glyphs.get((s.get("status") or "").lower(), "•")
        project = tg._esc(s.get("project", "?"))
        loop = s.get("loop_number")
        loop_str = f" · Loop {loop}" if loop is not None else ""
        last = _rel(s.get("last_activity", ""))
        lines.append(f"\n{glyph} <b>{project}</b>{loop_str} <i>· {tg._esc(last)}</i>")
        if s.get("quest"):
            lines.append(f"  Quest: {tg._esc(s['quest'])}")
        if s.get("next_move"):
            lines.append(f"  Next: <i>{tg._esc(s['next_move'])}</i>")
        if s.get("branch"):
            lines.append(f"  Branch: <code>{tg._esc(s['branch'])}</code>")
    if len(sessions) > 10:
        lines.append(f"\n<i>... and {len(sessions) - 10} more.</i>")
    return "\n".join(lines)


async def _handle_message(msg: dict) -> None:
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    from_user = str((msg.get("from") or {}).get("id") or "")
    text = (msg.get("text") or "").strip()
    update_id = msg.get("message_id")  # not the update_id, but unique-ish
    if not text or not chat_id:
        return
    if OWNER_CHAT_ID and from_user != OWNER_CHAT_ID:
        log.info("ignoring message from non-owner user %s", from_user)
        return

    # Slash commands first (do NOT log them — they're not part of the conversation).
    if text.startswith("/"):
        try:
            reply = await _handle_command(text, chat_id)
        except Exception as e:
            log.exception("command failed: %s", e)
            reply = f"⚠️ command error: {e}"
        if reply is not None:
            await tg.send(reply)
        return

    # Plain text path — log inbound, answer, log outbound.
    await _log_tg_message(str(chat_id), "user", text, update_id=update_id)

    log.info("chat: %s", text[:120])
    hits = await _search_brain(text)
    answer = _format_answer_for_telegram(await _synthesize_answer(text, hits))
    # Citation footer: show all hits with a short preview
    if hits:
        cite_lines = ["", "<b>Sources</b> <i>([N] in answer maps here)</i>"]
        show = hits[: max(1, CITATION_LIMIT)]
        for i, h in enumerate(show, start=1):
            preview = _make_preview(h["content"])
            date = f" · <i>{tg._esc(h['added'])}</i>" if h.get("added") else ""
            cite_lines.append(f"<i>[{i}]</i> <code>{tg._esc(h['source'])}</code>{date}")
            cite_lines.append(f"{tg._esc(preview)}")
        if len(hits) > len(show):
            cite_lines.append(f"<i>…+{len(hits) - len(show)} more matches</i>")
        answer += "\n" + "\n".join(cite_lines)
    await tg.send(answer)
    # Log outbound (the synthesized answer text only — no need to store sources block).
    await _log_tg_message(str(chat_id), "bot", answer)


async def _run_capture_async() -> None:
    """Fire-and-forget on-demand capture. Sends a Telegram summary when done."""
    from .jobs import tg_capture as cap
    run_id = uuid.uuid4().hex[:12]
    try:
        stats = await cap.run(run_id)
        log.info("tg_capture on-demand run=%s stats=%s", run_id, stats)
    except Exception as e:
        log.exception("tg_capture on-demand failed: %s", e)
        try:
            await tg.send(f"⚠️ Capture failed: {tg._esc(str(e)[:300])}")
        except Exception:
            pass


async def _run_council_async() -> None:
    """Fire-and-forget council run. council.run() already sends a Telegram
    summary via writer.notify() at the end, so we just need to surface errors.
    """
    from .jobs import council as cj
    run_id = uuid.uuid4().hex[:12]
    try:
        stats = await cj.run(run_id)
        log.info("council on-demand run=%s stats=%s", run_id, stats)
    except Exception as e:
        log.exception("council on-demand failed: %s", e)
        try:
            await tg.send(f"⚠️ Council failed: {tg._esc(str(e)[:400])}")
        except Exception:
            pass


def _render_basic_markdown_html(text: str) -> str:
    """Render a tiny subset of markdown safely for Telegram HTML:
    - **bold**
    Everything else is escaped.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        j = text.find("**", i)
        if j == -1:
            out.append(tg._esc(text[i:]))
            break
        k = text.find("**", j + 2)
        if k == -1:
            out.append(tg._esc(text[i:]))
            break
        out.append(tg._esc(text[i:j]))
        out.append(f"<b>{tg._esc(text[j + 2:k])}</b>")
        i = k + 2
    return "".join(out)


def _format_answer_for_telegram(answer: str, max_chars: int = 2800) -> str:
    """Normalize model output to clean Telegram-friendly HTML."""
    if not answer:
        return "(no response)"
    text = answer.replace("```", "").replace("\r\n", "\n").strip()
    lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
            lines.append(f"<b>{tg._esc(line)}</b>")
            continue
        if line.startswith("- ") or line.startswith("* "):
            line = f"• {line[2:].strip()}"
        lines.append(_render_basic_markdown_html(line))

    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


def _make_preview(content: str, max_chars: int = 110) -> str:
    """Build a short, human-readable snippet for citation footers."""
    if not content:
        return "(empty)"
    text = content
    if "<user_query>" in text and "</user_query>" in text:
        text = text.split("<user_query>", 1)[1].split("</user_query>", 1)[0]
    text = text.replace("\\n", " ").replace("\\t", " ").replace("```", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(
        r"\"?(type|content|text|role|messages|user_query|assistant_response|model)\"?\s*:\s*",
        " ",
        text,
        flags=re.I,
    )
    text = re.sub(r"[\{\}\[\]\"]", " ", text)
    text = " ".join(text.strip().split())
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return f"\"{text}\""


# ───────────────────────────────── main loop ──────────────────────────────────
async def run_forever() -> None:
    if not tg.BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set")
    log.info("sh-brain-tgbot starting; polling messages + callback_query")
    offset = _load_offset()
    async with httpx.AsyncClient() as client:
        while True:
            updates = await _poll_updates(client, offset)
            for u in updates:
                uid = u.get("update_id", 0)
                if uid >= offset:
                    offset = uid + 1
                cb = u.get("callback_query")
                if cb:
                    try:
                        await _handle_callback(cb)
                    except Exception as e:
                        log.exception("callback handler failed: %s", e)
                msg = u.get("message")
                if msg:
                    try:
                        await _handle_message(msg)
                    except Exception as e:
                        log.exception("message handler failed: %s", e)
                        try:
                            await tg.send(f"⚠️ Brain hit an error: {tg._esc(str(e)[:200])}")
                        except Exception:
                            pass
            if updates:
                _save_offset(offset)


def main() -> int:
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
