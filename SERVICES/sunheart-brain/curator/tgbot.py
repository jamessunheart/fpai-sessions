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
from . import james_ask
from .appflowy import AppFlowy
from .proposals import SAFE_AUTO_APPLY


async def _ask_send_wrapper(text: str):
    """Adapter for james_ask.send_pending: tg.send returns bool, return a
    minimal dict so message_id (None for now) fits the expected shape."""
    ok = await tg.send(text)
    return {"result": {"message_id": None}} if ok else None

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("curator.tgbot")


OFFSET_FILE = Path(os.environ.get("SH_TGBOT_OFFSET_FILE", "/var/lib/sh-brain/tgbot.offset"))
OWNER_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Team capture: comma-separated `chat_id:display_name` pairs · these humans can
# DM the bot to drop intents into Linear CAPTURED (river-only, no command access).
# Format: "12345:Atlas,67890:Cheyenne,11111:Halley"
_TEAM_RAW = os.environ.get("TEAM_CAPTURE_USERS", "")
TEAM_CAPTURE: dict[str, str] = {}
for _pair in _TEAM_RAW.split(","):
    _pair = _pair.strip()
    if ":" in _pair:
        _cid, _name = _pair.split(":", 1)
        TEAM_CAPTURE[_cid.strip()] = _name.strip()

def _is_team_capture_user(uid: str) -> bool:
    """Non-owner human authorized to drop captures (capture-only · no commands · no brain search)."""
    return bool(uid) and uid in TEAM_CAPTURE

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
            "  /now       — current priority + status from NOW.md (cross-terminal coordination)\n"
            "  /vision    — unifying vision: 30-day goal + ONE Thing + AI alignment\n"
            "  /goals [james|ai|team] — goals broken down by audience (founder · AI · team)\n"
            "  /projects  — projects ranked most→least important (from NOW.md)\n"
            "  /questions — open inquiries across qb books (fpai/game/sunheart)\n"
            "  /characters — Champions in the Game · roster + KPIs\n"
            "  /cohort NAME — per-Champion flow status for one cohort (e.g., zen-village)\n"
            "  /show-card NAME — view a Champion's Character Card content\n"
            "  /invite NAME [email|phone|@handle] [path] [cohort=ZV] — render invitation + deep link\n"
            "  /invites — your sent invitations with status (sent/clicked/signed)\n"
            "  /invite-types — list available invitation templates\n"
            "  /match [name] — one specific helpful next move (defaults to James)\n"
            "  /game      — vital Game stats for the architect\n"
            "  /signals   — trading + lead signals (retreat / party / coaching / commerce)\n"
            "  /decisions — unified queue of items needing your decision\n"
            "  /money     — costs + revenue + liquid + runway\n"
            "       /money liquid                                — liquid balances by account\n"
            "       /money trades                                — open trade positions + live P/L\n"
            "       /money trade close &lt;id&gt; [@ &lt;exit&gt;] [note]   — close a position (uses live mark if no price)\n"
            "       /money trade delete &lt;id&gt;                     — remove a trade record (typo-correction)\n"
            "       /money set &lt;id&gt; &lt;amount&gt; [purpose]    — update an existing cost line\n"
            "       /money set-balance &lt;account&gt; &lt;amt&gt;     — update an account balance\n"
            "       /money trade &lt;sym&gt; &lt;side&gt; &lt;qty&gt; @ &lt;price&gt; [note] — open a trade position\n"
            "       /money onebpo                                — OneBPO P&L + Cora Nation contribution\n"
            "       /money add cost &lt;id&gt; &lt;name&gt; &lt;amt&gt; &lt;cat&gt; — add new cost\n"
            "       /money add revenue &lt;stream&gt; &lt;amt&gt; [note] — add/update revenue\n"
            "       /money &lt;free text&gt;                       — capture as money note (queued)\n"
            "  /servers   — live server + hosting status (primary / brain / legacy)\n"
            "  /roi       — yesterday's brain ROI ledger (cost vs engagement)\n"
            "  /opportunities — run today's proactive scan now (silent if nothing)\n"
            "  /capabilities [category] — what this system can do (and when it shipped)\n"
            "  /voice [on|off]  — toggle voice replies (default ON · voice-in always replies in voice)\n"
            "  /more      — same as /signals more (expanded view: liquidity, costs, etc.)\n"
            "  /log       — recent AI activity timeline\n"
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
    if cmd == "questions":
        return await _cmd_questions()
    if cmd in ("characters", "champions"):
        return await _cmd_characters()
    if cmd == "invite":
        return await _cmd_invite(rest)
    if cmd == "invites":
        return await _cmd_invites()
    if cmd in ("invite-types", "invite_types", "invitetypes"):
        return await _cmd_invite_types()
    if cmd == "cohort":
        return await _cmd_cohort(rest)
    if cmd in ("show-card", "showcard", "card"):
        return await _cmd_show_card(rest)
    if cmd == "match":
        return await _cmd_match(rest)
    if cmd == "game":
        return await _cmd_game()
    if cmd == "now":
        return await _cmd_now()
    if cmd == "goals":
        return await _cmd_goals(rest)
    if cmd == "vision":
        return await _cmd_vision()
    if cmd == "signals":
        return await _cmd_signals(rest.strip().lower())
    if cmd == "more":
        return await _cmd_signals("more")
    if cmd == "decisions":
        return await _cmd_decisions()
    if cmd == "money":
        return await _cmd_money(rest)
    if cmd == "log":
        return await _cmd_log()
    if cmd == "servers":
        return await _cmd_servers()
    if cmd == "roi":
        return await _cmd_roi()
    if cmd == "opportunities":
        await tg.send("⏳ Running opportunities scan…")
        asyncio.create_task(_run_opportunities_async())
        return None
    if cmd == "capabilities":
        return await _cmd_capabilities(rest.strip())
    if cmd == "voice":
        return _cmd_voice(rest.strip().lower())
    return f"Unknown command: /{tg._esc(cmd)}. Try /help."


def _cmd_voice(arg: str) -> str:
    """Runtime toggle for voice-out replies.

    /voice          → show status
    /voice on       → enable (remove lockfile)
    /voice off      → disable (create lockfile)
    /voice test     → return a small text reply that will get TTS'd back if
                      issued from a voice message (the caller controls TTS
                      dispatch; this just confirms the path is alive)
    """
    if arg in ("on", "enable", "enabled"):
        try:
            if _VOICE_DISABLE_LOCK.exists():
                _VOICE_DISABLE_LOCK.unlink()
            return ("🔊 <b>Voice replies: ON</b>\n"
                    f"Voice messages will be answered with voice + text.\n"
                    f"Model: <code>{tg._esc(_TTS_MODEL)}</code> · "
                    f"Voice: <code>{tg._esc(_TTS_VOICE)}</code> · "
                    f"Format: <code>{tg._esc(_TTS_FORMAT)}</code>")
        except Exception as e:
            return f"⚠️ Could not enable voice: {tg._esc(str(e))}"
    if arg in ("off", "disable", "disabled", "mute"):
        try:
            _VOICE_DISABLE_LOCK.parent.mkdir(parents=True, exist_ok=True)
            _VOICE_DISABLE_LOCK.write_text(
                datetime.now(timezone.utc).isoformat() + "\n"
            )
            return ("🔇 <b>Voice replies: OFF</b>\n"
                    "Voice messages will still be transcribed, but the bot will "
                    "reply with text only. Re-enable with <code>/voice on</code>.")
        except Exception as e:
            return f"⚠️ Could not disable voice: {tg._esc(str(e))}"
    # status / default
    enabled = _voice_out_enabled()
    state = "🔊 ON" if enabled else "🔇 OFF"
    why = ""
    if not enabled:
        if os.environ.get("EMBER_TGBOT_VOICE_DISABLE", "").strip() in ("1", "true", "yes"):
            why = " <i>(env EMBER_TGBOT_VOICE_DISABLE)</i>"
        elif _VOICE_DISABLE_LOCK.exists():
            why = f" <i>(lockfile {tg._esc(str(_VOICE_DISABLE_LOCK))})</i>"
    return (
        f"🎙️ <b>Voice status:</b> {state}{why}\n"
        f"Model: <code>{tg._esc(_TTS_MODEL)}</code> · "
        f"Voice: <code>{tg._esc(_TTS_VOICE)}</code> · "
        f"Max chars: <code>{_TTS_MAX_CHARS}</code> · "
        f"Format: <code>{tg._esc(_TTS_FORMAT)}</code>\n"
        "Toggle: <code>/voice on</code> · <code>/voice off</code>\n"
        "<i>Voice replies fire only when the inbound message was voice.</i>"
    )


# ---------- shared state-file paths (synced from laptop) ----------
import os as _os
_STATE_DIR = _os.environ.get("FPAI_STATE_DIR", "/var/lib/sh-brain/state")
_NOW_PATH = _os.path.join(_STATE_DIR, "NOW.md")
_AI_GOALS_PATH = _os.path.join(_STATE_DIR, "AI_GOALS.md")
_QB_BOARD_PATH = _os.path.join(_STATE_DIR, "qb-board.jsonl")
_DEFAULT_TEAM_COHORT = _os.environ.get("DEFAULT_TEAM_COHORT", "zen-village")


async def _cmd_projects() -> str:
    """Render ranked projects from NOW.md → '## 📊 PROJECT RANKING' section.

    NOW.md is the SSOT for priority ordering (synced from the cockpit repo).
    If NOW.md is unreachable, fall back to the live Sessions API.
    """
    try:
        with open(_NOW_PATH, encoding="utf-8") as f:
            now_md = f.read()
    except Exception as e:
        return await _cmd_projects_fallback_sessions(error=str(e))

    rows = _parse_project_ranking(now_md)
    if not rows:
        return await _cmd_projects_fallback_sessions(
            error=f"PROJECT RANKING section not found in NOW.md ({_NOW_PATH})."
        )

    import os as _os2
    mtime_age = ""
    try:
        age_s = int(_os2.path.getmtime(_NOW_PATH))
        from datetime import datetime as _dt
        diff = (_dt.now() - _dt.fromtimestamp(age_s)).total_seconds()
        if diff < 3600: mtime_age = f"{int(diff//60)}m ago"
        elif diff < 86400: mtime_age = f"{int(diff//3600)}h ago"
        else: mtime_age = f"{int(diff//86400)}d ago"
    except Exception:
        pass

    DEFAULT_TOP = 5
    lines = ["📊 <b>Projects — most-important first</b>"]
    if mtime_age:
        lines.append(f"<i>NOW.md synced {mtime_age}</i>\n")
    for r in rows[:DEFAULT_TOP]:
        lines.append(
            f"\n<b>#{r['rank']}</b> {tg._esc(r['name'])}"
        )
        if r.get("status"):
            lines.append(f"  {tg._esc(r['status'])}")
        if r.get("why"):
            lines.append(f"  <i>{tg._esc(r['why'])}</i>")
    if len(rows) > DEFAULT_TOP:
        collapsed = ", ".join(f"#{r['rank']} {r['name'].split('—')[0].strip()}" for r in rows[DEFAULT_TOP:])
        lines.append(f"\n<i>Lower-priority: {tg._esc(collapsed)}</i>")
    lines.append("\n<i>Source: core/STATE/NOW.md · /questions for live inquiries</i>")
    return "\n".join(lines)


def _parse_project_ranking(md: str) -> list[dict]:
    """Parse the PROJECT RANKING markdown table.

    Looks for a heading containing 'PROJECT RANKING' and a markdown table with
    columns: # | Project | Why this rank | Status. Returns list of dicts:
    {rank, name, why, status}.
    """
    import re
    section_re = re.compile(r"##\s+.*PROJECT\s+RANKING.*$", re.MULTILINE | re.IGNORECASE)
    m = section_re.search(md)
    if not m:
        return []
    body = md[m.end():]
    # Stop at next ## heading
    next_h = re.search(r"^\n##\s", body, re.MULTILINE)
    if next_h:
        body = body[: next_h.start()]
    rows: list[dict] = []
    row_re = re.compile(r"^\|\s*(\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|\s*$", re.MULTILINE)
    for rm in row_re.finditer(body):
        rank = int(rm.group(1))
        name = _strip_md(rm.group(2))
        why = _strip_md(rm.group(3))
        status = _strip_md(rm.group(4))
        rows.append({"rank": rank, "name": name, "why": why, "status": status})
    rows.sort(key=lambda r: r["rank"])
    return rows


def _strip_md(s: str) -> str:
    """Strip basic markdown emphasis from a table cell."""
    import re
    s = s.strip()
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    s = re.sub(r"\[(.+?)\]\([^)]+\)", r"\1", s)
    return s.strip()


async def _cmd_projects_fallback_sessions(error: str = "") -> str:
    """Legacy /projects: live Claude session state from the Sessions API."""
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
        prefix = f"📡 <b>Projects</b>\n\n<i>NOW.md ranking unavailable: {tg._esc(error)}</i>\n" if error else "📡 <b>Projects</b>\n\n"
        return f"{prefix}Could not reach the sessions API either: {tg._esc(str(e))}"
    sessions = data.get("sessions", [])
    glyphs = {"active": "🟢", "paused": "⏸", "blocked": "🛑", "complete": "✓"}
    lines = ["📡 <b>Projects — live session state</b>"]
    if error:
        lines.append(f"<i>NOW.md ranking unavailable: {tg._esc(error)}</i>")
    lines.append("")
    if not sessions:
        lines.append("<i>No active sessions tracked yet.</i>")
        return "\n".join(lines)
    for s in sessions[:10]:
        glyph = glyphs.get((s.get("status") or "").lower(), "•")
        project = tg._esc(s.get("project", "?"))
        loop = s.get("loop_number")
        loop_str = f" · Loop {loop}" if loop is not None else ""
        lines.append(f"\n{glyph} <b>{project}</b>{loop_str}")
        if s.get("quest"):
            lines.append(f"  Quest: {tg._esc(s['quest'])}")
        if s.get("next_move"):
            lines.append(f"  Next: <i>{tg._esc(s['next_move'])}</i>")
    return "\n".join(lines)


async def _cmd_questions() -> str:
    """Show active inquiries across qb books, reduced from synced board.jsonl."""
    try:
        with open(_QB_BOARD_PATH, encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        return (
            "❓ <b>Questions</b>\n\n"
            f"qb board unavailable at <code>{tg._esc(_QB_BOARD_PATH)}</code>: {tg._esc(str(e))}\n\n"
            "Run <code>sync_qb_to_brain.sh</code> from the laptop."
        )

    import json as _json
    events: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(_json.loads(line))
        except Exception:
            continue

    state = _qb_derive_state(events)
    if not state:
        return "❓ <b>Questions</b>\n\n<i>No qb events on file yet.</i>"

    by_book: dict[str, list[dict]] = {}
    for q in state.values():
        by_book.setdefault(q.get("book") or "fpai", []).append(q)

    # Display order: P1 books first. Game (Champion enrollment / retreat funnel)
    # outranks fpai (substrate). Sunheart (personal) sits between.
    book_order = ["game", "sunheart", "fpai"]
    extras = sorted(b for b in by_book.keys() if b not in book_order)
    ordered = [b for b in book_order if b in by_book] + extras

    from datetime import datetime as _dtq, timezone as _tzq
    now = _dtq.now(_tzq.utc)

    def _is_goal(q: dict) -> bool:
        text = (q.get("text") or "").strip().upper()
        return text.startswith("GOAL:") or text.startswith("🎯") or text.startswith("⭐")

    def _rel_age(ts_str: str) -> str:
        try:
            ts = _dtq.fromisoformat(ts_str.replace("Z", "+00:00"))
            secs = (now - ts).total_seconds()
        except Exception:
            return ""
        if secs < 60: return "just now"
        if secs < 3600: return f"{int(secs//60)}m ago"
        if secs < 86400: return f"{int(secs//3600)}h ago"
        if secs < 86400*7: return f"{int(secs//86400)}d ago"
        if secs < 86400*30: return f"{int(secs//(86400*7))}w ago"
        return f"{int(secs//(86400*30))}mo ago"

    def _stale(q: dict) -> bool:
        try:
            ts = _dtq.fromisoformat(q["updated_at"].replace("Z", "+00:00"))
            return (now - ts).total_seconds() > 86400 * 7
        except Exception:
            return False

    def _show_pulse(q: dict) -> str | None:
        """Show last pulse only if recent (<24h) AND substantive. Returns rendered line or None."""
        prog = q.get("progress") or []
        if not prog:
            return None
        last = prog[-1]
        note = (last.get("note") or "").strip()
        if not note:
            return None
        try:
            ts = _dtq.fromisoformat(last.get("ts", "").replace("Z", "+00:00"))
            secs = (now - ts).total_seconds()
            if secs > 86400:  # older than 24h — drop it
                return None
        except Exception:
            return None
        # Filter "shipped X" status pulses — they're noise on /questions (use /log for those)
        low = note.lower()
        if any(low.startswith(p) for p in ("shipped", "deployed", "committed", "✅", "/", "verified")):
            return None
        age = _rel_age(last.get("ts", ""))
        return f"     ↳ <i>{age}: {tg._esc(_qb_short(note, 180))}</i>"

    lines = ["❓ <b>Open inquiries — qb across books</b>\n"]
    any_active = False

    for book in ordered:
        qs = by_book[book]
        active_all = [q for q in qs if q["status"] == "active"]
        blocked = [q for q in qs if q["status"] == "blocked"]
        if not active_all and not blocked:
            continue
        any_active = True

        # Sort: goals first, then by most-recently-updated.
        goals = sorted([q for q in active_all if _is_goal(q)],
                        key=lambda q: q["updated_at"], reverse=True)
        non_goals = sorted([q for q in active_all if not _is_goal(q)],
                            key=lambda q: q["updated_at"], reverse=True)
        active = goals + non_goals

        lines.append(f"\n<b>📖 {tg._esc(book)}</b> <i>({len(active)} active{f', {len(blocked)} blocked' if blocked else ''})</i>")
        for q in active[:6]:
            icon = "🎯" if _is_goal(q) else "❓"
            text = q["text"]
            # Strip "GOAL:" prefix in display since icon carries the meaning
            if _is_goal(q) and text.upper().startswith("GOAL:"):
                text = text[5:].strip()
            stale_tag = " <i>[stale]</i>" if _stale(q) else ""
            age = _rel_age(q["updated_at"])
            lines.append(f"  {icon} {tg._esc(_qb_short(text, 200))}{stale_tag}")
            pulse_line = _show_pulse(q)
            if pulse_line:
                lines.append(pulse_line)
            elif age and not stale_tag:
                # Show age only if we didn't show a pulse
                pass  # keep output tight; age shown via pulse line otherwise

        for q in blocked[:3]:
            lines.append(f"  ⊗ {tg._esc(_qb_short(q['text'], 200))}")
            if q.get("block_reason"):
                lines.append(f"     ⊗ <i>{tg._esc(_qb_short(q['block_reason'], 160))}</i>")

    if not any_active:
        lines.append("<i>No open questions across any book. Clean board.</i>")

    lines.append("\n<i>Legend: 🎯 goal · ❓ question · ⊗ blocked · pulse shown only if &lt;24h and substantive</i>")
    lines.append("<i>Source: qb-board.jsonl · use `qb` on laptop to manage</i>")
    return "\n".join(lines)


def _qb_derive_state(events: list[dict]) -> dict[str, dict]:
    """Reduce qb events → per-question current state. Mirrors qb's own logic."""
    state: dict[str, dict] = {}
    for ev in events:
        qid = ev.get("qid")
        if not qid:
            continue
        s = state.setdefault(qid, {
            "qid": qid,
            "text": "",
            "status": "open",
            "book": ev.get("book") or "fpai",
            "owner": None,
            "updated_at": ev.get("ts", ""),
            "progress": [],
            "block_reason": None,
            "answer": None,
        })
        s["updated_at"] = ev.get("ts", s["updated_at"])
        if ev.get("book"):
            s["book"] = ev["book"]
        kind = ev.get("event")
        if kind == "open":
            s["text"] = ev.get("text", s["text"])
            s["status"] = "active"
        elif kind == "supersede":
            s["text"] = ev.get("text", s["text"])
            s["status"] = "active"
        elif kind == "take":
            s["status"] = "active"
        elif kind == "pulse":
            note = ev.get("note", "")
            if note:
                s["progress"].append({"ts": ev.get("ts", ""), "note": note})
            if s["status"] == "blocked":
                s["status"] = "active"
            s["block_reason"] = None
        elif kind == "block":
            s["status"] = "blocked"
            s["block_reason"] = ev.get("note", "")
        elif kind == "unblock":
            s["status"] = "active"
            s["block_reason"] = None
        elif kind == "answer":
            s["status"] = "answered"
            s["answer"] = ev.get("note") or ev.get("text") or ""
        elif kind == "rebook":
            new_book = ev.get("note") or ev.get("book")
            if new_book:
                s["book"] = new_book
    return state


def _qb_short(text: str, n: int) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= n:
        return text
    return text[: n - 1] + "…"


# ───────────────────────────── /invite + /invites ──────────────────────────────
_INVITE_TEMPLATES_PATH = _os.path.join(_STATE_DIR, "INVITE_TEMPLATES.md")
_INVITES_LOG_PATH = _os.path.join(_STATE_DIR, "invites.jsonl")
_INVITER_NAME = _os.environ.get("INVITER_NAME", "James Sunheart")
_INVITE_BASE_URL = _os.environ.get("INVITE_BASE_URL", "https://fullpotential.com/game/")
_GAME_BOT_USERNAME = _os.environ.get("GAME_BOT_USERNAME", "fullpotentialgamebot")
_DEFAULT_PATH = "game"

# Detection regexes (deliberately permissive — friction-min, not validation)
import re as _re_inv
_RE_EMAIL = _re_inv.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.\-]+$")
_RE_TG_HANDLE = _re_inv.compile(r"^@[A-Za-z0-9_]{3,}$")
_RE_PHONE = _re_inv.compile(r"^\+?[\d][\d\s().\-]{6,}$")


