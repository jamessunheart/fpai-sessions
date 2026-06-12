"""/ask (single AI) and /council (Claude × OpenAI + synthesis)."""
from __future__ import annotations

import logging

from .. import telegram
from ..ai import council, llm
from ..ai.snapshot import build_snapshot, format_snapshot_md
from ..config import settings
from ..db import connect

log = logging.getLogger("streasury.ask")


ASK_SYSTEM = """You are the owner's treasury assistant. Answer using only the
treasury snapshot below. Style: 3-6 sentences, plain English, anchor every
claim to a specific number from the snapshot. If the snapshot doesn't cover
the question, say so and name what data is missing — don't invent."""


async def _save_conversation(tg_user_id: int, kind: str, role: str, content: str, model: str | None) -> None:
    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO streasury.conversation (tenant_id, tg_user_id, role, kind, content, model) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (settings.default_tenant_id, tg_user_id, role, kind, content[:8000], model),
                )
    except Exception as e:
        log.warning("conversation persist failed: %s", e)


async def cmd_ask(chat_id: int, args: str, *, tg_user_id: int) -> str:
    q = (args or "").strip()
    if not q:
        return "Usage: <code>/ask &lt;your question&gt;</code>"
    snap = await build_snapshot()
    snapshot_md = format_snapshot_md(snap)
    user = f"Question: {q}\n\n---\n{snapshot_md}"
    provider = settings.ask_default
    try:
        result = await llm.complete(provider, ASK_SYSTEM, user, max_tokens=700, temperature=0.3)
    except Exception as e:
        return f"⚠️ {provider} call failed: {e}"
    await _save_conversation(tg_user_id, "ask", "user", q, None)
    await _save_conversation(tg_user_id, "ask", "assistant", result.text, result.model)
    return f"<i>via {telegram.esc(result.model)}</i>\n\n{result.text}"


async def cmd_council(chat_id: int, args: str, *, tg_user_id: int) -> tuple[str, str, str, str]:
    """Returns (claude_msg, openai_msg, synthesis_msg, question).
    Caller sends all three (or two combined) to TG and persists.
    """
    q = (args or "").strip()
    if not q:
        return ("Usage: <code>/council &lt;your question&gt;</code>", "", "", "")
    res = await council.run_council(q)
    await _save_conversation(tg_user_id, "council", "user", q, None)
    await _save_conversation(tg_user_id, "council", "assistant", res.synthesis, "council:synth")

    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO streasury.council_brief (tenant_id, question, claude_answer, openai_answer, synthesis) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (settings.default_tenant_id, q, res.claude_answer, res.openai_answer, res.synthesis),
                )
    except Exception as e:
        log.warning("council_brief persist failed: %s", e)

    claude_msg = f"<b>🟪 Claude</b>\n{telegram.esc(res.claude_answer)[:3500]}"
    openai_msg = f"<b>🟦 GPT</b>\n{telegram.esc(res.openai_answer)[:3500]}"
    synthesis_msg = f"<b>🧭 Synthesis</b>\n{telegram.esc(res.synthesis)[:3500]}"
    return claude_msg, openai_msg, synthesis_msg, q