def _parse_invite_args(rest: str, available_paths: set[str]) -> dict:
    """Parse `/invite NAME [contact] [path] [why_them...]` polymorphically.

    Strategy: tokenize by whitespace, classify each token as email / phone /
    tg-handle / known-path / name-fragment. First name-fragment(s) collapse
    into NAME. Remaining name-fragments after the contact/path become
    {WHY_THEM}. All fields optional except NAME.
    """
    tokens = [t for t in rest.strip().split() if t]
    out = {"name": "", "contact": "", "channel": "", "path": "",
           "cohort": "", "why_them": "", "raw": rest.strip()}
    name_parts: list[str] = []
    why_parts: list[str] = []
    contact_seen = False
    path_seen = False
    for tok in tokens:
        # Explicit `cohort=zen-village` (or `c=zen-village`) syntax
        low = tok.lower()
        if low.startswith("cohort=") or low.startswith("c="):
            out["cohort"] = tok.split("=", 1)[1].strip().lower()
            continue
        if not contact_seen and _RE_EMAIL.match(tok):
            out["contact"] = tok
            out["channel"] = "email"
            contact_seen = True
            continue
        if not contact_seen and _RE_TG_HANDLE.match(tok):
            out["contact"] = tok
            out["channel"] = "telegram"
            contact_seen = True
            continue
        if not contact_seen and _RE_PHONE.match(tok):
            out["contact"] = tok
            out["channel"] = "whatsapp"
            contact_seen = True
            continue
        tok_lower = tok.lower()
        if not path_seen and tok_lower in available_paths:
            out["path"] = tok_lower
            path_seen = True
            continue
        # Otherwise: name fragment (before contact) or why-them (after)
        if not contact_seen and not path_seen:
            name_parts.append(tok)
        else:
            why_parts.append(tok)
    out["name"] = " ".join(name_parts).strip()
    out["why_them"] = " ".join(why_parts).strip()
    if not out["path"]:
        out["path"] = _DEFAULT_PATH
    return out


def _load_invite_templates() -> dict[str, str]:
    """Parse INVITE_TEMPLATES.md → {path_slug: body}. Each `## slug` heading
    starts a template; body runs until the next `## ` or `---` divider."""
    try:
        with open(_INVITE_TEMPLATES_PATH, encoding="utf-8") as f:
            md = f.read()
    except Exception:
        return {}
    templates: dict[str, str] = {}
    current_slug = None
    current_body: list[str] = []
    for line in md.splitlines():
        m = _re_inv.match(r"^##\s+([A-Za-z][A-Za-z0-9\-_]*)\s*$", line)
        if m:
            if current_slug and current_body:
                templates[current_slug] = "\n".join(current_body).strip()
            current_slug = m.group(1).lower()
            current_body = []
            continue
        if line.strip() == "---" and current_slug:
            templates[current_slug] = "\n".join(current_body).strip()
            current_slug = None
            current_body = []
            continue
        if current_slug:
            current_body.append(line)
    if current_slug and current_body:
        templates[current_slug] = "\n".join(current_body).strip()
    return templates


def _render_template(body: str, name: str, why_them: str, link: str) -> str:
    """Substitute {NAME}, {WHY_THEM}, {TRACKED_LINK}. Empty WHY_THEM → blank line."""
    first_name = (name.split()[0] if name else "there")
    out = body.replace("{NAME}", first_name)
    if why_them:
        out = out.replace("{WHY_THEM}", why_them)
    else:
        out = _re_inv.sub(r"\n*\{WHY_THEM\}\n*", "\n", out)
    out = out.replace("{TRACKED_LINK}", link)
    return out.strip()


def _build_tracked_link(path: str, cohort: str = "") -> str:
    """Tracked Telegram deep-link to @fullpotentialgamebot.

    Payload format: invite_n_<INVITER>_p_<PATH>_c_<COHORT> — markers all
    optional after `invite_`. Recipients land in the Game-bot, /sign in TG.
    """
    from urllib.parse import quote as _quote
    inviter_slug = _INVITER_NAME.replace(" ", "_")
    parts = [f"invite_n_{inviter_slug}"]
    if path and path != _DEFAULT_PATH:
        parts.append(f"p_{path}")
    if cohort:
        parts.append(f"c_{cohort}")
    payload = "_".join(parts)
    return f"https://t.me/{_GAME_BOT_USERNAME}?start={_quote(payload)}"


def _build_tracked_link_legacy_web(path: str) -> str:
    """Web fallback URL — kept for cases where TG deep-link won't work
    (recipient firmly resists installing Telegram). Returns the website
    URL with inviter attribution that champion-sign reads on sign."""
    from urllib.parse import quote as _quote
    inviter_enc = _quote(_INVITER_NAME)
    base = _INVITE_BASE_URL.rstrip("/") + "/"
    if path and path != _DEFAULT_PATH:
        return f"{base}?inviter={inviter_enc}&path={_quote(path)}"
    return f"{base}?inviter={inviter_enc}"


def _build_deep_links(channel: str, contact: str, rendered_text: str) -> list[tuple[str, str]]:
    """Return list of (label, url) for whatever channel the contact maps to."""
    from urllib.parse import quote as _quote
    out: list[tuple[str, str]] = []
    if channel == "email":
        subject = "Invitation to Full Potential — from James"
        out.append(("📧 Open in Mail",
                    f"mailto:{contact}?subject={_quote(subject)}&body={_quote(rendered_text)}"))
    elif channel == "whatsapp":
        digits = "".join(c for c in contact if c.isdigit() or c == "+")
        wa_phone = digits.lstrip("+")  # wa.me wants no leading +
        out.append(("💬 Open in WhatsApp",
                    f"https://wa.me/{wa_phone}?text={_quote(rendered_text)}"))
        out.append(("📱 SMS fallback",
                    f"sms:{digits}&body={_quote(rendered_text)}"))
    elif channel == "telegram":
        out.append(("✈️ Forward in Telegram",
                    f"https://t.me/{contact.lstrip('@')}"))
    return out


def _log_invite(name: str, contact: str, channel: str, path: str,
                link: str, why_them: str = "", cohort: str = "") -> None:
    """Append the invite to the immutable log."""
    import json as _json
    from datetime import datetime as _dt
    row = {
        "ts": _dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inviter": _INVITER_NAME,
        "name": name,
        "contact": contact,
        "channel": channel or "copy-paste",
        "path": path,
        "cohort": cohort,
        "link": link,
        "why_them": why_them,
        "status": "sent",
    }
    try:
        _os.makedirs(_STATE_DIR, exist_ok=True)
        with open(_INVITES_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(_json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        log.warning("invite log write failed: %s", e)


async def _cmd_invite(rest: str) -> str:
    """`/invite NAME [contact] [path] [why_them...]`

    Friction-min: detects email / phone / @handle / name from any token order.
    Always renders copy-paste-ready text + tracked link. Adds appropriate
    deep link for the detected channel (mailto: / wa.me / TG forward).
    """
    templates = _load_invite_templates()
    if not templates:
        return (
            "📨 <b>Invite</b>\n\n"
            f"Templates not loaded from <code>{tg._esc(_INVITE_TEMPLATES_PATH)}</code>.\n"
            "Run <code>sync_now_to_brain.sh</code> from the laptop "
            "(it auto-syncs INVITE_TEMPLATES.md alongside NOW.md)."
        )
    available = set(templates.keys())
    args = _parse_invite_args(rest, available)
    if not args["name"]:
        path_list = ", ".join(sorted(available))
        return (
            "📨 <b>/invite</b> — render an invitation\n\n"
            "<b>Usage:</b>\n"
            "<code>/invite NAME [email|phone|@handle] [path] [why-them...]</code>\n\n"
            "Anything you don't pass is skipped. Examples:\n"
            "<code>/invite Mark</code> — copy-paste text only\n"
            "<code>/invite Mark mark@example.com</code> — opens Mail\n"
            "<code>/invite Mark +15551234567 retreat</code> — opens WhatsApp\n"
            "<code>/invite Mark @markhandle apprenticeship</code> — TG forward link\n\n"
            f"<b>Available paths:</b> {tg._esc(path_list)}\n"
            "Default path: <b>game</b>"
        )
    if args["path"] not in templates:
        path_list = ", ".join(sorted(available))
        return (f"📨 Unknown path: <code>{tg._esc(args['path'])}</code>\n"
                f"Available: {tg._esc(path_list)}")

    body = templates[args["path"]]
    link = _build_tracked_link(args["path"], args.get("cohort", ""))
    rendered = _render_template(body, args["name"], args["why_them"], link)
    _log_invite(args["name"], args["contact"], args["channel"], args["path"],
                link, args["why_them"], args.get("cohort", ""))

    deep_links = _build_deep_links(args["channel"], args["contact"], rendered)

    cohort_part = f" · cohort: <i>{tg._esc(args['cohort'])}</i>" if args.get("cohort") else ""
    lines = [
        f"📨 <b>Invitation drafted</b> — <i>{tg._esc(args['path'])}</i> path · {tg._esc(args['name'])}{cohort_part}",
    ]
    if args["channel"]:
        lines.append(f"<i>Channel: {tg._esc(args['channel'])} → {tg._esc(args['contact'])}</i>")
    else:
        lines.append("<i>No channel — copy-paste only</i>")
    lines.append("")
    lines.append("<pre>" + tg._esc(rendered) + "</pre>")
    if deep_links:
        lines.append("")
        for label, url in deep_links:
            lines.append(f'<a href="{tg._esc(url)}">{tg._esc(label)}</a>')
    lines.append("")
    lines.append(f"<i>Logged to invites.jsonl · /invites for status</i>")
    return "\n".join(lines)


async def _cmd_invites() -> str:
    """List sent invites with status enriched from /api/champion/list."""
    import json as _json
    rows: list[dict] = []
    try:
        with open(_INVITES_LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(_json.loads(line))
                except Exception:
                    continue
    except FileNotFoundError:
        return "📨 <b>Invites</b>\n\n<i>No invites sent yet. Try <code>/invite NAME</code>.</i>"
    except Exception as e:
        return f"📨 <b>Invites</b>\n\n⚠️ log read failed: {tg._esc(str(e))}"

    if not rows:
        return "📨 <b>Invites</b>\n\n<i>Log empty. Try <code>/invite NAME</code>.</i>"

    # Pull current Champion roster for status enrichment
    signed_names: set[str] = set()
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=4.0) as c:
            r = await c.get(f"{_FPAI_BASE.rstrip('/')}/api/champion/list")
            if r.status_code == 200:
                data = r.json()
                for ch in data.get("champions", []) if isinstance(data, dict) else data:
                    nm = (ch.get("name") or "").strip().lower()
                    if nm:
                        signed_names.add(nm)
    except Exception:
        pass  # status enrichment is best-effort

    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    lines = [f"📨 <b>Invites — {len(rows)} sent</b>\n"]
    for r in rows[:15]:
        name = r.get("name", "?")
        signed = name.strip().lower() in signed_names
        glyph = "✓ signed" if signed else "· sent"
        path = r.get("path", "game")
        ch_part = f" · {r.get('channel')}" if r.get("channel") else ""
        coh_part = f" · 👥{r.get('cohort')}" if r.get("cohort") else ""
        ts = (r.get("ts") or "")[:10]  # date only
        lines.append(f"  <b>{tg._esc(name)}</b> · {tg._esc(path)}{tg._esc(ch_part)}{tg._esc(coh_part)} · {tg._esc(ts)} · {glyph}")
    if len(rows) > 15:
        lines.append(f"\n<i>… and {len(rows) - 15} older.</i>")
    n_signed = sum(1 for r in rows if r.get("name", "").strip().lower() in signed_names)
    lines.append(f"\n<i>{n_signed}/{len(rows)} signed</i>")
    return "\n".join(lines)


async def _cmd_invite_types() -> str:
    """List the available invitation paths from INVITE_TEMPLATES.md."""
    templates = _load_invite_templates()
    if not templates:
        return (
            "📨 <b>Invite types</b>\n\n"
            f"Templates not loaded from <code>{tg._esc(_INVITE_TEMPLATES_PATH)}</code>."
        )
    lines = ["📨 <b>Invite types</b> — pass any of these as the path arg\n"]
    for slug in sorted(templates.keys()):
        body = templates[slug]
        # First substantive content line — skip greeting (`{NAME} —`),
        # blanks, the {WHY_THEM} placeholder, and the signoff (`— James`).
        summary = ""
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("{") and line.endswith("}"):
                continue
            if line.startswith("—"):  # signoff
                continue
            if line.endswith("—"):  # greeting line ends with em-dash
                continue
            if len(line) < 25:  # too short to be a real sentence
                continue
            summary = line
            break
        marker = " ⭐" if slug == _DEFAULT_PATH else ""
        lines.append(f"  <b>{tg._esc(slug)}</b>{marker} — <i>{tg._esc(summary[:110])}</i>")
    lines.append(f"\n<i>Edit <code>core/STATE/INVITE_TEMPLATES.md</code> to add/tune; "
                 "sync_now_to_brain.sh syncs them to the brain server.</i>")
    return "\n".join(lines)


# ───────────────────────────── /characters ──────────────────────────────
_FPAI_BASE = _os.environ.get("FPAI_BASE_URL", "https://fullpotential.com")


async def _cmd_characters() -> str:
    """Show enrolled Champions + latest Game KPIs.

    Sources:
      - GET /api/champion/list          → roster
      - GET /api/champion/leaderboard   → field-score + affiliate ranking
      - GET /api/champion/retreat/list  → retreat-interest count
    Each call is best-effort; missing data degrades the section, not the reply.
    """
    import httpx as _httpx
    headers = {"Accept": "application/json"}
    async def _fetch(path: str) -> dict | None:
        url = f"{_FPAI_BASE.rstrip('/')}{path}"
        try:
            async with _httpx.AsyncClient(timeout=6.0) as c:
                r = await c.get(url, headers=headers)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.warning("/characters fetch %s failed: %s", path, e)
            return None

    listing, board, retreats = await asyncio.gather(
        _fetch("/api/champion/list"),
        _fetch("/api/champion/leaderboard"),
        _fetch("/api/champion/retreat/list"),
    )

    if not listing and not board:
        return ("🎴 <b>Characters</b>\n\n"
                f"<i>Could not reach Champion APIs at {tg._esc(_FPAI_BASE)}.</i>")

    champions = (listing or {}).get("champions", []) if listing else []
    total = (listing or {}).get("count", len(champions)) if listing else 0
    top_champs = (board or {}).get("top_champions", []) if board else []
    top_affs = (board or {}).get("top_affiliates", []) if board else []
    top_loops = (board or {}).get("top_loops", []) if board else []
    interest_count = (retreats or {}).get("count", 0) if retreats else 0

    total_proofs = sum(int(c.get("proofs", 0) or 0) for c in top_champs)
    total_affiliates = sum(int(c.get("affiliates", 0) or 0) for c in top_champs)
    cards_filled = sum(1 for c in top_champs if c.get("card"))

    lines = [f"🎴 <b>Characters in the Game</b> — {total} Champion{'s' if total != 1 else ''}\n"]

    # KPI strip
    kpis = [
        f"⚡ Field proofs: <b>{total_proofs}</b>",
        f"🤝 Affiliates: <b>{total_affiliates}</b>",
        f"📇 Cards filled: <b>{cards_filled}/{total}</b>",
        f"🏝 Retreat interest: <b>{interest_count}</b>",
    ]
    lines.append(" · ".join(kpis))

    # Top champions by Field Score
    if top_champs:
        lines.append("\n<b>Top Champions by Field Score</b>")
        for c in top_champs[:8]:
            name = tg._esc(c.get("name") or "?")
            num = c.get("champion_number") or "—"
            fs = c.get("field_score", 0)
            proofs = c.get("proofs", 0)
            affs = c.get("affiliates", 0)
            card = "🎴" if c.get("card") else "—"
            lines.append(f"  #{num} <b>{name}</b> · score {fs} · {proofs} proofs · {affs} affiliates · card {card}")

    # Top affiliates (people who invited the most)
    if top_affs:
        lines.append("\n<b>Top Affiliates (most invites)</b>")
        for a in top_affs[:5]:
            name = tg._esc(a.get("name") or a.get("inviter") or "?")
            count = a.get("affiliate_count") or a.get("count") or 0
            lines.append(f"  ↗ <b>{name}</b> · {count} invited")
    else:
        lines.append("\n<i>No affiliates yet — share your invite link to start the network.</i>")

    # Loop activity
    if top_loops:
        recent_loops = sorted(top_loops, key=lambda l: l.get("loop_number") or 0, reverse=True)[:5]
        loop_strs = [f"L{l.get('loop_number')}({l.get('proof_count', 0)})" for l in recent_loops]
        lines.append(f"\n<b>Recent Loops</b>: {' · '.join(loop_strs)}")

    # Roster (compact, only if list endpoint returned)
    if champions:
        lines.append("\n<b>Roster</b>")
        for c in champions[:10]:
            name = tg._esc(c.get("name") or "?")
            handle = c.get("handle") or ""
            handle_str = f" <i>{tg._esc(handle)}</i>" if handle else ""
            num = c.get("champion_number") or "—"
            role = tg._esc((c.get("role") or "")[:60])
            lines.append(f"  #{num} {name}{handle_str}{f' · {role}' if role else ''}")
        if len(champions) > 10:
            lines.append(f"  <i>…+{len(champions) - 10} more</i>")

    lines.append("\n<i>Source: fullpotential.com/api/champion · invite link: fullpotential.com/game?inviter=YOUR-HANDLE</i>")
    return "\n".join(lines)


# ───────────────────────────── /match ──────────────────────────────
async def _cmd_cohort(rest: str) -> str:
    """Organizer view of a cohort — per-Champion flow status.

    Usage: /cohort zen-village
    Hits champion-sign /cohort/{name} which returns enriched per-Champion
    data (signed ✓, card status, # proofs, # affiliates, field_score).
    """
    cohort_name = rest.strip().lower()
    if not cohort_name:
        return ("👥 <b>/cohort COHORT_NAME</b>\n\n"
                "Show per-Champion flow status for one cohort. Example:\n"
                "<code>/cohort zen-village</code>\n\n"
                "Tag a Champion with cohort by adding <code>cohort=NAME</code> "
                "to <code>/invite</code> (e.g., <code>/invite Mark mark@x.com retreat cohort=zen-village</code>).")

    import httpx as _httpx
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"{_FPAI_BASE.rstrip('/')}/api/champion/cohort/{cohort_name}")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"👥 <b>Cohort: {tg._esc(cohort_name)}</b>\n\nAPI unreachable: {tg._esc(str(e))}"

    members = data.get("members", [])
    if not members:
        return (f"👥 <b>Cohort: {tg._esc(cohort_name)}</b>\n\n"
                f"<i>No Champions tagged with this cohort yet.</i>\n\n"
                f"Invite someone with <code>/invite NAME contact path cohort={tg._esc(cohort_name)}</code> "
                f"to start the cohort.")

    lines = [f"👥 <b>Cohort: {tg._esc(cohort_name)}</b> · {len(members)} members\n"]
    # Aggregate header
    n_card = sum(1 for m in members if m.get("card"))
    n_proofs = sum(m.get("proofs", 0) for m in members)
    n_affs = sum(m.get("affiliates", 0) for m in members)
    lines.append(f"<i>Aggregate: {n_card}/{len(members)} cards · "
                 f"{n_proofs} proofs · {n_affs} affiliates</i>\n")

    for m in members[:25]:
        nm = m.get("name") or "?"
        cn = m.get("champion_number") or "?"
        card_glyph = "📇" if m.get("card") else "·  "
        card_part = f" {card_glyph}" + (f" {tg._esc(m.get('card_level') or '')}" if m.get("card") else "")
        proofs = m.get("proofs", 0)
        affs = m.get("affiliates", 0)
        score = m.get("field_score", 0)
        flow_bits = []
        if proofs: flow_bits.append(f"{proofs}🌀")
        if affs: flow_bits.append(f"{affs}🤝")
        flow_str = " · ".join(flow_bits) if flow_bits else "no proofs/affs yet"
        lines.append(f"  <b>#{cn} {tg._esc(nm)}</b>{card_part} · FS {score} · {tg._esc(flow_str)}")
        for g in (m.get("active_goals") or [])[:3]:
            gtext = g.get("goal", "")
            if gtext:
                lines.append(f"     🎯 <i>{tg._esc(gtext[:80])}</i>")

    if len(members) > 25:
        lines.append(f"\n<i>… and {len(members) - 25} more.</i>")
    lines.append(f"\n<i>📇 = card · 🌀 = proof · 🤝 = affiliate · 🎯 = goal · "
                 f"<code>/show-card NAME</code> for content</i>")
    return "\n".join(lines)


async def _cmd_show_card(rest: str) -> str:
    """View a Champion's Character Card content (visibility-aware).

    Usage: /show-card NAME
    For inner/sacred cards, set ADMIN_TOKEN in env to bypass visibility gate.
    """
    name_or_slug = rest.strip()
    if not name_or_slug:
        return ("📇 <b>/show-card NAME</b>\n\n"
                "View a Champion's Character Card content.\n"
                "Example: <code>/show-card James Sunheart</code>")

    import httpx as _httpx
    admin_token = _os.environ.get("ADMIN_TOKEN", "")
    params = {"admin_token": admin_token} if admin_token else {}
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"{_FPAI_BASE.rstrip('/')}/api/champion/card/get/{name_or_slug}",
                            params=params)
            if r.status_code == 404:
                return f"📇 <b>No card found for: {tg._esc(name_or_slug)}</b>"
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"📇 <b>Card lookup failed</b>: {tg._esc(str(e))}"

    if not data.get("ok"):
        return (f"📇 <b>{tg._esc(data.get('name') or name_or_slug)}</b>\n\n"
                f"<i>{tg._esc(data.get('message') or 'card not viewable')}</i>")

    name = data.get("name") or name_or_slug
    level = data.get("level") or "?"
    visibility = data.get("visibility") or "?"
    updated = data.get("date_last_updated") or data.get("date_first_submitted") or ""
    content = data.get("content") or ""
    # Telegram caps at ~4096; trim if needed
    if len(content) > 3500:
        content = content[:3500] + "\n\n…<i>(truncated — view file directly for full)</i>"
    return (f"📇 <b>Card: {tg._esc(name)}</b> · L{tg._esc(str(level))} · "
            f"{tg._esc(visibility)} · {tg._esc(updated)}\n\n"
            f"<pre>{tg._esc(content)}</pre>")


async def _cmd_match(rest: str) -> str:
    """One specific helpful next move for the named Champion.

    Reads the player's lookup state via /api/champion/match and renders the
    chosen move + action URL. Defaults to "James Sunheart" when no name given.
    """
    import httpx as _httpx
    name = (rest or "").strip() or "James Sunheart"
    url = f"{_FPAI_BASE.rstrip('/')}/api/champion/match"
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(url, params={"name": name})
            r.raise_for_status()
            d = r.json()
    except Exception as e:
        return f"🎯 <b>Match</b>\n\n<i>Could not reach {tg._esc(_FPAI_BASE)}: {tg._esc(str(e))}</i>"

    if not d.get("ok"):
        err = d.get("error") or "unknown error"
        return f"🎯 <b>Match for {tg._esc(name)}</b>\n\n<i>{tg._esc(err)}</i>"

    icon = d.get("icon", "🎯")
    move = d.get("move", "Keep playing.")
    action = d.get("action", "")
    action_url = d.get("url", "")
    out = [f"{icon} <b>Match for {tg._esc(name)}</b>\n", tg._esc(move)]
    if action_url:
        out.append(f"\n<a href=\"{tg._esc(action_url)}\">→ Open</a>")
    if action:
        out.append(f"<i>action: {tg._esc(action)}</i>")
    return "\n".join(out)


# ───────────────────────────── /game ──────────────────────────────
async def _cmd_game() -> str:
    """Vital Game stats for the architect — composed from existing endpoints.

    Pulls from:
      GET /api/champion/stats          → counts + Field Score sum + growth
      GET /api/retreat/stats           → retreat-interest counter
      GET /api/champion/leaderboard    → top champions, top affiliates, top loops
    Each call is best-effort; missing data degrades the section, not the reply.
    """
    import httpx as _httpx
    headers = {"Accept": "application/json"}
    async def _fetch(path: str) -> dict | None:
        try:
            async with _httpx.AsyncClient(timeout=6.0) as c:
                r = await c.get(f"{_FPAI_BASE.rstrip('/')}{path}", headers=headers)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.warning("/game fetch %s failed: %s", path, e)
            return None

    stats, retreats, board = await asyncio.gather(
        _fetch("/api/champion/stats"),
        _fetch("/api/retreat/stats"),
        _fetch("/api/champion/leaderboard"),
    )

    if not stats:
        return f"🎮 <b>Game Stats</b>\n\n<i>Could not reach {tg._esc(_FPAI_BASE)}.</i>"

    champs_total = (stats.get("champions") or {}).get("total", 0)
    champs_public = (stats.get("champions") or {}).get("public", 0)
    cards_total = (stats.get("cards") or {}).get("total", 0)
    proofs_total = (stats.get("proofs") or {}).get("total", 0)
    proofs_public = (stats.get("proofs") or {}).get("public", 0)
    affiliate_links = stats.get("affiliate_links", 0)
    field_score = stats.get("field_score_sum", 0)
    growth = (stats.get("growth_this_week") or {})
    growth_total = growth.get("total", 0) or sum(int(growth.get(k, 0) or 0) for k in ("signatures", "proofs", "cards"))
    retreat_total = (retreats or {}).get("total", 0) if retreats else 0
    retreat_public = (retreats or {}).get("public", 0) if retreats else 0
    top_loops = ((board or {}).get("top_loops") or [])[:3]

    # 30-day goal status: champs >= 2 means "first non-James human" hit
    goal_hit = champs_total >= 2
    goal_line = (
        "✓ Goal hit — Game is no longer N=1." if goal_hit
        else f"✗ Champions: {champs_total} (need ≥2 for first non-James human)"
    )

    lines = [
        "🎮 <b>Game · Vital Stats</b>",
        f"\n🎯 <b>30-day goal:</b> {goal_line}",
        "",
        f"🌀 Champions: <b>{champs_total}</b> ({champs_public} public)",
        f"🎴 Characters built: <b>{cards_total}</b>",
        f"🌱 Proofs filed: <b>{proofs_total}</b> ({proofs_public} public)",
        f"🤝 Affiliate links generated: <b>{affiliate_links}</b>",
        f"📊 Field Score sum: <b>{field_score}</b>",
        f"🌴 Retreat interest: <b>{retreat_total}</b> ({retreat_public} public)",
        f"📈 Growth this week: <b>+{growth_total}</b>",
    ]

    if top_loops:
        lines.append("\n<b>Latest loops</b>")
        for L in top_loops:
            n = L.get("loop_number") or "?"
            player = tg._esc(L.get("player") or "?")
            quest = tg._esc((L.get("quest") or "")[:80])
            lines.append(f"  L{n} · {player} — {quest}")

    lines.append("\n<i>Source: fullpotential.com/api/champion + /api/retreat</i>")
    return "\n".join(lines)


# ───────────────────────────── /now ──────────────────────────────
async def _cmd_now() -> str:
    """Render current priority + status from top of NOW.md.

    Surfaces the cross-terminal coordination state so any session — Telegram,
    Claude Code, Cursor — can see what's being worked on right now.
    """
    try:
        with open(_NOW_PATH, encoding="utf-8") as f:
            now_md = f.read()
    except Exception as e:
        return f"📍 <b>Now</b>\n\n<i>NOW.md unreachable: {tg._esc(str(e))}</i>"

    import re as _re
    from datetime import datetime as _dt
    import os as _os3

    # Last-updated line + priority block (between '## 🎯 CURRENT PRIORITY' and next '##')
    updated_m = _re.search(r"\*\*Last Updated:\*\*\s*(.+)", now_md)
    updated = updated_m.group(1).strip() if updated_m else "?"

    prio_section = ""
    pm = _re.search(r"##\s+.*CURRENT\s+PRIORITY.*$", now_md, _re.IGNORECASE | _re.MULTILINE)
    if pm:
        body = now_md[pm.end():]
        next_h = _re.search(r"^---\s*$|^##\s", body, _re.MULTILINE)
        if next_h:
            body = body[: next_h.start()]
        prio_section = body.strip()

    age = ""
    try:
        diff = (_dt.now() - _dt.fromtimestamp(_os3.path.getmtime(_NOW_PATH))).total_seconds()
        if diff < 3600: age = f"{int(diff//60)}m ago"
        elif diff < 86400: age = f"{int(diff//3600)}h ago"
        else: age = f"{int(diff//86400)}d ago"
    except Exception:
        pass

    lines = ["📍 <b>Now</b>"]
    lines.append(f"<i>NOW.md last updated: {tg._esc(updated)}{f' · synced {age}' if age else ''}</i>\n")
    if prio_section:
        # Compact: convert markdown headings + bullets to telegram HTML
        for raw in prio_section.splitlines()[:30]:
            line = raw.strip()
            if not line:
                lines.append("")
                continue
            if line.startswith("###"):
                lines.append(f"<b>{tg._esc(line.lstrip('#').strip())}</b>")
            elif line.startswith("**") and line.endswith("**"):
                lines.append(f"<b>{tg._esc(line.strip('*').strip())}</b>")
            elif line.startswith("- ") or line.startswith("* "):
                lines.append(f"  • {tg._esc(line[2:])}")
            else:
                lines.append(_render_basic_markdown_html(line))
    lines.append("\n<i>Source: core/STATE/NOW.md · /goals · /projects · /questions for more</i>")
    return "\n".join(lines)


# ───────────────────────────── /vision ─────────────────────────────
async def _cmd_vision() -> str:
    """Surface the unifying vision: priority + 30-day goal + (if present) AI's
    Founder priority line. Source of truth is NOW.md + AI_GOALS.md."""
    try:
        with open(_NOW_PATH, encoding="utf-8") as f:
            now_md = f.read()
    except Exception as e:
        return f"🌅 <b>Vision</b>\n\n<i>NOW.md unreachable: {tg._esc(str(e))}</i>"

    parts = ["🌅 <b>Vision</b>\n"]

    # 30-day goal blockquote (top of NOW.md, e.g. "> **🎯 30-day goal:** ...")
    import re as _re_v
    g30 = _re_v.search(r"^>\s*\*\*🎯\s*30-day goal[^*]*\*\*\s*(.+?)$",
                       now_md, _re_v.MULTILINE)
    if g30:
        parts.append(f"<b>🎯 30-day goal</b>")
        parts.append(f"<i>{tg._esc(g30.group(1).strip())}</i>\n")

    # CURRENT PRIORITY section
    pri = _re_v.search(r"##\s+.*CURRENT PRIORITY[^\n]*\n+(?:###\s+)?(?:Priority:\s*)?(.+?)\n",
                       now_md, _re_v.IGNORECASE | _re_v.DOTALL)
    if pri:
        # Parse the few lines after CURRENT PRIORITY
        sec_start = pri.start()
        sec = now_md[sec_start: sec_start + 2000]
        # Title line
        title_m = _re_v.search(r"###\s+Priority:\s*(.+?)$", sec, _re_v.MULTILINE)
        status_m = _re_v.search(r"\*\*Status:\*\*\s*(.+?)$", sec, _re_v.MULTILINE)
        live_m = _re_v.search(r"\*\*Live at:\*\*\s*`?(.+?)`?\s*$", sec, _re_v.MULTILINE)
        filt_m = _re_v.search(r"\*\*Decision filter:\*\*\s*(.+?)$", sec, _re_v.MULTILINE)
        # First narrative paragraph after the bold metadata
        narrative_m = _re_v.search(r"^\n([A-Z][^\n]{40,}\.)\s*$", sec, _re_v.MULTILINE)
        parts.append("<b>🎯 The ONE Thing</b>")
        if title_m:
            parts.append(f"<b>{tg._esc(_strip_md(title_m.group(1)))}</b>")
        if status_m:
            parts.append(f"  {tg._esc(_strip_md(status_m.group(1)))}")
        if live_m:
            parts.append(f"  Live: {tg._esc(_strip_md(live_m.group(1)))}")
        if filt_m:
            parts.append(f"  <i>Decision filter: {tg._esc(_strip_md(filt_m.group(1)))}</i>")
        if narrative_m:
            parts.append(f"\n{tg._esc(_strip_md(narrative_m.group(1)))}")
        parts.append("")

    # Founder priority from AI_GOALS.md (one paragraph, mirrored from NOW.md)
    try:
        with open(_AI_GOALS_PATH, encoding="utf-8") as f:
            ai_md = f.read()
        fp = _re_v.search(r"\*\*Founder priority[^*]*\*\*\s*(.+?)(?=\n\n|\n##)",
                          ai_md, _re_v.DOTALL)
        if fp:
            parts.append("<b>🤖 What the AI is aligned to</b>")
            parts.append(f"<i>{tg._esc(_strip_md(fp.group(1).strip())[:600])}</i>\n")
    except Exception:
        pass

    parts.append("<i>For the goal breakdown: /goals · for the priority list: /projects</i>")
    return "\n".join(parts)


# ───────────────────────────── /goals ──────────────────────────────
async def _cmd_goals(arg: str = "") -> str:
    """Render goals broken down by audience: Founder (James) · AI · Team.

    Usage:
      /goals               — all three sections (compact)
      /goals james|founder — just James's goals (full detail, top 3 from NOW.md)
      /goals ai            — just AI working goals (from AI_GOALS.md)
      /goals team [COHORT] — just team/cohort goals (default cohort: zen-village)
    """
    a = (arg or "").strip().lower()
    only = ""
    cohort_arg = ""
    if a in ("james", "founder", "me"):
        only = "founder"
    elif a in ("ai", "system", "claude"):
        only = "ai"
    elif a == "team" or a.startswith("team "):
        only = "team"
        rest = a[4:].strip()
        if rest:
            cohort_arg = rest
    elif a.startswith("cohort "):
        only = "team"
        cohort_arg = a[7:].strip()

    sections: list[str] = []

    # ── Founder (James) — from NOW.md GOALS table ──────────────────────
    if only in ("", "founder"):
        founder_block = await _render_founder_goals(detail=(only == "founder"))
        if founder_block:
            sections.append(founder_block)

    # ── AI working goals — from AI_GOALS.md ────────────────────────────
    if only in ("", "ai"):
        ai_block = _render_ai_goals(detail=(only == "ai"))
        if ai_block:
            sections.append(ai_block)

    # ── Team / cohort goals — from champion-sign /cohort/{name} ────────
    if only in ("", "team"):
        team_cohort = cohort_arg or _DEFAULT_TEAM_COHORT
        team_block = await _render_team_goals(team_cohort, detail=(only == "team"))
        if team_block:
            sections.append(team_block)

    if not sections:
        return ("🎯 <b>Goals</b>\n\n<i>No goals found in any tier. Add to NOW.md GOALS section, "
                "AI_GOALS.md, or via /setgoal on @fullpotentialgamebot.</i>")

    header = "🎯 <b>Goals — broken down by audience</b>\n" if not only else ""
    footer = ("\n<i>/goals james · /goals ai · /goals team [cohort] for one tier. "
              "/vision for the unifying frame.</i>" if not only else "")
    return header + "\n\n".join(sections) + footer


async def _render_founder_goals(detail: bool = False) -> str:
    """Top-3 founder goals from NOW.md GOALS table."""
    try:
        with open(_NOW_PATH, encoding="utf-8") as f:
            now_md = f.read()
    except Exception as e:
        return f"<b>👤 For James (founder)</b>\n<i>NOW.md unreachable: {tg._esc(str(e))}</i>"
    rows = _parse_goals(now_md)
    if not rows:
        return ("<b>👤 For James (founder)</b>\n"
                "<i>No GOALS section in NOW.md. Add `## 🎯 GOALS` with a markdown table.</i>")
    lines = ["<b>👤 For James (founder)</b> — <i>top 3 from NOW.md</i>"]
    n = 3 if not detail else len(rows)
    for r in rows[:n]:
        lines.append(f"<b>#{r['rank']}</b> {tg._esc(r['goal'])}")
        if detail:
            if r.get("target"):
                lines.append(f"   🎯 <b>Target:</b> {tg._esc(r['target'])}")
            if r.get("timeframe"):
                lines.append(f"   🕐 <b>By:</b> {tg._esc(r['timeframe'])}")
            if r.get("state"):
                lines.append(f"   📍 <i>{tg._esc(r['state'])}</i>")
        else:
            bits = []
            if r.get("target"): bits.append(tg._esc(r['target']))
            if r.get("timeframe"): bits.append(tg._esc(r['timeframe']))
            if bits:
                lines.append(f"   <i>{' · '.join(bits)}</i>")
    if not detail and len(rows) > 3:
        lines.append(f"   <i>+{len(rows)-3} more — /goals james for full list</i>")
    return "\n".join(lines)


def _render_ai_goals(detail: bool = False) -> str:
    """Active AI working goals from AI_GOALS.md."""
    try:
        with open(_AI_GOALS_PATH, encoding="utf-8") as f:
            ai_md = f.read()
    except Exception:
        return ("<b>🤖 For the AI</b>\n"
                f"<i>AI_GOALS.md not synced (expected at {tg._esc(_AI_GOALS_PATH)}).</i>")
    rows = _parse_ai_goals(ai_md)
    if not rows:
        return "<b>🤖 For the AI</b>\n<i>No `### G<n> — Title` entries found in AI_GOALS.md.</i>"
    lines = ["<b>🤖 For the AI</b> — <i>working goals from AI_GOALS.md</i>"]
    n = 4 if not detail else len(rows)
    for r in rows[:n]:
        lines.append(f"<b>{tg._esc(r['id'])}</b> {tg._esc(r['title'])}")
        if detail:
            if r.get("why"):
                lines.append(f"   <i>Why:</i> {tg._esc(r['why'][:200])}")
            if r.get("how"):
                lines.append(f"   <i>How:</i> {tg._esc(r['how'][:200])}")
            if r.get("status"):
                lines.append(f"   📍 <i>{tg._esc(r['status'][:120])}</i>")
        elif r.get("status"):
            lines.append(f"   <i>📍 {tg._esc(r['status'][:120])}</i>")
    return "\n".join(lines)


async def _render_team_goals(cohort: str, detail: bool = False) -> str:
    """Per-Champion active goals across one cohort, via champion-sign API."""
    import httpx as _httpx
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"{_FPAI_BASE.rstrip('/')}/api/champion/cohort/{cohort}")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return (f"<b>👥 For the team — cohort: {tg._esc(cohort)}</b>\n"
                f"<i>API unreachable: {tg._esc(str(e))}</i>")
    members = data.get("members", [])
    if not members:
        return (f"<b>👥 For the team — cohort: {tg._esc(cohort)}</b>\n"
                f"<i>No Champions in this cohort yet. Invite some via "
                f"`/invite NAME contact path cohort={tg._esc(cohort)}`.</i>")
    members_with_goals = [m for m in members if (m.get("active_goals") or [])]
    lines = [f"<b>👥 For the team — cohort: {tg._esc(cohort)}</b> "
             f"<i>· {len(members)} members · {len(members_with_goals)} with active goals</i>"]
    if not members_with_goals:
        lines.append("<i>No active per-Champion goals yet. Members can /setgoal on @fullpotentialgamebot.</i>")
        return "\n".join(lines)
    for m in members_with_goals[:8]:
        nm = m.get("name") or "?"
        cn = m.get("champion_number") or "?"
        lines.append(f"<b>#{cn} {tg._esc(nm)}</b>")
        for g in (m.get("active_goals") or [])[:3]:
            text = g.get("goal", "")
            if not text:
                continue
            meta = []
            if g.get("target"): meta.append(f"target: {g['target']}")
            if g.get("timeframe"): meta.append(f"by {g['timeframe']}")
            meta_str = f" <i>({' · '.join(meta)})</i>" if meta else ""
            lines.append(f"   🎯 {tg._esc(text[:120])}{meta_str}")
    if len(members_with_goals) > 8:
        lines.append(f"<i>+{len(members_with_goals)-8} more team members with goals.</i>")
    return "\n".join(lines)


def _parse_ai_goals(md: str) -> list[dict]:
    """Parse AI_GOALS.md '### G<n> — Title' blocks. Each block has Why/How/Status lines."""
    import re
    sec = re.search(r"##\s+.*ACTIVE AI WORKING GOALS.*$", md,
                    re.MULTILINE | re.IGNORECASE)
    if not sec:
        return []
    body = md[sec.end():]
    nh = re.search(r"^##\s", body, re.MULTILINE)
    if nh:
        body = body[: nh.start()]
    rows: list[dict] = []
    # Split on `### G<n>` entries
    block_re = re.compile(r"^###\s+(G\d+(?:\.\d+)?)\s*[—-]\s*(.+?)$", re.MULTILINE)
    matches = list(block_re.finditer(body))
    for i, m in enumerate(matches):
        gid = m.group(1).strip()
        title = m.group(2).strip()
        block_start = m.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        block = body[block_start:block_end]
        why_m = re.search(r"\*\*Why:\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)", block, re.DOTALL)
        how_m = re.search(r"\*\*How AI applies:\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)", block, re.DOTALL)
        status_m = re.search(r"\*\*Status:\*\*\s*(.+?)(?=\n\*\*|\n###|\Z)", block, re.DOTALL)
        rows.append({
            "id": gid,
            "title": title,
            "why": _strip_md(why_m.group(1).strip().replace("\n", " ")) if why_m else "",
            "how": _strip_md(how_m.group(1).strip().replace("\n", " ")) if how_m else "",
            "status": _strip_md(status_m.group(1).strip().replace("\n", " ")) if status_m else "",
        })
    return rows


def _parse_goals(md: str) -> list[dict]:
    """Parse GOALS markdown table — columns: # | Goal | Target | Timeframe | Current state."""
    import re
    sec = re.search(r"##\s+.*GOALS.*$", md, re.MULTILINE | re.IGNORECASE)
    if not sec:
        return []
    body = md[sec.end():]
    nh = re.search(r"^\n##\s", body, re.MULTILINE)
    if nh:
        body = body[: nh.start()]
    rows: list[dict] = []
    row_re = re.compile(r"^\|\s*(\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|\s*$", re.MULTILINE)
    for rm in row_re.finditer(body):
        rows.append({
            "rank": int(rm.group(1)),
            "goal": _strip_md(rm.group(2)),
            "target": _strip_md(rm.group(3)),
            "timeframe": _strip_md(rm.group(4)),
            "state": _strip_md(rm.group(5)),
        })
    rows.sort(key=lambda r: r["rank"])
    return rows


# ───────────────────────────── /signals ──────────────────────────────
_SIGNALS_CATEGORIES = {"game", "money", "leads", "trading"}
_SIGNALS_MORE_TOKENS = {"more", "expand", "detail", "details", "verbose", "all", "full"}


async def _cmd_signals(arg: str = "") -> str:
    """Compose live signals: GAME · MONEY · LEADS · TRADING.

    Modes:
      ""              — compact (top 3 each, one-line trades)
      "more"          — everything expanded (liquid breakdown, top costs, etc.)
      "game"/"money"/"leads"/"trading" — drill into one section in full detail
    """
    a = (arg or "").strip().lower()
    if a in _SIGNALS_MORE_TOKENS:
        mode = "more"
    elif a in _SIGNALS_CATEGORIES:
        mode = a
    else:
        mode = "compact"

    show_game = mode in ("compact", "more", "game")
    show_money = mode in ("compact", "more", "money")
    show_leads = mode in ("compact", "more", "leads")
    show_trading = mode in ("compact", "more", "trading")
    full_game = mode in ("more", "game")
    full_money = mode in ("more", "money")
    full_leads = mode in ("more", "leads")
    full_trading = mode in ("more", "trading")

    import httpx as _httpx
    headers = {"Accept": "application/json"}

    async def _fetch_json(url: str) -> dict | None:
        try:
            async with _httpx.AsyncClient(timeout=6.0) as c:
                r = await c.get(url, headers=headers)
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.warning("/signals fetch %s failed: %s", url, e)
            return None

    base = _os.environ.get("FPAI_BASE_URL", "https://fullpotential.com")
    cos_url = _os.environ.get("CHIEF_OF_STAFF_URL", "http://127.0.0.1:8107")
    wt_base = _os.environ.get("WHALETRACK_PUBLIC_BASE", "https://fullpotential.ai/dashboards/whaletrack")

    wt_symbols = [s.strip().upper() for s in
                  _os.environ.get("WHALETRACK_SYMBOLS", "SOL,BTC,ETH,XRP").split(",") if s.strip()]

    fetches = []
    fetches.append(_fetch_json(f"{base}/api/champion/signals") if show_game or show_leads else _async_none())
    fetches.append(_fetch_json(f"{base}/api/champion/retreat/list") if show_leads else _async_none())
    fetches.append(_fetch_json(f"{base}/api/champion/leaderboard") if show_leads else _async_none())
    fetches.append(_fetch_json(f"{base}/api/champion/list") if show_leads else _async_none())
    fetches.append(_fetch_json(f"{cos_url}/money") if show_money else _async_none())
    if show_trading:
        sig_reads = asyncio.gather(*[_fetch_json(f"{wt_base}/api/signal-read/{s}") for s in wt_symbols])
    else:
        sig_reads = _async_none()
    fetches.append(sig_reads)
    game_signals, retreats, board, listing, money, signal_reads = await asyncio.gather(*fetches)

    title = {
        "compact": "📡 <b>Signals</b>",
        "more": "📡 <b>Signals — full</b>",
        "game": "🎮 <b>Signals · Game</b>",
        "money": "💰 <b>Signals · Money</b>",
        "leads": "📥 <b>Signals · Leads</b>",
        "trading": "📈 <b>Signals · Trading</b>",
    }[mode]
    lines = [title, ""]

    if show_game:
        lines.extend(_render_game(game_signals, full=full_game))
    if show_money:
        if show_game:
            lines.append("")
        lines.extend(_render_money(money, full=full_money))
    if show_leads:
        if show_game or show_money:
            lines.append("")
        retreat_count = (retreats or {}).get("count", 0)
        champ_count = (listing or {}).get("count", 0)
        top_champs = (board or {}).get("top_champions", [])
        cards_filled = sum(1 for c in top_champs if c.get("card"))
        affiliates_total = sum(int(c.get("affiliates", 0) or 0) for c in top_champs)
        lines.extend(_render_leads(
            retreat_count, champ_count, cards_filled, affiliates_total, full=full_leads,
        ))
    if show_trading:
        if show_game or show_money or show_leads:
            lines.append("")
        lines.extend(_render_trading(signal_reads, wt_symbols, wt_base, full=full_trading))

    if mode == "compact":
        lines.append("")
        lines.append("<i>/more · /signals game|money|leads|trading</i>")
    return "\n".join(lines)


async def _async_none():
    return None


def _render_game(game_signals: dict | None, *, full: bool) -> list[str]:
    out: list[str] = ["<b>🎮 GAME</b>"]
    if not game_signals:
        out.append("  ⚪ <i>/api/champion/signals unreachable</i>")
        return out
    goal = game_signals.get("goal_30d") or {}
    coh = game_signals.get("field_coherence") or {}
    comps = coh.get("components") or {}
    state = game_signals.get("field_state") or {}
    act = game_signals.get("activity_7d") or {}

    if goal.get("name"):
        cur = goal.get("current")
        tgt = goal.get("target")
        done = "✓" if goal.get("complete") else f"{cur}/{tgt}"
        out.append(f"  🎯 <i>{tg._esc(goal['name'])}</i> · <b>{tg._esc(str(done))}</b>")

    head = coh.get("headline")
    if head is not None:
        head_str = f"{float(head):.2f}"
        if full:
            comp_strs = []
            for k in ("activity", "witness", "conversion", "drift"):
                v = comps.get(k)
                comp_strs.append(f"{k} {'—' if v is None else f'{float(v):.2f}'}")
            out.append(f"  🌡 Coherence: <b>{head_str}</b> · " + " · ".join(comp_strs))
        else:
            out.append(f"  🌡 Coherence: <b>{head_str}</b>")

    if state:
        out.append(
            f"  📊 {state.get('champions',0)} champ · "
            f"{state.get('proofs',0)} proofs · "
            f"{state.get('mirrors',0)} mirrors · "
            f"{state.get('leads',0)} leads · "
            f"score {state.get('field_score_sum',0)}"
        )
    if act:
        lp = act.get("last_proof") or {}
        last_str = f"L{lp.get('loop_number')}" if lp.get("loop_number") else "?"
        out.append(
            f"  📈 7d: +{act.get('new_champions',0)} champs · "
            f"+{act.get('new_proofs',0)} proofs · "
            f"+{act.get('new_mirrors',0)} mirrors · last {last_str}"
        )
        if full and lp.get("player"):
            out.append(
                f"     <i>last proof: {tg._esc(lp.get('player','?'))} · "
                f"L{tg._esc(str(lp.get('loop_number','?')))} · "
                f"{tg._esc((lp.get('ts','') or '')[:16])}</i>"
            )
    if full:
        top_inviter = game_signals.get("top_inviter")
        if top_inviter:
            out.append(f"  ↗ Top inviter: <b>{tg._esc(top_inviter.get('name','?'))}</b> · {top_inviter.get('count',0)} invited")
        notes = coh.get("notes") or {}
        for k in ("activity", "witness", "conversion", "drift"):
            n = notes.get(k)
            if n:
                out.append(f"     <i>{k}:</i> <i>{tg._esc(str(n)[:160])}</i>")
        stats = coh.get("stats") or {}
        if stats:
            out.append(
                f"  📐 stats: {stats.get('proofs_total',0)} proofs · "
                f"{stats.get('proofs_distance_weighted_witnessed',0)} DWW · "
                f"{stats.get('proofs_self_or_ai_witnessed',0)} self/AI · "
                f"{stats.get('mirrors_paired',0)} mirrors"
            )
    return out


def _render_money(money: dict | None, *, full: bool) -> list[str]:
    out: list[str] = ["<b>💰 MONEY</b>"]
    if not money:
        out.append("  ⚪ <i>Chief of Staff unreachable</i>")
        return out
    total_cost = float(money.get("total_cost_monthly_usd") or 0)
    total_rev = float(money.get("total_revenue_monthly_usd") or 0)
    net = float(money.get("net_monthly_usd") or (total_rev - total_cost))
    net_glyph = "🟢" if net > 0 else ("🔴" if net < 0 else "⚪")
    out.append(
        f"  {net_glyph} Net: <b>${net:+,.0f}/mo</b> · rev ${total_rev:,.0f} · cost ${total_cost:,.0f}"
    )

    ledger = None
    try:
        ledger = _money_load_ledger()
    except Exception as e:
        log.warning("/signals ledger read failed: %s", e)
    ledger_liquid = ledger.get("liquid_assets") if isinstance(ledger, dict) else None
    groups = (ledger_liquid or {}).get("groups") if isinstance(ledger_liquid, dict) else None
    liquid_total = 0.0
    if isinstance(groups, list):
        for g in groups:
            for a in g.get("accounts") or []:
                try:
                    liquid_total += float(a.get("balance_usd") or 0)
                except Exception:
                    pass
    if liquid_total > 0:
        if net > 0 and total_cost > 0:
            zr = liquid_total / total_cost
            runway_str = f" · runway <b>∞</b> <i>(zero-rev: {zr:.0f} mo)</i>"
        elif total_cost > 0:
            runway_str = f" · runway <b>{liquid_total/total_cost:.1f} mo</b>"
        else:
            runway_str = ""
        out.append(f"  💵 Liquid: <b>${liquid_total:,.0f}</b>{runway_str}")

    leak = money.get("biggest_leak") or {}
    if leak.get("name"):
        out.append(
            f"  🔧 Biggest leak: {tg._esc(leak.get('name','?'))} "
            f"(${float(leak.get('monthly_usd',0)):,.0f}/mo)"
        )

    if full:
        if isinstance(groups, list) and groups:
            out.append("  <i>Liquid breakdown:</i>")
            for g in groups:
                g_name = g.get("name") or g.get("id") or "?"
                accts = g.get("accounts") or []
                g_total = sum(float(a.get("balance_usd") or 0) for a in accts)
                out.append(f"    · <b>{tg._esc(g_name)}</b> — <b>${g_total:,.0f}</b>")
                for a in sorted(accts, key=lambda x: -float(x.get("balance_usd") or 0))[:6]:
                    a_name = a.get("name") or a.get("id") or "?"
                    a_bal = float(a.get("balance_usd") or 0)
                    a_type = a.get("type") or ""
                    type_str = f" <i>({tg._esc(a_type)})</i>" if a_type else ""
                    out.append(f"       ${a_bal:>9,.0f}  {tg._esc(a_name)}{type_str}")
                if len(accts) > 6:
                    out.append(f"       <i>…+{len(accts)-6} more</i>")
        rev = money.get("revenue") or []
        rev_real = [r for r in rev if float(r.get("revenue_usd", 0) or 0) > 0]
        if rev_real:
            out.append("  <i>Revenue streams:</i>")
            for r in sorted(rev_real, key=lambda x: -float(x.get("revenue_usd",0) or 0))[:5]:
                stream = r.get("stream") or r.get("name") or "?"
                mo = float(r.get("revenue_usd", 0) or 0)
                out.append(f"    + ${mo:,.0f}/mo  {tg._esc(stream)}")
        costs = money.get("costs") or []
        if costs:
            out.append("  <i>Top costs:</i>")
            for c in sorted(costs, key=lambda x: -float(x.get("monthly_usd",0) or 0))[:5]:
                nm = tg._esc(c.get("name", "?"))
                mo = float(c.get("monthly_usd", 0) or 0)
                kill = " 🗑" if c.get("kill_candidate") else ""
                out.append(f"    − ${mo:,.0f}  {nm}{kill}")
        trades = (ledger or {}).get("trades") or []
        open_trades = [t for t in trades if not t.get("closed_at")]
        if open_trades:
            out.append(f"  <i>Open trades: {len(open_trades)}</i>")
            for t in open_trades[:5]:
                out.append(
                    f"    · {tg._esc(str(t.get('symbol') or '?'))} "
                    f"{tg._esc(str(t.get('side') or ''))} "
                    f"{t.get('qty')} @ {t.get('price')}"
                )
    return out


def _render_leads(retreat_count: int, champ_count: int, cards_filled: int,
                  affiliates_total: int, *, full: bool) -> list[str]:
    out: list[str] = ["<b>📥 LEADS</b>"]
    if full:
        out.append(f"  🏝 Retreat leads: <b>{retreat_count}</b>")
        out.append(f"  🎉 Party leads: <b>0</b> <i>(no endpoint yet)</i>")
        out.append(f"  🤝 Coaching leads: <b>0</b> <i>(no marketplace yet)</i>")
        out.append(f"  🛍 Commerce leads: <b>0</b> <i>(no marketplace yet)</i>")
        out.append(f"  👥 Champions: <b>{champ_count}</b>")
        out.append(f"  📇 Cards filled: <b>{cards_filled}/{champ_count}</b>")
        out.append(f"  ↗ Affiliates: <b>{affiliates_total}</b>")
    else:
        out.append(
            f"  🏝 {retreat_count} retreat · "
            f"👥 {champ_count} champion{'s' if champ_count != 1 else ''} · "
            f"📇 {cards_filled}/{champ_count} cards · "
            f"↗ {affiliates_total} affiliates"
        )
    return out


_VERDICT_DOT = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def _render_trading(signal_reads: list | None, symbols: list[str], wt_base: str,
                    *, full: bool) -> list[str]:
    """Render WhaleTrack signals using /api/signal-read/<sym> per symbol —
    same source as the WhaleTrack Telegram bot, so verdicts match
    (honesty multiplier + asymmetry boost applied).
    """
    out: list[str] = ["<b>📈 TRADING · WhaleTrack</b> <i>(paper)</i>"]
    if not signal_reads or not any(signal_reads):
        out.append(f"  🔴 <i>WhaleTrack signal-read unreachable at {tg._esc(wt_base)}</i>")
        return out

    # Surface a single most-severe system_alerts banner (matches WT bot)
    banner = None
    for d in signal_reads:
        if not d:
            continue
        for a in d.get("system_alerts") or []:
            if banner is None:
                banner = a
                break
        if banner:
            break
    if banner:
        sev = (banner.get("severity") or "").lower()
        icon = "⚠️" if sev == "warn" else ("🔔" if sev == "info" else "ℹ️")
        out.append(f"  {icon} <b>{tg._esc(banner.get('headline','') or '')}</b>")
        if full and banner.get("detail"):
            out.append(f"     <i>{tg._esc(banner['detail'][:200])}</i>")

    rendered = 0
    for sym, d in zip(symbols, signal_reads):
        if not d:
            out.append(f"  ⚪ <i>{tg._esc(sym)}: no signal</i>")
            continue
        v = d.get("verdict") or {}
        action = (v.get("action") or "?").upper()
        color = (v.get("color") or "").lower()
        dot = _VERDICT_DOT.get(color, "⚪")
        conf = v.get("confidence_pct")
        raw = v.get("confidence_raw_pct")
        price = d.get("current_price")
        chg = d.get("change_24h_pct")
        chg_str = f" ({chg:+.1f}%)" if isinstance(chg, (int, float)) else ""
        conf_str = f"{conf:.0f}%" if isinstance(conf, (int, float)) else "?"

        # Asymmetry tag (e.g. "↗ liq long 4.0:1") when the signal carries it
        asym_tag = ""
        a_sig = (v.get("asymmetry_signal") or "").upper()
        a_ratio = v.get("asymmetry_ratio")
        if a_sig in ("LONG", "SHORT") and isinstance(a_ratio, (int, float)) and a_ratio > 1.2:
            arrow = "↗" if a_sig == "LONG" else "↘"
            asym_tag = f"  <i>{arrow} liq {a_sig.lower()} {a_ratio:.1f}:1</i>"

        head = f"  {dot} <b>{tg._esc(sym)}</b> ${_fmt_price(price)}{chg_str} → <b>{tg._esc(action)}</b> ({conf_str}){asym_tag}"
        out.append(head)

        if full:
            # Show the raw vs adjusted confidence breakdown so the gap is visible
            adj_bits = []
            if isinstance(raw, (int, float)) and raw is not None:
                adj_bits.append(f"raw {raw:.0f}%")
            ab = v.get("asymmetry_boost_pct")
            if isinstance(ab, (int, float)) and abs(ab) > 0.5:
                adj_bits.append(f"asym {ab:+.0f}%")
            hm = v.get("honesty_multiplier")
            if isinstance(hm, (int, float)):
                adj_bits.append(f"honesty ×{hm:.2f}")
            if adj_bits:
                out.append(f"     <i>{' · '.join(adj_bits)}</i>")
            ag_n = v.get("agreement_score")
            ag_t = v.get("total_sources")
            ag_pct = v.get("agreement_pct")
            if ag_n is not None and ag_t:
                pct_str = f", {ag_pct:.0f}% agree" if isinstance(ag_pct, (int, float)) else ""
                out.append(f"     <i>{ag_n}/{ag_t} sources{pct_str}</i>")
        rendered += 1

    if rendered == 0:
        out.append("  ⚪ <i>No signal-read responses came back.</i>")
        return out

    if full:
        out.append(f"  <i>Source: {tg._esc(wt_base)}/api/signal-read/&lt;sym&gt; · matches @whaletrack bot</i>")
    return out


def _fmt_price(p) -> str:
    """Format price: thousands separator + appropriate decimals."""
    try:
        v = float(p)
    except Exception:
        return str(p)
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 1:
        return f"{v:,.2f}"
    return f"{v:,.4f}"


# ───────────────────────────── /decisions ──────────────────────────────
async def _cmd_decisions() -> str:
    """Unified decision queue — Curator Queue + qb blocked questions."""
    lines = ["⚖️ <b>Decisions — items waiting on you</b>\n"]
    found = False

    # Source 1: Curator Queue 🟡 Proposed rows
    try:
        async with AppFlowy() as af:
            _, db_id = await af.find_database_id("07 · Curator Queue")
            ids = await af.list_rows(db_id, limit=40)
            curator_pending = []
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
                if status.startswith("🟡 Proposed") and prop:
                    curator_pending.append((rid, prop))
                if len(curator_pending) >= 5:
                    break
        if curator_pending:
            found = True
            lines.append(f"<b>📋 Curator Queue</b> <i>({len(curator_pending)} pending)</i>")
            for _rid, prop in curator_pending:
                lines.append(f"  · {tg._esc(prop[:140])}")
            lines.append("  <i>Use /pending to see approve buttons.</i>\n")
    except Exception as e:
        lines.append(f"<i>Curator Queue unavailable: {tg._esc(str(e)[:120])}</i>\n")

    # Source 2: qb blocked questions across books
    try:
        with open(_QB_BOARD_PATH, encoding="utf-8") as f:
            raw = f.read()
        import json as _json
        events = []
        for ln in raw.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                events.append(_json.loads(ln))
            except Exception:
                continue
        state = _qb_derive_state(events)
        blocked = [q for q in state.values() if q["status"] == "blocked"]
        if blocked:
            found = True
            lines.append(f"<b>⊗ qb blocked</b> <i>({len(blocked)})</i>")
            for q in blocked[:5]:
                book = q.get("book") or "?"
                lines.append(f"  · [{tg._esc(book)}] {tg._esc(_qb_short(q['text'], 110))}")
                if q.get("block_reason"):
                    lines.append(f"     ⊗ <i>{tg._esc(_qb_short(q['block_reason'], 100))}</i>")
            lines.append("")
    except Exception:
        pass

    if not found:
        lines.append("✅ <i>Nothing waiting on you. Decision queue clear.</i>")

    lines.append("<i>Sources: Curator Queue (AppFlowy) + qb blocked across books</i>")
    return "\n".join(lines)


# ───────────────────────────── /money ──────────────────────────────
_LEDGER_PATH = _os.environ.get(
    "LEDGER_PATH", "/opt/chief-of-staff/state/ledger.json"
)
_MONEY_AUDIT_PATH = _os.environ.get(
    "MONEY_AUDIT_PATH", "/var/lib/sh-brain/state/money_edits.jsonl"
)


def _money_load_ledger() -> dict:
    import json as _json
    with open(_LEDGER_PATH) as f:
        return _json.load(f)


def _money_save_ledger(data: dict) -> None:
    """Atomic write."""
    import json as _json
    tmp = _LEDGER_PATH + ".tmp"
    with open(tmp, "w") as f:
        _json.dump(data, f, indent=2)
    _os.replace(tmp, _LEDGER_PATH)


def _money_audit(action: str, payload: dict) -> None:
    """Append a one-line audit record. Best-effort; silent failure."""
    import json as _json
    from datetime import datetime as _dt
    try:
        _os.makedirs(_os.path.dirname(_MONEY_AUDIT_PATH), exist_ok=True)
        rec = {
            "ts": _dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action": action,
            **payload,
        }
        with open(_MONEY_AUDIT_PATH, "a") as f:
            f.write(_json.dumps(rec) + "\n")
    except Exception as e:
        log.warning("money audit log failed: %s", e)


async def _cmd_money(rest: str = "") -> str:
    """Dispatcher. /money [set|add|<free text>]."""
    rest = (rest or "").strip()
    if not rest:
        return await _money_view()

    parts = rest.split(maxsplit=1)
    sub = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if sub == "set":
        return await _money_set(arg)
    if sub == "add":
        return await _money_add(arg)
    if sub in ("balance", "balances", "liquid"):
        return await _money_liquid_view()
    if sub == "set-balance":
        return await _money_set_balance(arg)
    if sub == "trade":
        # Sub-subcommands: close / delete / cancel
        sub_parts = arg.split(maxsplit=1)
        if sub_parts and sub_parts[0].lower() in ("close", "exit"):
            return await _money_trade_close(sub_parts[1] if len(sub_parts) > 1 else "")
        if sub_parts and sub_parts[0].lower() in ("delete", "remove", "cancel", "del"):
            return await _money_trade_delete(sub_parts[1] if len(sub_parts) > 1 else "")
        return await _money_trade(arg)
    if sub == "trades":
        return await _money_trades_view()
    if sub in ("onebpo", "business", "pl", "p&l"):
        return await _money_onebpo_view()
    # Anything else: free-text money note → propose via Curator Queue
    return await _money_note(rest)


async def _money_set(arg: str) -> str:
    """Update an existing cost line. Format: <id> <amount> [purpose]"""
    parts = arg.split(maxsplit=2)
    if len(parts) < 2:
        return ("Usage: <code>/money set &lt;id&gt; &lt;amount&gt; [purpose]</code>\n"
                "Example: <code>/money set anthropic-max 200</code>")
    item_id = parts[0]
    try:
        amount = float(parts[1].lstrip("$").replace(",", ""))
    except ValueError:
        return f"⚠️ amount must be a number (got <code>{tg._esc(parts[1])}</code>)"
    new_purpose = parts[2] if len(parts) > 2 else None

    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"⚠️ ledger unreachable at <code>{tg._esc(_LEDGER_PATH)}</code>: {tg._esc(str(e))}"

    costs = ledger.get("costs_monthly_usd", [])
    target = next((c for c in costs if c.get("id") == item_id), None)
    if not target:
        existing = ", ".join(c.get("id", "?") for c in costs)
        return f"⚠️ id <code>{tg._esc(item_id)}</code> not found in costs.\nKnown ids: <code>{tg._esc(existing)}</code>"

    old_amount = float(target.get("monthly_usd", 0) or 0)
    old_purpose = target.get("purpose", "")
    target["monthly_usd"] = amount
    if new_purpose:
        target["purpose"] = new_purpose
    from datetime import datetime as _dt2
    ledger["last_updated"] = _dt2.utcnow().strftime("%Y-%m-%d")

    try:
        _money_save_ledger(ledger)
    except Exception as e:
        return f"⚠️ ledger save failed: {tg._esc(str(e))}"

    _money_audit("set", {"id": item_id, "old": old_amount, "new": amount, "purpose": new_purpose})
    delta = amount - old_amount
    sign = "+" if delta >= 0 else ""
    lines = [
        f"✅ <b>Updated:</b> {tg._esc(target.get('name', item_id))}",
        f"  ${old_amount:,.0f}/mo → <b>${amount:,.0f}/mo</b>  ({sign}${delta:,.0f})",
    ]
    if new_purpose:
        lines.append(f"  purpose: <i>{tg._esc(new_purpose)}</i>")
    lines.append(f"\n<i>Audit: {tg._esc(_MONEY_AUDIT_PATH)}</i>")
    lines.append("<i>To pull change back to repo: scp from brain server</i>")
    return "\n".join(lines)


async def _money_add(arg: str) -> str:
    """Add new cost or revenue line.

    Formats:
      add cost <id> <name-or-quoted-name> <amount> <category> [purpose]
      add revenue <stream> <amount/mo> [note]
    """
    parts = arg.split(maxsplit=1)
    if not parts:
        return ("Usage:\n"
                "  <code>/money add cost &lt;id&gt; &lt;name&gt; &lt;amount&gt; &lt;category&gt; [purpose]</code>\n"
                "  <code>/money add revenue &lt;stream&gt; &lt;amount/mo&gt; [note]</code>")
    kind = parts[0].lower()
    body = parts[1] if len(parts) > 1 else ""

    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"⚠️ ledger unreachable: {tg._esc(str(e))}"

    if kind == "cost":
        # id name amount category [purpose...]
        bits = body.split(maxsplit=4)
        if len(bits) < 4:
            return ("Usage: <code>/money add cost &lt;id&gt; &lt;name&gt; &lt;amount&gt; &lt;category&gt; [purpose]</code>\n"
                    "Example: <code>/money add cost stripe-fees 'Stripe processing' 45 fees Card processing</code>")
        item_id, name, amt_raw, category = bits[0], bits[1].strip("\"'"), bits[2], bits[3]
        purpose = bits[4] if len(bits) > 4 else ""
        try:
            amount = float(amt_raw.lstrip("$").replace(",", ""))
        except ValueError:
            return f"⚠️ amount must be a number (got <code>{tg._esc(amt_raw)}</code>)"
        costs = ledger.setdefault("costs_monthly_usd", [])
        if any(c.get("id") == item_id for c in costs):
            return f"⚠️ id <code>{tg._esc(item_id)}</code> already exists. Use /money set instead."
        new_row = {
            "name": name, "id": item_id, "category": category,
            "engine_role": "infra", "monthly_usd": amount, "purpose": purpose,
        }
        costs.append(new_row)
        from datetime import datetime as _dt3
        ledger["last_updated"] = _dt3.utcnow().strftime("%Y-%m-%d")
        try:
            _money_save_ledger(ledger)
        except Exception as e:
            return f"⚠️ ledger save failed: {tg._esc(str(e))}"
        _money_audit("add_cost", new_row)
        return (f"✅ <b>Added cost:</b> {tg._esc(name)} (id <code>{tg._esc(item_id)}</code>)\n"
                f"  ${amount:,.0f}/mo  ·  category: {tg._esc(category)}")

    if kind == "revenue":
        # stream amount [note...]
        bits = body.split(maxsplit=2)
        if len(bits) < 2:
            return ("Usage: <code>/money add revenue &lt;stream&gt; &lt;amount/mo&gt; [note]</code>\n"
                    "Example: <code>/money add revenue stripe_credits 250 First Stripe credit purchase</code>")
        stream, amt_raw = bits[0], bits[1]
        note = bits[2] if len(bits) > 2 else ""
        try:
            amount = float(amt_raw.lstrip("$").replace(",", ""))
        except ValueError:
            return f"⚠️ amount must be a number (got <code>{tg._esc(amt_raw)}</code>)"
        rev = ledger.setdefault("revenue_monthly", {})
        if stream in rev:
            old = float(rev[stream].get("revenue_usd", 0) or 0)
            rev[stream]["revenue_usd"] = amount
            if note:
                rev[stream]["_note"] = note
            from datetime import datetime as _dt4
            rev[stream]["as_of"] = _dt4.utcnow().isoformat() + "Z"
            action = "update_revenue"
            verb = "Updated"
            extra = f"${old:,.0f}/mo → <b>${amount:,.0f}/mo</b>"
        else:
            from datetime import datetime as _dt5
            rev[stream] = {
                "revenue_usd": amount,
                "_note": note,
                "as_of": _dt5.utcnow().isoformat() + "Z",
            }
            action = "add_revenue"
            verb = "Added"
            extra = f"${amount:,.0f}/mo"
        from datetime import datetime as _dt6
        ledger["last_updated"] = _dt6.utcnow().strftime("%Y-%m-%d")
        try:
            _money_save_ledger(ledger)
        except Exception as e:
            return f"⚠️ ledger save failed: {tg._esc(str(e))}"
        _money_audit(action, {"stream": stream, "amount": amount, "note": note})
        msg = f"✅ <b>{verb} revenue stream:</b> {tg._esc(stream)}\n  {extra}"
        if note:
            msg += f"\n  <i>{tg._esc(note)}</i>"
        return msg

    return f"⚠️ Unknown /money add kind: <code>{tg._esc(kind)}</code> (try <b>cost</b> or <b>revenue</b>)"


async def _money_note(text: str) -> str:
    """Free-text money note. Captures to brain + queues a Curator proposal."""
    _money_audit("note", {"text": text[:500]})

    # Try to write a Curator Queue proposal so it surfaces in /pending and /decisions.
    queued = False
    queue_err = ""
    try:
        from .proposals import Proposal, ProposalWriter
        async with AppFlowy() as af:
            writer = ProposalWriter(af)
            p = Proposal(
                proposal=f"💰 Money note: {text[:160]}",
                type="money-note",
                confidence_score=0.5,
                proposed_by="tgbot:/money",
                reasoning=("User-submitted free-text money note via /money command. "
                           "Review and decide whether to set/add a ledger entry "
                           "(/money set <id> <amount> or /money add cost/revenue ...)."),
                diff={"raw_text": text, "kind": "free-text-money-note"},
            )
            await writer.write(p, auto_apply=False)
            queued = True
    except Exception as e:
        queue_err = str(e)
        log.warning("money-note queue failed: %s", e)

    lines = ["📝 <b>Money note captured</b>"]
    lines.append(f"<i>{tg._esc(text[:300])}</i>\n")
    if queued:
        lines.append("✅ Queued to Curator Queue (will surface in <code>/decisions</code> and <code>/pending</code>).")
    else:
        lines.append(f"⚠️ Curator Queue write failed: <i>{tg._esc(queue_err[:140])}</i>")
        lines.append(f"Audit log still recorded at <code>{tg._esc(_MONEY_AUDIT_PATH)}</code>.")
    lines.append("\n<b>Apply directly</b>: <code>/money set &lt;id&gt; &lt;amount&gt;</code> or <code>/money add cost/revenue …</code>")
    return "\n".join(lines)


async def _money_view() -> str:
    """Cross-system money view from Chief of Staff (loopback on brain server)."""
    import httpx as _httpx
    cos_url = _os.environ.get("CHIEF_OF_STAFF_URL", "http://127.0.0.1:8107")
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"{cos_url}/money", headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return (f"💰 <b>Money</b>\n\n"
                f"<i>Chief of Staff at {tg._esc(cos_url)} unreachable: {tg._esc(str(e))}</i>")

    costs = data.get("costs", []) or []
    revenue = data.get("revenue", []) or []
    total_cost = float(data.get("total_cost_monthly_usd") or sum(float(c.get("monthly_usd", 0) or 0) for c in costs))
    total_rev = float(data.get("total_revenue_monthly_usd") or 0)

    # Take-home: revenue × per-stream take_home_pct (default 1.0 if not set).
    # Pull take_home_pct from the underlying ledger.json since chief-of-staff
    # may not surface it.
    pct_by_stream: dict[str, float] = {}
    try:
        ledger_raw = _money_load_ledger()
        for k, v in (ledger_raw.get("revenue_monthly") or {}).items():
            pct_by_stream[k] = float(v.get("take_home_pct", 1.0) or 1.0)
    except Exception:
        pass
    take_home_total = 0.0
    for r in revenue:
        stream = r.get("stream") or ""
        rev_usd = float(r.get("revenue_usd", 0) or 0)
        pct = pct_by_stream.get(stream, 1.0)
        take_home_total += rev_usd * pct
    net_take_home = take_home_total - total_cost

    lines = ["💰 <b>Money — current resources by source</b>\n"]
    lines.append(f"<b>Gross revenue:</b> ${total_rev:,.0f}/mo  ·  <b>Costs:</b> ${total_cost:,.0f}/mo")
    lines.append(f"<b>Take-home:</b> ${take_home_total:,.0f}/mo (after payroll/COGS)  ·  <b>Net to James:</b> <b>${net_take_home:+,.0f}/mo</b>\n")

    # Revenue rows
    rev_real = [r for r in revenue if float(r.get("revenue_usd", 0) or 0) > 0]
    if rev_real:
        max_rev = max(float(r.get("revenue_usd", 0) or 0) for r in rev_real)
        lines.append("<b>Revenue streams</b> <i>(gross · take-home)</i>")
        for r in sorted(rev_real, key=lambda x: -float(x.get("revenue_usd", 0) or 0))[:8]:
            stream = r.get("stream") or r.get("name") or "?"
            mo = float(r.get("revenue_usd", 0) or 0)
            pct = pct_by_stream.get(stream, 1.0)
            take = mo * pct
            bar = _money_bar(mo, max_rev)
            tag = f"{int(pct*100)}% take" if pct < 1.0 else "100%"
            lines.append(f"  <code>{bar}</code>  ${mo:,.0f}  →  <b>${take:,.0f}</b>  <i>{tg._esc(tag)}</i>  {tg._esc(stream)}")
        lines.append("")
    else:
        lines.append("<b>Revenue:</b> <i>0 active revenue streams yet.</i>\n")

    if costs:
        max_cost = max(float(c.get("monthly_usd", 0) or 0) for c in costs)
        lines.append("<b>Top costs</b>")
        for c in sorted(costs, key=lambda x: -float(x.get("monthly_usd", 0) or 0))[:8]:
            kill = " 🗑" if c.get("kill_candidate") else ""
            amt = float(c.get('monthly_usd', 0) or 0)
            bar = _money_bar(amt, max_cost)
            lines.append(f"  <code>{bar}</code>  ${amt:,.0f}  {tg._esc(c.get('name','?'))}{kill}")

    biggest_leak = data.get("biggest_leak")
    if biggest_leak:
        lines.append(f"\n<b>🔧 Biggest leak:</b> {tg._esc(biggest_leak.get('name','?'))} (${float(biggest_leak.get('monthly_usd',0)):,.0f}/mo)")

    # Liquid + runway summary inline
    try:
        ledger_raw = _money_load_ledger()
        liq = ledger_raw.get("liquid_assets")
        if liq:
            confirmed, pending = _money_liquid_totals(liq)
            lines.append(f"\n<b>💵 Liquid:</b> ${confirmed:,.0f} confirmed"
                         + (f" (+ ${pending:,.0f} pending)" if pending > 0 else ""))
            if total_cost > 0:
                runway_no_rev = confirmed / total_cost
                if take_home_total >= total_cost:
                    lines.append(f"<b>Runway:</b> infinite (take-home ≥ costs)  ·  if revenue stops: {runway_no_rev:.0f} months")
                else:
                    burn = total_cost - take_home_total
                    runway_with_rev = confirmed / burn
                    lines.append(f"<b>Runway:</b> {runway_with_rev:.0f}mo at current take-home  ·  {runway_no_rev:.0f}mo if revenue stops")
            lines.append("<i>/money liquid for breakdown by account</i>")
        trades = ledger_raw.get("trades", [])
        open_trades = [t for t in trades if t.get("status") == "open"]
        if open_trades:
            total_basis = sum(float(t.get("qty", 0) or 0) * float(t.get("entry_price", 0) or 0) for t in open_trades)
            lines.append(f"\n<b>📈 Open trades:</b> {len(open_trades)} positions · cost basis ${total_basis:,.0f}")
            lines.append("<i>/money trades for per-position detail</i>")
    except Exception as e:
        log.warning("liquid summary failed: %s", e)

    # OneBPO / Cora Nation contribution highlight
    try:
        pl = ledger_raw.get("business_pl")
        if pl and pl.get("monthly"):
            latest = pl["monthly"][-1]
            cora_total = float(pl.get("cora_nation_contribution_total_usd", 0) or 0)
            cora_latest = float(latest.get("cora_nation_contribution_usd", 0) or 0)
            lines.append(f"\n<b>🌿 OneBPO mission flow</b> — Cora Nation contribution {tg._esc(latest.get('month','?'))}: ${cora_latest:,.0f} · cumulative: ${cora_total:,.0f}")
            lines.append("<i>/money onebpo for full P&L</i>")
    except Exception:
        pass

    lines.append("\n<i>Source: Chief of Staff /money + ledger.json · loopback 127.0.0.1:8107</i>")
    lines.append("<i>Modify: /money set / set-balance / add / trade / liquid · /money &lt;free text&gt;</i>")
    return "\n".join(lines)




def _money_liquid_totals(liq: dict) -> tuple[float, float]:
    confirmed = 0.0
    pending = 0.0
    for g in liq.get("groups", []):
        for a in g.get("accounts", []):
            bal = float(a.get("balance_usd", 0) or 0)
            if a.get("pending"):
                pending += bal
            else:
                confirmed += bal
    return confirmed, pending


async def _money_liquid_view() -> str:
    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"\U0001F4B5 <b>Liquid</b>\n\n<i>ledger unreachable: {tg._esc(str(e))}</i>"
    liq = ledger.get("liquid_assets")
    if not liq:
        return ("\U0001F4B5 <b>Liquid</b>\n\n"
                "<i>No liquid_assets section in ledger.json. Use "
                "<code>/money set-balance &lt;account-id&gt; &lt;amount&gt;</code> to seed.</i>")
    confirmed, pending = _money_liquid_totals(liq)
    as_of = liq.get("as_of", "?")
    lines = [
        f"\U0001F4B5 <b>Liquid balances</b> <i>(as of {tg._esc(as_of)})</i>\n",
        f"<b>Confirmed:</b> ${confirmed:,.0f}"
        + (f"  ·  <b>Pending:</b> ${pending:,.0f}  ·  <b>Total:</b> ${confirmed+pending:,.0f}" if pending > 0 else ""),
        "",
    ]
    all_accts = []
    for g in liq.get("groups", []):
        for a in g.get("accounts", []):
            all_accts.append(a)
    max_bal = max((float(a.get("balance_usd", 0) or 0) for a in all_accts), default=1.0)

    for g in liq.get("groups", []):
        accts = g.get("accounts", [])
        group_total = sum(float(a.get("balance_usd", 0) or 0) for a in accts if not a.get("pending"))
        group_pending = sum(float(a.get("balance_usd", 0) or 0) for a in accts if a.get("pending"))
        est = g.get("estimated_total_usd")
        est_str = f" <i>(est: ${est:,.0f})</i>" if est else ""
        head = f"<b>\U0001F4C1 {tg._esc(g.get('name','?'))}</b> — ${group_total:,.0f}"
        if group_pending > 0:
            head += f" + ${group_pending:,.0f} pending"
        head += est_str
        lines.append(head)
        for a in sorted(accts, key=lambda x: -float(x.get("balance_usd", 0) or 0)):
            bal = float(a.get("balance_usd", 0) or 0)
            bar = _money_bar(bal, max_bal, width=10)
            tag = " <i>pending</i>" if a.get("pending") else ""
            lines.append(f"  <code>{bar}</code>  ${bal:,.2f}  {tg._esc(a.get('name','?'))}{tag}  <code>{tg._esc(a.get('id','?'))}</code>")
        lines.append("")

    lines.append("<i>Modify: /money set-balance &lt;account-id&gt; &lt;amount&gt;</i>")
    return "\n".join(lines)


async def _money_set_balance(arg: str) -> str:
    parts = arg.split(maxsplit=1)
    if len(parts) < 2:
        return ("Usage: <code>/money set-balance &lt;account-id&gt; &lt;amount&gt;</code>\n"
                "Example: <code>/money set-balance macu-cn 73000</code>\n"
                "Run <code>/money liquid</code> to see all account ids.")
    acct_id = parts[0]
    try:
        amount = float(parts[1].lstrip("$").replace(",", ""))
    except ValueError:
        return f"⚠️ amount must be a number (got <code>{tg._esc(parts[1])}</code>)"

    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"⚠️ ledger unreachable: {tg._esc(str(e))}"
    liq = ledger.get("liquid_assets")
    if not liq:
        return "⚠️ no liquid_assets section in ledger.json yet."

    target = None
    target_group = None
    for g in liq.get("groups", []):
        for a in g.get("accounts", []):
            if a.get("id") == acct_id:
                target = a
                target_group = g
                break
        if target:
            break
    if not target:
        ids = []
        for g in liq.get("groups", []):
            ids += [a.get("id", "?") for a in g.get("accounts", [])]
        return f"⚠️ account <code>{tg._esc(acct_id)}</code> not found.\nKnown ids: <code>{tg._esc(', '.join(ids))}</code>"

    old = float(target.get("balance_usd", 0) or 0)
    target["balance_usd"] = amount
    from datetime import datetime as _dt7
    liq["as_of"] = _dt7.utcnow().strftime("%Y-%m-%d")
    ledger["last_updated"] = liq["as_of"]
    try:
        _money_save_ledger(ledger)
    except Exception as e:
        return f"⚠️ ledger save failed: {tg._esc(str(e))}"
    _money_audit("set_balance", {"id": acct_id, "old": old, "new": amount,
                                  "group": target_group.get("id") if target_group else None})

    delta = amount - old
    sign = "+" if delta >= 0 else ""
    # Emit money ping for the change.
    asyncio.create_task(_money_ping(
        "💵", "Balance updated",
        f"{target.get('name', acct_id)}: ${old:,.2f} → ${amount:,.2f} ({sign}${delta:,.2f})",
    ))
    return (f"✅ <b>Balance updated:</b> {tg._esc(target.get('name', acct_id))}\n"
            f"  ${old:,.2f} → <b>${amount:,.2f}</b>  ({sign}${delta:,.2f})\n"
            f"  group: {tg._esc(target_group.get('name','?')) if target_group else '?'}")


async def _money_trade(arg: str) -> str:
    """Open a trade. Format: <symbol> <side> <qty> [Nx] @ <price> [from <wallet>] [note]

    Examples:
      /money trade BTC long 0.5 @ 65000 spot DCA
      /money trade BTC short 1.205 3x @ 79650 from BTR $32K margin
      /money trade SOL short 100 5x @ 90 from kucoin perp
    """
    import re as _re
    if not arg.strip():
        return (
            "Usage: <code>/money trade &lt;sym&gt; &lt;side&gt; &lt;qty&gt; [Nx] @ &lt;price&gt; [from &lt;wallet&gt;] [note]</code>\n"
            "Examples:\n"
            "  <code>/money trade BTC long 0.5 @ 65000 sweep entry</code>\n"
            "  <code>/money trade BTC short 1.205 3x @ 79650 from BTR $32K margin</code>\n"
            "Sides: <b>long</b> | <b>short</b>. Leverage <code>Nx</code> optional (default 1x = spot).\n"
            "Wallet: optional <code>from &lt;id&gt;</code> ties this position to a liquid-asset account."
        )

    # Parse: symbol, side, qty, optional leverage (Nx), price, optional "from <wallet>" + note
    pattern = (
        r"^\s*(\S+)\s+"                 # 1: symbol
        r"(long|short|buy|sell)\s+"     # 2: side
        r"([\d.]+)\s*"                  # 3: qty
        r"(?:([\d.]+)x\s+)?"            # 4: optional leverage (e.g., 3x)
        r"@\s*\$?([\d.,]+)\s*"          # 5: price
        r"(.*)$"                        # 6: rest (may contain "from <wallet>" + note)
    )
    m = _re.match(pattern, arg, _re.IGNORECASE)
    if not m:
        return "⚠️ Couldn't parse. Use: <code>/money trade &lt;sym&gt; &lt;side&gt; &lt;qty&gt; [Nx] @ &lt;price&gt; [from &lt;wallet&gt;] [note]</code>"
    symbol = m.group(1).upper()
    side = "long" if m.group(2).lower() in ("long", "buy") else "short"
    try:
        qty = float(m.group(3))
        leverage = float(m.group(4)) if m.group(4) else 1.0
        price = float(m.group(5).replace(",", ""))
    except ValueError:
        return "⚠️ qty, leverage, and price must be numbers"
    rest = (m.group(6) or "").strip()

    wallet_id = ""
    note = rest
    wm = _re.match(r"^from\s+(\S+)\s*(.*)$", rest, _re.IGNORECASE)
    if wm:
        wallet_id = wm.group(1)
        note = wm.group(2).strip()

    notional = qty * price
    margin = notional / leverage if leverage else notional

    from datetime import datetime as _dt8
    import secrets as _sec
    trade_id = f"t-{_dt8.utcnow().strftime('%Y%m%d')}-{_sec.token_hex(3)}"
    trade = {
        "id": trade_id, "symbol": symbol, "side": side, "qty": qty,
        "leverage": leverage,
        "entry_price": price,
        "notional_usd": notional,
        "margin_usd": margin,
        "wallet_id": wallet_id,
        "entry_at": _dt8.utcnow().isoformat() + "Z",
        "status": "open", "note": note,
    }

    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"⚠️ ledger unreachable: {tg._esc(str(e))}"
    trades = ledger.setdefault("trades", [])
    trades.append(trade)
    ledger["last_updated"] = _dt8.utcnow().strftime("%Y-%m-%d")
    try:
        _money_save_ledger(ledger)
    except Exception as e:
        return f"⚠️ ledger save failed: {tg._esc(str(e))}"
    _money_audit("trade_open", trade)

    lev_str = f" {leverage:g}x" if leverage and leverage != 1 else " spot"
    wallet_str = f"\n  wallet: <code>{tg._esc(wallet_id)}</code>" if wallet_id else ""
    return (f"\U0001F4C8 <b>Trade opened:</b> {tg._esc(symbol)} {side}{lev_str} {qty} @ ${price:,.2f}\n"
            f"  notional: ${notional:,.2f}  ·  margin: ${margin:,.2f}\n"
            f"  id: <code>{tg._esc(trade_id)}</code>"
            + wallet_str
            + (f"\n  <i>{tg._esc(note)}</i>" if note else "")
            + f"\n\n<i>/money trades for live P/L</i>")


async def _money_trades_view() -> str:
    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"\U0001F4C8 <b>Trades</b>\n\n<i>ledger unreachable: {tg._esc(str(e))}</i>"
    trades = ledger.get("trades", [])
    open_trades = [t for t in trades if t.get("status") == "open"]
    closed_trades = [t for t in trades if t.get("status") == "closed"]
    if not trades:
        return ("\U0001F4C8 <b>Trades</b>\n\n"
                "<i>No trades recorded yet. Use:</i>\n"
                "<code>/money trade BTC long 0.5 @ 65000 sweep entry</code>\n"
                "<code>/money trade BTC short 1.205 3x @ 79650 from BTR</code> <i>(leveraged)</i>")

    prices = await _fetch_live_prices() if open_trades else {}

    lines = [f"\U0001F4C8 <b>Trades</b> — {len(open_trades)} open, {len(closed_trades)} closed\n"]
    if open_trades:
        lines.append("<b>Open positions</b>")
        total_margin = 0.0
        total_pl = 0.0
        for t in open_trades:
            sym = t.get("symbol", "?")
            side = t.get("side", "?")
            qty = float(t.get("qty", 0) or 0)
            entry = float(t.get("entry_price", 0) or 0)
            leverage = float(t.get("leverage", 1) or 1)
            margin = float(t.get("margin_usd") or (qty * entry / leverage if leverage else qty * entry))
            notional = float(t.get("notional_usd") or (qty * entry))
            wallet = t.get("wallet_id") or ""
            total_margin += margin

            arrow = "↗" if side == "long" else "↘"
            lev_str = f" {leverage:g}x" if leverage and leverage != 1 else ""
            head = (f"  {arrow} <b>{tg._esc(sym)}</b> {tg._esc(side)}{lev_str} "
                    f"{qty} @ ${entry:,.2f}")
            lines.append(head)

            current = prices.get(sym.upper())
            if current is not None:
                if side == "long":
                    pnl = (current - entry) * qty
                else:
                    pnl = (entry - current) * qty
                total_pl += pnl
                pl_pct_notional = (pnl / notional * 100) if notional else 0
                pl_pct_margin = (pnl / margin * 100) if margin else 0
                pnl_glyph = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")
                pnl_sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"     {pnl_glyph} mark ${current:,.2f}  ·  "
                    f"P/L <b>{pnl_sign}${pnl:,.0f}</b> "
                    f"({pnl_sign}{pl_pct_notional:.1f}% notional, "
                    f"{pnl_sign}{pl_pct_margin:.1f}% margin)"
                )
            else:
                lines.append(f"     ⚪ <i>no live price for {tg._esc(sym)} (not in WhaleTrack feed)</i>")
            meta = f"     notional ${notional:,.0f} · margin ${margin:,.0f}"
            if wallet:
                meta += f" · from <code>{tg._esc(wallet)}</code>"
            meta += f" · <code>{tg._esc(t.get('id','?'))}</code>"
            lines.append(meta)
            if t.get("note"):
                lines.append(f"     <i>{tg._esc(t['note'][:120])}</i>")

        if total_margin > 0:
            sign = "+" if total_pl >= 0 else ""
            pct = (total_pl / total_margin * 100) if total_margin else 0
            lines.append(f"\n<b>Totals:</b> margin ${total_margin:,.0f} · "
                         f"P/L <b>{sign}${total_pl:,.0f}</b> ({sign}{pct:.1f}% on margin)")
        if not prices:
            lines.append("<i>(live-price fetch from WhaleTrack failed — P/L not computed)</i>")

    if closed_trades:
        lines.append(f"\n<b>Recently closed</b> ({len(closed_trades)})")
        for t in sorted(closed_trades, key=lambda x: x.get("closed_at", ""), reverse=True)[:5]:
            sym = t.get("symbol", "?")
            pl = float(t.get("realized_pl_usd", 0) or 0)
            sign = "+" if pl >= 0 else ""
            lines.append(f"  {tg._esc(sym)} {sign}${pl:,.0f}  <code>{tg._esc(t.get('id','?'))}</code>")
    return "\n".join(lines)


async def _fetch_live_prices() -> dict[str, float]:
    """Pull current prices for open trade symbols from WhaleTrack /api/recommendations.

    Returns a dict of UPPERCASE_SYMBOL -> current_price. Best-effort; on failure
    returns {}. Also reads BTC anchor.price as a backup BTC source.
    """
    import httpx as _httpx
    wt_base = _os.environ.get("WHALETRACK_PUBLIC_BASE", "https://fullpotential.ai/dashboards/whaletrack")
    out: dict[str, float] = {}
    try:
        async with _httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"{wt_base}/api/recommendations")
            r.raise_for_status()
            data = r.json()
        anchor = data.get("btc_anchor") or {}
        if anchor.get("price"):
            try:
                out["BTC"] = float(anchor["price"])
            except Exception:
                pass
        for rec in data.get("recommendations") or []:
            sym = (rec.get("symbol") or "").upper()
            cp = rec.get("current_price")
            if sym and cp is not None:
                try:
                    out[sym] = float(cp)
                except Exception:
                    pass
    except Exception as e:
        log.warning("/money trades live-price fetch failed: %s", e)
    return out


async def _money_trade_close(arg: str) -> str:
    """Close an open trade. Usage:
       /money trade close <id> [@ <exit_price>] [note]

    If no exit price supplied, uses the live mark from WhaleTrack.
    Computes realized P/L = (mark-entry)*qty for long, (entry-mark)*qty for short.
    Sets status='closed', exit_price, closed_at, realized_pl_usd."""
    import re as _re
    arg = (arg or "").strip()
    if not arg:
        return ("Usage: <code>/money trade close &lt;id&gt; [@ &lt;exit_price&gt;] [note]</code>\n"
                "Example: <code>/money trade close t-20260508-58fdcc @ 80000 took profit</code>\n"
                "If you omit the price, the live WhaleTrack mark is used.")

    m = _re.match(r"^\s*(\S+)(?:\s*@\s*\$?([\d.,]+))?\s*(.*)$", arg)
    if not m:
        return "⚠️ Couldn't parse. Use: <code>/money trade close &lt;id&gt; [@ &lt;exit_price&gt;] [note]</code>"
    trade_id = m.group(1).strip()
    exit_price_arg = m.group(2)
    close_note = (m.group(3) or "").strip()

    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"⚠️ ledger unreachable: {tg._esc(str(e))}"
    trades = ledger.get("trades", [])
    target = next((t for t in trades if t.get("id") == trade_id), None)
    if target is None:
        return f"⚠️ No trade with id <code>{tg._esc(trade_id)}</code>. <code>/money trades</code> to list."
    if target.get("status") == "closed":
        return f"⚠️ Trade <code>{tg._esc(trade_id)}</code> is already closed."

    sym = (target.get("symbol") or "").upper()
    entry = float(target.get("entry_price") or 0)
    qty = float(target.get("qty") or 0)
    side = target.get("side") or "long"

    if exit_price_arg:
        try:
            exit_price = float(exit_price_arg.replace(",", ""))
        except ValueError:
            return "⚠️ exit_price must be a number"
        price_source = "manual"
    else:
        prices = await _fetch_live_prices()
        if sym not in prices:
            return (f"⚠️ No live mark for {tg._esc(sym)} (not in WhaleTrack feed). "
                    f"Specify exit price: <code>/money trade close {tg._esc(trade_id)} @ &lt;price&gt;</code>")
        exit_price = prices[sym]
        price_source = "live mark from WhaleTrack"

    if side == "long":
        pnl = (exit_price - entry) * qty
    else:
        pnl = (entry - exit_price) * qty

    from datetime import datetime as _dt9
    target["status"] = "closed"
    target["exit_price"] = exit_price
    target["closed_at"] = _dt9.utcnow().isoformat() + "Z"
    target["realized_pl_usd"] = pnl
    if close_note:
        target["close_note"] = close_note
    ledger["last_updated"] = _dt9.utcnow().strftime("%Y-%m-%d")
    try:
        _money_save_ledger(ledger)
    except Exception as e:
        return f"⚠️ ledger save failed: {tg._esc(str(e))}"
    _money_audit("trade_close", {"id": trade_id, "exit_price": exit_price, "realized_pl_usd": pnl, "source": price_source})

    notional = float(target.get("notional_usd") or qty * entry)
    margin = float(target.get("margin_usd") or notional)
    pct_notional = (pnl / notional * 100) if notional else 0
    pct_margin = (pnl / margin * 100) if margin else 0
    glyph = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")
    sign = "+" if pnl >= 0 else ""
    return (
        f"\U0001F4C8 <b>Trade closed:</b> {tg._esc(sym)} {tg._esc(side)} "
        f"{qty} @ entry ${entry:,.2f} → exit ${exit_price:,.2f}\n"
        f"  {glyph} Realized P/L <b>{sign}${pnl:,.0f}</b> "
        f"({sign}{pct_notional:.2f}% notional, {sign}{pct_margin:.2f}% margin)\n"
        f"  id: <code>{tg._esc(trade_id)}</code> · price: <i>{tg._esc(price_source)}</i>"
        + (f"\n  <i>{tg._esc(close_note)}</i>" if close_note else "")
    )


async def _money_trade_delete(arg: str) -> str:
    """Delete a trade entirely (typo correction). Usage:
       /money trade delete <id>

    Removes the record from the ledger. Audit-logged. Use 'close' instead
    when you actually exited the position — delete is for fixing mistakes."""
    trade_id = (arg or "").strip().split()[0] if arg.strip() else ""
    if not trade_id:
        return ("Usage: <code>/money trade delete &lt;id&gt;</code>\n"
                "Use this for typo-correction. To exit a position, use "
                "<code>/money trade close</code> instead so realized P/L is logged.")
    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"⚠️ ledger unreachable: {tg._esc(str(e))}"
    trades = ledger.get("trades", [])
    target = next((t for t in trades if t.get("id") == trade_id), None)
    if target is None:
        return f"⚠️ No trade with id <code>{tg._esc(trade_id)}</code>. <code>/money trades</code> to list."
    ledger["trades"] = [t for t in trades if t.get("id") != trade_id]
    from datetime import datetime as _dt10
    ledger["last_updated"] = _dt10.utcnow().strftime("%Y-%m-%d")
    try:
        _money_save_ledger(ledger)
    except Exception as e:
        return f"⚠️ ledger save failed: {tg._esc(str(e))}"
    _money_audit("trade_delete", {"id": trade_id, "deleted_record": target})
    sym = target.get("symbol", "?")
    side = target.get("side", "?")
    qty = target.get("qty", "?")
    return (
        f"🗑 <b>Trade deleted:</b> {tg._esc(sym)} {tg._esc(side)} {qty} "
        f"<code>{tg._esc(trade_id)}</code>\n"
        f"<i>Audit-logged. Original record preserved in money_edits.jsonl.</i>"
    )


# ───────────────────────────── money pings ──────────────────────────────
# Generic ping helper. Any process (Telegram bot, future Stripe webhook,
# bank-sync job, receipt OCR pipeline, sibling agent) can call _money_ping
# to push a money-event notification to the owner.
#
# Categories that ping by default:
#   - trade_open / trade_close
#   - set_balance (account balance changes)
#   - add_revenue (new revenue stream)
# Categories that do NOT ping (already loud via chat reply):
#   - set (cost update via /money set)
#   - add_cost
#   - note (free-text)
#
# To toggle: future /money pings on|off command writes to a config file
# read here. For now, always-on for the categories above.

async def _money_ping(emoji: str, headline: str, detail: str = "") -> None:
    """Send a money-event ping to the owner. Best-effort, silent failure."""
    try:
        msg = f"{emoji} <b>{tg._esc(headline)}</b>"
        if detail:
            msg += f"\n{tg._esc(detail)}"
        msg += "\n<i>(money ping · /money for full view)</i>"
        await tg.send(msg)
    except Exception as e:
        log.warning("money ping failed: %s", e)


def _money_ping_audit_filter(action: str) -> tuple[str, str] | None:
    """Decide whether an audit action triggers a ping. Returns (emoji, headline) or None."""
    table = {
        "set_balance": ("💵", "Balance updated"),
        "trade_open": ("📈", "Trade opened"),
        "trade_close": ("📉", "Trade closed"),
        "add_revenue": ("✨", "New revenue stream"),
        "update_revenue": ("💰", "Revenue updated"),
    }
    return table.get(action)



async def _money_onebpo_view() -> str:
    """OneBPO Managed Services P&L + Cora Nation contribution timeline."""
    try:
        ledger = _money_load_ledger()
    except Exception as e:
        return f"📊 <b>OneBPO P&L</b>\n\n<i>ledger unreachable: {tg._esc(str(e))}</i>"
    pl = ledger.get("business_pl")
    if not pl:
        return "📊 <b>OneBPO P&L</b>\n\n<i>No business_pl section in ledger.json.</i>"
    months = pl.get("monthly", [])
    if not months:
        return "📊 <b>OneBPO P&L</b>\n\n<i>No monthly data.</i>"

    lines = [f"📊 <b>{tg._esc(pl.get('company','OneBPO'))} P&L</b>"]
    lines.append(f"<i>as of {tg._esc(pl.get('as_of','?'))}</i>\n")

    total_rev = sum(float(m.get("operating_income_usd", 0) or 0) for m in months)
    total_op = sum(float(m.get("operating_profit_usd", 0) or 0) for m in months)
    total_net = sum(float(m.get("net_profit_usd", 0) or 0) for m in months)
    total_cora = float(pl.get("cora_nation_contribution_total_usd", 0) or 0)
    period = f"{months[0].get('month','?')} → {months[-1].get('month','?')}"

    lines.append(f"<b>Period totals</b> ({tg._esc(period)})")
    lines.append(f"  Revenue: <b>${total_rev:,.0f}</b>")
    lines.append(f"  Operating profit: <b>${total_op:,.0f}</b>")
    lines.append(f"  Net profit: <b>${total_net:,.0f}</b>")
    lines.append(f"  🌿 <b>Cora Nation contribution: ${total_cora:,.0f}</b>")
    lines.append("")

    formula = pl.get("formula") or {}
    if formula.get("description"):
        lines.append(f"<b>Formula:</b> <i>{tg._esc(formula['description'])}</i>")
        lines.append("")

    lines.append("<b>Monthly</b>")
    for m in months:
        rev = float(m.get("operating_income_usd", 0) or 0)
        op = float(m.get("operating_profit_usd", 0) or 0)
        net = float(m.get("net_profit_usd", 0) or 0)
        cora = float(m.get("cora_nation_contribution_usd", 0) or 0)
        avail = float(m.get("implied_available_net_usd", 0) or 0)
        reserve = float(m.get("implied_reserve_usd", 0) or 0)
        other = float(m.get("implied_other_half_usd", 0) or 0)
        lines.append(f"<b>{tg._esc(m.get('month','?'))}</b>")
        lines.append(f"   csv: rev ${rev:,.0f} · op ${op:,.0f} · net ${net:,.0f}")
        if avail > 0:
            lines.append(f"   <i>implied available net</i> <b>${avail:,.0f}</b>  →  reserve ${reserve:,.0f} (10%) + 🌿 cora ${cora:,.0f} (45%) + other ${other:,.0f} (45%)")
        else:
            lines.append(f"   🌿 cora ${cora:,.0f}")

    lines.append("")
    note = pl.get("_note") or pl.get("note")
    if note:
        lines.append(f"<i>{tg._esc(note)}</i>")
    lines.append("<i>Source: ledger.json business_pl</i>")
    return "\n".join(lines)


def _money_bar(value: float, max_value: float, width: int = 12) -> str:
    """Render a simple unicode bar chart cell."""
    if max_value <= 0:
        return " " * width
    filled = int(round((value / max_value) * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


# ───────────────────────────── /log ──────────────────────────────
async def _cmd_log() -> str:
    """Recent AI activity timeline — qb events + NOW.md sync + recent council jobs."""
    import os as _os4
    from datetime import datetime as _dt2
    events_out: list[tuple[str, str]] = []  # (ts, line)

    # qb events (last 10)
    try:
        with open(_QB_BOARD_PATH, encoding="utf-8") as f:
            lines = f.read().splitlines()
        import json as _json
        recent = []
        for ln in lines[-30:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                recent.append(_json.loads(ln))
            except Exception:
                continue
        for ev in recent[-15:]:
            ts = ev.get("ts", "")
            kind = ev.get("event", "?")
            book = ev.get("book", "?")
            text = (ev.get("text") or ev.get("note") or "")[:80]
            icon = {"open": "○", "pulse": "·", "answer": "✓", "block": "⊗", "unblock": "○"}.get(kind, "•")
            events_out.append((ts, f"{icon} qb [{tg._esc(book)}] <i>{tg._esc(kind)}</i> — {tg._esc(text)}"))
    except Exception as e:
        events_out.append(("", f"<i>(qb log unreadable: {tg._esc(str(e)[:80])})</i>"))

    # NOW.md last sync mtime
    try:
        mt = _os4.path.getmtime(_NOW_PATH)
        ts = _dt2.fromtimestamp(mt).strftime("%Y-%m-%dT%H:%M:%SZ")
        events_out.append((ts, f"📝 NOW.md synced from cockpit"))
    except Exception:
        pass

    # Sort by ts descending
    events_out.sort(key=lambda t: t[0], reverse=True)

    lines = ["🕐 <b>Recent activity</b>\n"]
    if not events_out:
        lines.append("<i>No recent activity to surface.</i>")
    else:
        for ts, line in events_out[:15]:
            short_ts = ts[5:16] if ts and len(ts) >= 16 else ""
            lines.append(f"  <code>{short_ts}</code>  {line}")

    lines.append("\n<i>Sources: qb events + NOW.md sync mtime · v1 will add council jobs + treasury txns</i>")
    return "\n".join(lines)


# ───────────────────────────── Linear (Sunheart Flow Spine Phase 2) ─────────────────────────────
# Voice memo → Linear CAPTURED. Added 2026-05-23 per project_sunheart_flow_spine.
# Token at ~/.config/fpai/linear/api.token (mode 600). Defaults map to Full Potential AI team FUL.
_LINEAR_TOKEN_PATH = os.environ.get(
    "LINEAR_API_TOKEN_PATH",
    str(Path.home() / ".config" / "fpai" / "linear" / "api.token"),
)
_LINEAR_TEAM_ID = os.environ.get("LINEAR_TEAM_ID", "44963b86-9bc7-4cc1-8440-d094711408f8")
_LINEAR_CAPTURED_STATE_ID = os.environ.get(
    "LINEAR_CAPTURED_STATE_ID", "18529b8e-7c40-4e6d-9e36-d7e5082acfe1"
)
_LINEAR_API = "https://api.linear.app/graphql"
_LINEAR_LABEL_CACHE: dict[str, str] = {}


def _linear_token() -> str | None:
    try:
        return Path(_LINEAR_TOKEN_PATH).expanduser().read_text().strip() or None
    except Exception:
        return None


async def _linear_label_lookup() -> dict[str, str]:
    """Fetch labels once · cache name→id. Returns empty dict on failure."""
    global _LINEAR_LABEL_CACHE
    if _LINEAR_LABEL_CACHE:
        return _LINEAR_LABEL_CACHE
    token = _linear_token()
    if not token:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as cli:
            r = await cli.post(
                _LINEAR_API,
                headers={"Authorization": token, "Content-Type": "application/json"},
                json={
                    "query": '{ issueLabels(filter: {team: {id: {eq: "'
                    + _LINEAR_TEAM_ID
                    + '"}}}) { nodes { id name } } }'
                },
            )
            data = (r.json() or {}).get("data", {}) or {}
            for n in (data.get("issueLabels", {}) or {}).get("nodes", []):
                _LINEAR_LABEL_CACHE[n["name"]] = n["id"]
    except Exception as e:
        log.warning("linear label lookup failed: %s", e)
    return _LINEAR_LABEL_CACHE


async def _linear_capture(transcript: str, from_name: str = "James") -> str | None:
    """Post transcript to Linear CAPTURED. Returns TG reply string with URL · None on failure.

    Voice-prefix detection:
      'rapid:' / 'urgent:' → ⚡ Rapid Current (default)
      'active:' / 'flow:'  → 🌀 Active Flow
      'slow:'  / 'later:'  → 🍃 Slow River
      'dormant:' / 'park:' / 'someday:' → 💤 Dormant Pool
    """
    token = _linear_token()
    if not token:
        log.warning("linear: no token at %s · skipping capture", _LINEAR_TOKEN_PATH)
        return None

    t = (transcript or "").strip()
    lower = t.lower()
    label_name = "⚡ Rapid Current"
    body = t
    prefix_map = [
        (("rapid:", "urgent:"), "⚡ Rapid Current"),
        (("active:", "flow:"), "🌀 Active Flow"),
        (("slow:", "later:"), "🍃 Slow River"),
        (("dormant:", "park:", "someday:"), "💤 Dormant Pool"),
    ]
    for prefixes, label in prefix_map:
        for p in prefixes:
            if lower.startswith(p):
                label_name = label
                body = t[len(p):].strip()
                break
        if label_name != "⚡ Rapid Current" or body != t:
            break

    title_prefix = "" if from_name == "James" else f"[{from_name}] "
    title = (title_prefix + (body.split("\n")[0][:80].strip())) or "(voice capture)"
    description = (
        f"Captured from {from_name} via @sunheartbrain_bot\n\n"
        f"---\n\n{transcript}\n\n"
        f"---\n_Captured by Sunheart Flow Spine Phase 2 wire ·"
        f" {datetime.now(timezone.utc).isoformat()}_"
    )

    labels = await _linear_label_lookup()
    label_id = labels.get(label_name)

    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { identifier url }
      }
    }
    """
    variables: dict = {
        "input": {
            "teamId": _LINEAR_TEAM_ID,
            "stateId": _LINEAR_CAPTURED_STATE_ID,
            "title": title,
            "description": description,
        }
    }
    if label_id:
        variables["input"]["labelIds"] = [label_id]

    try:
        async with httpx.AsyncClient(timeout=15.0) as cli:
            r = await cli.post(
                _LINEAR_API,
                headers={"Authorization": token, "Content-Type": "application/json"},
                json={"query": mutation, "variables": variables},
            )
            data = (r.json() or {}).get("data", {}) or {}
            iss = ((data.get("issueCreate") or {}).get("issue")) or {}
            if iss.get("url"):
                return (
                    f"🌊 <b>Captured in the river</b> · "
                    f"<a href=\"{iss['url']}\">{iss['identifier']}</a> · "
                    f"<i>{tg._esc(label_name)}</i>"
                )
    except Exception as e:
        log.warning("linear capture failed: %s", e)
    return None


async def _transcribe_voice(file_id: str) -> str | None:
    """Telegram voice file_id → OpenAI Whisper transcript. None on failure."""
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key or not tg.BOT_TOKEN:
        log.warning("voice: OPENAI_API_KEY or TELEGRAM_BOT_TOKEN missing")
        return None
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{tg.BOT_TOKEN}/getFile",
                params={"file_id": file_id},
            )
            r.raise_for_status()
            file_path = r.json()["result"]["file_path"]
            r = await client.get(
                f"https://api.telegram.org/file/bot{tg.BOT_TOKEN}/{file_path}"
            )
            r.raise_for_status()
            audio_bytes = r.content
            r = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {openai_key}"},
                files={"file": ("voice.ogg", audio_bytes, "audio/ogg")},
                data={"model": "whisper-1"},
            )
            r.raise_for_status()
            return (r.json().get("text") or "").strip() or None
    except Exception as e:
        log.exception("voice transcription failed: %s", e)
        return None


# ───────────────────────────── voice OUT (TTS) ─────────────────────────────
# Reply-to-voice behavior is opt-out per James 2026-05-21:
#   - Inbound voice → always reply with voice (and text).
#   - EMBER_TGBOT_VOICE_DISABLE=1 env or voice_disable.lock file → text-only fallback.
#   - Long replies get truncated for TTS (full text still sent as a normal message).

_VOICE_DISABLE_LOCK = Path(
    os.environ.get(
        "EMBER_TGBOT_VOICE_LOCK",
        "/var/lib/sh-brain/voice_disable.lock",
    )
)
_TTS_MODEL = os.environ.get("SH_TGBOT_TTS_MODEL", "tts-1")  # tts-1 (fast/cheap) or tts-1-hd
_TTS_VOICE = os.environ.get("SH_TGBOT_TTS_VOICE", "nova")    # alloy/echo/fable/onyx/nova/shimmer
_TTS_MAX_CHARS = int(os.environ.get("SH_TGBOT_TTS_MAX_CHARS", "1200"))
_TTS_FORMAT = os.environ.get("SH_TGBOT_TTS_FORMAT", "opus")  # opus = OGG/Opus, native TG voice
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _voice_out_enabled() -> bool:
    if os.environ.get("EMBER_TGBOT_VOICE_DISABLE", "").strip() in ("1", "true", "yes"):
        return False
    try:
        if _VOICE_DISABLE_LOCK.exists():
            return False
    except Exception:
        pass
    return True


def _strip_for_tts(html_text: str) -> str:
    """Remove HTML tags + entity-decode + collapse for the speech model.

    Drops citation footers ([N] sources block) and code-fence noise, keeps
    the first paragraph + Next moves bullets. Trims to _TTS_MAX_CHARS.
    """
    if not html_text:
        return ""
    # Cut everything after a "Sources" header — TTS shouldn't read citations.
    cut = re.split(r"\n*<b>\s*Sources\b", html_text, maxsplit=1, flags=re.IGNORECASE)
    text = cut[0]
    # Strip tags
    text = _HTML_TAG_RE.sub("", text)
    # HTML entity decode (we only ever emit &amp; &lt; &gt;)
    text = (text
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#x27;", "'"))
    # Collapse bullet markers + extra whitespace
    text = re.sub(r"^\s*[•\-\*]\s+", ". ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > _TTS_MAX_CHARS:
        text = text[: _TTS_MAX_CHARS - 1].rstrip() + "…"
    return text


async def _synthesize_tts(text: str) -> tuple[bytes, str, str] | None:
    """text → audio bytes via OpenAI TTS. Returns (bytes, mime, ext) or None.

    Format defaults to OGG/Opus so Telegram renders the native voice bubble.
    MP3 fallback is available for environments where Opus encoding is off.
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        log.warning("voice-out: OPENAI_API_KEY missing")
        return None
    speak = _strip_for_tts(text)
    if not speak or len(speak) < 2:
        return None
    fmt = _TTS_FORMAT
    if fmt not in ("opus", "mp3", "aac", "flac", "wav", "pcm"):
        fmt = "opus"
    mime = {"opus": "audio/ogg", "mp3": "audio/mpeg", "aac": "audio/aac",
            "flac": "audio/flac", "wav": "audio/wav", "pcm": "audio/L16"}.get(fmt, "audio/ogg")
    ext = "ogg" if fmt == "opus" else fmt
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _TTS_MODEL,
                    "voice": _TTS_VOICE,
                    "input": speak,
                    "response_format": fmt,
                },
            )
            r.raise_for_status()
            return r.content, mime, ext
    except Exception as e:
        log.exception("voice-out synthesis failed: %s", e)
        return None


async def _send_voice_reply(text: str) -> bool:
    """Synthesize + send a voice reply. Returns True on success.

    Caller controls when this fires (e.g. only when inbound was voice). On any
    failure, returns False — caller already sent the text reply so user still
    gets the answer.
    """
    if not _voice_out_enabled():
        log.info("voice-out disabled (env or lockfile); skipping")
        return False
    synth = await _synthesize_tts(text)
    if not synth:
        return False
    audio, mime, ext = synth
    fname = f"reply.{ext}"
    if mime == "audio/ogg":
        return await tg.send_voice(audio, filename=fname, mime=mime)
    return await tg.send_audio(audio, filename=fname, mime=mime)


async def _handle_message(msg: dict) -> None:
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    from_user = str((msg.get("from") or {}).get("id") or "")
    text = (msg.get("text") or "").strip()
    update_id = msg.get("message_id")  # not the update_id, but unique-ish
    voice_in = False  # Track whether inbound was voice → reply with voice too

    # Identify caller role: owner (full access) · team capture (Linear-only) · stranger (ignored)
    is_owner = bool(OWNER_CHAT_ID) and from_user == OWNER_CHAT_ID
    is_team = _is_team_capture_user(from_user)
    capture_name = TEAM_CAPTURE.get(from_user, "James" if is_owner else "")

    # Voice / audio note → Whisper transcription → Linear (always) → flow as text only for owner.
    if not text and chat_id:
        voice = msg.get("voice") or msg.get("audio")
        if voice:
            if not (is_owner or is_team):
                log.info("ignoring voice from non-authorized user %s", from_user)
                return
            file_id = voice.get("file_id")
            if not file_id:
                return
            await tg.send("🎙️ <i>Transcribing…</i>")
            transcript = await _transcribe_voice(file_id)
            if not transcript:
                await tg.send("⚠️ Couldn't transcribe that voice note.")
                return
            await tg.send(f"🎙️ <b>Heard:</b> <i>{tg._esc(transcript)}</i>")
            text = transcript
            voice_in = True
            # Sunheart Flow Spine Phase 2: drop into Linear CAPTURED (with attribution).
            try:
                linear_reply = await _linear_capture(transcript, from_name=capture_name or "Anonymous")
                if linear_reply:
                    await tg.send(linear_reply)
            except Exception as e:
                log.warning("linear capture wrapper failed: %s", e)
            # Team-capture-only users: stop here. Don't run brain search / slash commands.
            if is_team and not is_owner:
                return

    if not text or not chat_id:
        return

    # Team-capture text-message: also drop to Linear, then stop.
    if is_team and not is_owner:
        if not text.startswith("/"):
            try:
                linear_reply = await _linear_capture(text, from_name=capture_name)
                if linear_reply:
                    await tg.send(linear_reply)
                else:
                    await tg.send("⚠️ Capture failed · text saved for retry.")
            except Exception as e:
                log.warning("team-capture text → linear failed: %s", e)
        else:
            await tg.send(
                "ℹ️ Capture-only access. Send text or voice to drop intent into the river. "
                "Slash commands are owner-only."
            )
        return

    if not is_owner:
        # Self-onboarding: first message from a stranger gets a greeting with
        # their chat_id so they can ask James to add them to TEAM_CAPTURE_USERS.
        # Track greeted strangers to avoid spam.
        _greeted_path = Path("/var/lib/sh-brain/greeted_strangers.txt")
        already_greeted = False
        try:
            _greeted_path.parent.mkdir(parents=True, exist_ok=True)
            if _greeted_path.exists():
                already_greeted = from_user in _greeted_path.read_text().splitlines()
        except Exception:
            pass
        if not already_greeted:
            try:
                first_name = (msg.get("from") or {}).get("first_name") or "there"
                username = (msg.get("from") or {}).get("username") or ""
                user_tag = f"@{username}" if username else ""
                greeting = (
                    f"👋 Hey {tg._esc(first_name)} · welcome to the Sunheart Flow.\n\n"
                    f"<b>Your chat_id:</b> <code>{from_user}</code>\n\n"
                    f"You're not authorized to capture into the river yet. "
                    f"Send this to James to be added:\n\n"
                    f"<i>'Hey James · please add me to the bot · "
                    f"chat_id <code>{from_user}</code> · name &lt;your name&gt;'</i>\n\n"
                    f"Once added · any text or voice memo you send here drops into the team river automatically."
                )
                await tg.send(greeting)
                with _greeted_path.open("a") as f:
                    f.write(from_user + "\n")
            except Exception as e:
                log.warning("stranger greeting failed: %s", e)
        log.info("ignoring message from non-authorized user %s", from_user)
        return

    # james_ask inbound: if this text replies to an open ask, consume it +
    # ack + return. Skip slash-commands (those are explicit non-asks).
    if not text.startswith("/"):
        try:
            matched = await james_ask.try_match_reply(text, message_id=update_id)
        except Exception as e:
            log.warning("james_ask.try_match_reply failed: %s", e)
            matched = None
        if matched:
            ack = (
                f"✅ <b>Logged as your reply to</b> <code>{tg._esc(matched['id'])}</code>\n"
                f"<i>From: {tg._esc(matched.get('from_agent', 'unknown'))}</i>\n"
                f"<i>The asking agent will pick this up on next sweep.</i>"
            )
            try:
                await tg.send(ack)
            except Exception:
                pass
            if voice_in:
                try:
                    await _send_voice_reply(f"Got it · logged as reply to {matched['id']}")
                except Exception:
                    pass
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
            # Speak slash-command replies too when the inbound was voice — the
            # whole point is eyes-closed conversation. Skip for commands that
            # explicitly handle their own messaging (returned None above).
            if voice_in:
                try:
                    await _send_voice_reply(reply)
                except Exception as e:
                    log.warning("voice-out (cmd) failed: %s", e)
        return

    # Plain text path — log inbound, answer, log outbound.
    await _log_tg_message(str(chat_id), "user", text, update_id=update_id)

    log.info("chat: %s", text[:120])
    hits = await _search_brain(text)
    answer_body = _format_answer_for_telegram(await _synthesize_answer(text, hits))
    answer = answer_body
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

    # Voice-out: only when inbound was voice. Speak the answer BODY only
    # (citations live in the text message; speaking [1][2][3] dumps would be
    # noise on the ears). Best-effort — text already delivered.
    if voice_in:
        try:
            await _send_voice_reply(answer_body)
        except Exception as e:
            log.warning("voice-out (chat) failed: %s", e)


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


async def _run_opportunities_async() -> None:
    """Fire-and-forget opportunities scan. The job sends its own Telegram
    message when there's substance; surface only errors here."""
    from .jobs import opportunities as opp
    run_id = uuid.uuid4().hex[:12]
    try:
        row = await opp.run(run_id)
        log.info("opportunities on-demand run=%s silent=%s sent=%s",
                 run_id, row.get("silent"), row.get("sent"))
        if row.get("silent"):
            try:
                await tg.send("🤫 <i>Scan ran. No concrete opportunities surfaced — keeping quiet.</i>")
            except Exception:
                pass
    except Exception as e:
        log.exception("opportunities on-demand failed: %s", e)
        try:
            await tg.send(f"⚠️ Opportunities scan failed: {tg._esc(str(e)[:300])}")
        except Exception:
            pass


# ───────────────────────────── /roi ──────────────────────────────
_ROI_LEDGER_PATH = _os.environ.get("SH_ROI_LEDGER", "/var/lib/sh-brain/roi.jsonl")


async def _cmd_roi() -> str:
    """Render the most recent ROI ledger row.

    Source: /var/lib/sh-brain/roi.jsonl, written nightly by `python -m curator roi`.
    """
    import json as _json
    p = _os.path.abspath(_ROI_LEDGER_PATH)
    if not _os.path.exists(p):
        return ("📈 <b>ROI ledger</b>\n\n"
                f"<i>No ledger yet at <code>{tg._esc(p)}</code>. "
                "Runs nightly via brain-curator-roi.timer; first row appears "
                "after the first scheduled run.</i>")
    last_row = None
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_row = line
        if not last_row:
            return "📈 <b>ROI ledger</b>\n\n<i>Ledger file present but empty.</i>"
        row = _json.loads(last_row)
    except Exception as e:
        return f"📈 <b>ROI ledger</b>\n\n<i>Could not read ledger: {tg._esc(str(e))}</i>"

    bot = row.get("bot_replies_24h", 0)
    james = row.get("james_messages_24h", 0)
    cost = float(row.get("est_cost_usd_24h") or 0)
    cpc = float(row.get("cost_per_call_usd") or 0)
    vp = row.get("value_proxy_james_per_bot_reply")
    alerts = row.get("alerts") or []
    totals = row.get("totals_lifetime") or {}
    date = row.get("date", "?")

    lines = [f"📈 <b>Brain ROI · {tg._esc(date)} (last 24h)</b>\n"]
    lines.append(f"  Bot replies (Claude-call proxy): <b>{bot}</b>")
    lines.append(f"  James messages: <b>{james}</b>")
    lines.append(f"  Est cost: <b>${cost:.2f}</b>  <i>(@ ${cpc:.3f}/call)</i>")
    if vp is not None:
        lines.append(f"  Value proxy (james/reply): <b>{vp}</b>")
    else:
        lines.append("  Value proxy: <i>n/a (no replies)</i>")
    if alerts:
        nice = ", ".join(alerts).replace("_", " ")
        lines.append(f"\n🚨 <b>Alerts:</b> {tg._esc(nice)}")
    if totals:
        lines.append(f"\n<i>Lifetime: {totals.get('bot', 0)} bot · {totals.get('user', 0)} user msgs</i>")
    lines.append(f"<i>Source: {tg._esc(p)}</i>")
    return "\n".join(lines)


# ───────────────────────────── /servers ──────────────────────────────
async def _cmd_servers() -> str:
    """Live server + hosting status.

    Combines:
      - NOW.md "### Servers" subsection (canonical inventory)
      - Local brain-server vitals (load, mem, disk, uptime)
      - systemctl status of key sh-brain units
      - HTTP pings to the public surface (fullpotential.com / .ai)
    """
    import shutil as _shutil
    import asyncio as _asyncio
    import httpx as _httpx
    import os as _os5

    lines = ["🖥️ <b>Servers — live status</b>\n"]

    # 1. NOW.md inventory
    inventory = _parse_servers_section()
    if inventory:
        lines.append("<b>Inventory (from NOW.md)</b>")
        for name, body in inventory:
            lines.append(f"  · <b>{tg._esc(name)}</b>")
            lines.append(f"     <i>{tg._esc(body[:240])}</i>")
        lines.append("")
    else:
        lines.append("<i>NOW.md Servers section not found — inventory skipped.</i>\n")

    # 2. Brain server vitals (this process)
    lines.append("<b>This server (brain) · live</b>")
    try:
        with open("/proc/uptime") as f:
            up_s = float(f.read().split()[0])
        days = int(up_s // 86400)
        hours = int((up_s % 86400) // 3600)
        lines.append(f"  ⏱️ uptime: {days}d {hours}h")
    except Exception:
        pass
    try:
        with open("/proc/loadavg") as f:
            la = f.read().split()[:3]
        lines.append(f"  📊 load: {la[0]} · {la[1]} · {la[2]}")
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for ln in f:
                k, _, v = ln.partition(":")
                meminfo[k.strip()] = v.strip()
        total_kb = int(meminfo.get("MemTotal", "0").split()[0] or 0)
        avail_kb = int(meminfo.get("MemAvailable", "0").split()[0] or 0)
        used_pct = 100 * (total_kb - avail_kb) / total_kb if total_kb else 0
        lines.append(f"  🧠 mem: {used_pct:.0f}% used  ({(total_kb-avail_kb)//1024}MB / {total_kb//1024}MB)")
    except Exception:
        pass
    try:
        du = _shutil.disk_usage("/")
        used_pct = 100 * du.used / du.total if du.total else 0
        lines.append(f"  💾 disk /: {used_pct:.0f}% used  ({du.used // (1024**3)}G / {du.total // (1024**3)}G)")
    except Exception:
        pass
    lines.append("")

    # 3. Key services on this box
    SERVICE_UNITS = (
        "sh-brain-tgbot",
        "sh-brain-index",
        "sh-mcp-http",
        "postgresql",
        "ollama",
    )
    statuses = await _systemctl_active_many(SERVICE_UNITS)
    lines.append("<b>Brain services</b>")
    for unit, state in statuses:
        glyph = "🟢" if state == "active" else ("🟡" if state in ("activating", "reloading") else "🔴")
        lines.append(f"  {glyph} <code>{tg._esc(unit)}</code> · {tg._esc(state)}")
    lines.append("")

    # 4. Public surface pings
    PUBLIC_TARGETS = (
        ("fullpotential.com", "https://fullpotential.com/"),
        ("fullpotential.ai", "https://fullpotential.ai/"),
        ("fullpotential.com/api/champion/list", "https://fullpotential.com/api/champion/list"),
    )
    async def _ping(url: str) -> tuple[int | None, float | None]:
        try:
            t0 = _asyncio.get_event_loop().time()
            async with _httpx.AsyncClient(timeout=6.0, follow_redirects=True) as c:
                r = await c.get(url)
                ms = (_asyncio.get_event_loop().time() - t0) * 1000.0
            return (r.status_code, ms)
        except Exception:
            return (None, None)

    pings = await _asyncio.gather(*[_ping(u) for _, u in PUBLIC_TARGETS])
    lines.append("<b>Public surface (primary)</b>")
    for (name, _url), (code, ms) in zip(PUBLIC_TARGETS, pings):
        if code is None:
            lines.append(f"  🔴 {tg._esc(name)} · unreachable")
        else:
            glyph = "🟢" if 200 <= code < 400 else "🟡"
            lines.append(f"  {glyph} {tg._esc(name)} · {code} · {ms:.0f}ms")
    lines.append("")

    # 5. Cost line (from memory: ~$805/mo all-in verified 2026-04-29)
    lines.append("<i>~$805/mo all-in (verified 2026-04-29). See /money for live breakdown · Source: NOW.md + /proc + systemctl + HTTP pings</i>")
    return "\n".join(lines)


def _parse_servers_section() -> list[tuple[str, str]]:
    """Pull the '### Servers' subsection from NOW.md as (name, description) pairs."""
    try:
        with open(_NOW_PATH, encoding="utf-8") as f:
            md = f.read()
    except Exception:
        return []
    import re as _re
    m = _re.search(r"^###\s+Servers\s*$", md, _re.MULTILINE | _re.IGNORECASE)
    if not m:
        return []
    body = md[m.end():]
    nh = _re.search(r"^(###|##)\s", body, _re.MULTILINE)
    if nh:
        body = body[: nh.start()]
    out: list[tuple[str, str]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        line = line[2:].strip()
        if " — " in line:
            name, _, rest = line.partition(" — ")
        elif " - " in line:
            name, _, rest = line.partition(" - ")
        else:
            name, rest = line, ""
        name = _strip_md(name)
        rest = _strip_md(rest)
        out.append((name, rest))
    return out


async def _systemctl_active_many(units: tuple[str, ...]) -> list[tuple[str, str]]:
    """Return [(unit, state)]. state is 'active', 'inactive', 'failed',
    'activating', or 'unknown' if systemctl is unavailable."""
    import asyncio as _asyncio
    async def _one(unit: str) -> tuple[str, str]:
        try:
            proc = await _asyncio.create_subprocess_exec(
                "systemctl", "is-active", unit,
                stdout=_asyncio.subprocess.PIPE,
                stderr=_asyncio.subprocess.DEVNULL,
            )
            out, _ = await _asyncio.wait_for(proc.communicate(), timeout=3.0)
            return (unit, (out.decode().strip() or "unknown"))
        except Exception:
            return (unit, "unknown")
    return list(await _asyncio.gather(*[_one(u) for u in units]))


# ───────────────────────────── /capabilities ──────────────────────────────
_CAPABILITIES_PATH = _os.path.join(_STATE_DIR, "CAPABILITIES.md")
_CATEGORY_ALIASES = {
    "game": "Game",
    "brain": "Sunheart Brain",
    "sunheart": "Sunheart Brain",
    "inquiry": "Inquiry",
    "coordination": "Inquiry",
    "money": "Economics",
    "economics": "Economics",
    "trading": "Trading",
    "signals": "Trading",
    "infra": "Infrastructure",
    "infrastructure": "Infrastructure",
    "village": "Village",
    "bots": "Other Telegram Bots",
    "deprecated": "Deprecated",
    "retired": "Deprecated",
}


async def _cmd_capabilities(rest: str = "") -> str:
    """Render core/STATE/CAPABILITIES.md grouped by category.

    Optional arg filters to a category alias (game, brain, inquiry, money,
    trading, infra, village, bots, deprecated). The file lives at
    /var/lib/sh-brain/state/CAPABILITIES.md, synced from the laptop via
    sync_now_to_brain.sh.
    """
    try:
        with open(_CAPABILITIES_PATH, encoding="utf-8") as f:
            md = f.read()
    except Exception as e:
        return (
            "🛠 <b>Capabilities</b>\n\n"
            f"<i>CAPABILITIES.md unreachable at <code>{tg._esc(_CAPABILITIES_PATH)}</code>: "
            f"{tg._esc(str(e))}</i>\n\n"
            "Run <code>SERVICES/sunheart-brain/ingest/sync_now_to_brain.sh</code> from the laptop."
        )

    sections = _parse_capabilities(md)
    if not sections:
        return "🛠 <b>Capabilities</b>\n\n<i>No category sections parsed from CAPABILITIES.md.</i>"

    filter_token = (rest or "").strip().lower()
    filter_match: str | None = None
    if filter_token:
        filter_match = _CATEGORY_ALIASES.get(filter_token)
        if filter_match is None:
            for key in _CATEGORY_ALIASES.keys():
                if key.startswith(filter_token):
                    filter_match = _CATEGORY_ALIASES[key]
                    break

    import os as _os6
    age = ""
    try:
        from datetime import datetime as _dt5
        diff = (_dt5.now() - _dt5.fromtimestamp(_os6.path.getmtime(_CAPABILITIES_PATH))).total_seconds()
        if diff < 3600: age = f"{int(diff//60)}m ago"
        elif diff < 86400: age = f"{int(diff//3600)}h ago"
        else: age = f"{int(diff//86400)}d ago"
    except Exception:
        pass

    lines = ["🛠 <b>Capabilities — what this system can do</b>"]
    if age:
        lines.append(f"<i>Last synced: {age}</i>")

    total_entries = sum(len(s["entries"]) for s in sections)
    shown = 0
    matched_section_count = 0

    for sec in sections:
        if filter_match and filter_match.lower() not in sec["title"].lower():
            continue
        matched_section_count += 1
        lines.append(f"\n<b>{tg._esc(sec['emoji'] + ' ' if sec['emoji'] else '')}{tg._esc(sec['title'])}</b>")
        per_section_cap = 999 if filter_match else 8
        entries = sec["entries"][:per_section_cap]
        for e in entries:
            shown += 1
            date = e.get("date") or ""
            name = e.get("name") or ""
            status = e.get("status") or ""
            desc = e.get("desc") or ""
            date_part = f"<code>{tg._esc(date)}</code> · " if date else ""
            status_part = f" {tg._esc(status)}" if status else ""
            desc_part = f" — <i>{tg._esc(desc)}</i>" if desc else ""
            lines.append(f"  · {date_part}<b>{tg._esc(name)}</b>{status_part}{desc_part}")
        remaining = len(sec["entries"]) - len(entries)
        if remaining > 0:
            lines.append(f"  <i>…+{remaining} more</i>")

    if filter_match and matched_section_count == 0:
        return (
            f"🛠 <b>Capabilities</b>\n\n<i>No category matched '{tg._esc(filter_token)}'. "
            f"Try: {', '.join(sorted(set(_CATEGORY_ALIASES.keys())))}.</i>"
        )

    if not filter_match and total_entries > shown:
        lines.append(f"\n<i>Showing top per category. {total_entries} total entries.</i>")
    lines.append(
        "\n<i>Source: core/STATE/CAPABILITIES.md · "
        "/capabilities &lt;category&gt; to filter (game, brain, inquiry, money, trading, infra, village, bots, deprecated)</i>"
    )
    return "\n".join(lines)


def _parse_capabilities(md: str) -> list[dict]:
    """Parse CAPABILITIES.md into [{title, emoji, entries:[{date,name,status,desc}]}].

    Section heading: '## <emoji?> <Title>' (skips Update Protocol + the file's
    top-level # heading). Entry format:
      - **YYYY-MM-DD** · <name> · <status icon + words> <description?>
      - <name> · <status>
    Anything else is ignored.
    """
    import re
    sections: list[dict] = []
    cur: dict | None = None
    lines = md.splitlines()
    head_re = re.compile(r"^##\s+(.+?)\s*$")
    for raw in lines:
        line = raw.rstrip()
        m = head_re.match(line)
        if m:
            title_full = m.group(1).strip()
            if title_full.lower().startswith("update protocol"):
                cur = None
                continue
            emoji, _, title = title_full.partition(" ")
            if not any(c.isalpha() for c in emoji):
                title_clean = title.strip() or title_full
                emoji_clean = emoji
            else:
                title_clean = title_full
                emoji_clean = ""
            cur = {"title": title_clean, "emoji": emoji_clean, "entries": []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        if not line.startswith("- "):
            continue
        body = line[2:].strip()
        entry = _parse_capability_line(body)
        if entry:
            cur["entries"].append(entry)
    return [s for s in sections if s["entries"]]


def _parse_capability_line(body: str) -> dict | None:
    """Parse a bullet body like:
    '**2026-05-08** · Foo · 🟢 live · short description'
    """
    import re
    parts = [p.strip() for p in body.split(" · ")]
    if not parts:
        return None
    date = ""
    first = parts[0]
    md_date = re.match(r"^\*\*(\d{4}-\d{2}-\d{2})\*\*$", first)
    plain_date = re.match(r"^(\d{4}-\d{2}-\d{2})$", first)
    if md_date:
        date = md_date.group(1)
        parts = parts[1:]
    elif plain_date:
        date = plain_date.group(1)
        parts = parts[1:]
    if not parts:
        return None
    name = re.sub(r"\*\*(.+?)\*\*", r"\1", parts[0]).strip()
    status = ""
    desc = ""
    if len(parts) >= 2:
        status_candidate = parts[1].strip()
        if any(g in status_candidate for g in ("🟢", "🟡", "⚪", "⚠️", "🔴")):
            status = status_candidate
            if len(parts) >= 3:
                desc = " · ".join(parts[2:]).strip()
        else:
            desc = " · ".join(parts[1:]).strip()
    return {"date": date, "name": name, "status": status, "desc": desc}


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
        _ja_tick = 0
        while True:
            # james_ask outbound: deliver any pending asks each cycle (~25s)
            try:
                await james_ask.send_pending(_ask_send_wrapper, esc_fn=tg._esc)
            except Exception as e:
                log.warning("james_ask.send_pending failed: %s", e)
            # Periodic expiry sweep (every ~50 cycles · ~20 min)
            _ja_tick += 1
            if _ja_tick % 50 == 0:
                try:
                    james_ask.expire_old()
                except Exception:
                    pass
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
