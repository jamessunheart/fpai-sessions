#!/usr/bin/env python3
"""Give @sunheartbrain_bot conversation memory.

Root cause (found 2026-06-13): curator/tgbot.py LOGS every Telegram turn to
brain_index.tg_messages but NEVER reads them back. Each reply is synthesized
from semantic note-search only — zero conversation history. So "what made you
bring that up?" makes the bot confabulate: it cannot see what "that" was.
James caught exactly this on June 13.

This patch (run ON server 162, in /opt/sh-brain-src):
  1. adds _recent_turns() — loads recent turns for the chat from tg_messages
  2. feeds that history into every _synthesize_answer() call
  3. lets the bot answer follow-ups from the conversation itself (not just notes)

Safety: anchors must each match exactly once (else ABORT, no change); backs up
the original; compiles the result; auto-reverts on any syntax error.

USAGE (James runs the prod write — Reserved-Class):
  scp tools/memory/patch_brain_memory.py root@162.0.208.88:/tmp/
  ssh root@162.0.208.88 'cd /opt/sh-brain-src && ./.venv/bin/python /tmp/patch_brain_memory.py \
      && systemctl restart sh-brain-tgbot && sleep 2 && systemctl is-active sh-brain-tgbot'
Then text the bot: "what did I just ask you?" — it should now know.
Rollback: the script prints the .bak path; `cp <bak> curator/tgbot.py && systemctl restart sh-brain-tgbot`.
"""
import shutil, py_compile, sys, time

P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# R1 — add _recent_turns helper + give _synthesize_answer a history param
edits.append((
    "async def _synthesize_answer(question: str, hits: list[dict]) -> str:",
    '''async def _recent_turns(chat_id: str, exclude_update_id=None, limit: int = 14):
    """Recent conversation turns for this chat (oldest-first) so the brain has
    continuity and can resolve what 'that' / 'you said' refer to."""
    from .db import connect
    sql = ("SELECT role, text FROM brain_index.tg_messages "
           "WHERE chat_id = %s AND private_flag IS NOT TRUE "
           "AND (%s::bigint IS NULL OR update_id IS DISTINCT FROM %s::bigint) "
           "ORDER BY at DESC LIMIT %s")
    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (str(chat_id), exclude_update_id, exclude_update_id, limit))
                rows = await cur.fetchall()
        return [(r[0], (r[1] or "")[:600]) for r in reversed(rows)]
    except Exception as e:
        log.warning("recent_turns load failed: %s", e)
        return []


async def _synthesize_answer(question: str, hits: list[dict], history=None) -> str:''',
))

# R2 — answer from history even when there are no semantic hits
edits.append((
    '    if not hits:\n        return ("I couldn\'t find anything in your brain about that. "',
    '    if not hits and not history:\n        return ("I couldn\'t find anything in your brain about that. "',
))

# R3 — build the prompt with conversation history prepended
edits.append((
    '    user = "Question:\\n" + question + "\\n\\nRelevant snippets from your brain:\\n\\n"',
    '''    user = ""
    if history:
        user += ("Recent conversation with James (oldest first). Use it to resolve what "
                 "'that', 'it', or 'you said' refer to, and to stay coherent:\\n")
        for _role, _text in history:
            _who = "James" if _role == "user" else "You"
            user += f"{_who}: {_text}\\n"
        user += "\\n"
    user += "James just said:\\n" + question + "\\n\\n"
    if hits:
        user += "Relevant snippets from your brain:\\n\\n"''',
))

# R4 — inject history at the dispatch site
edits.append((
    "    hits = await _search_brain(text)\n    answer_body = _format_answer_for_telegram(await _synthesize_answer(text, hits))",
    "    hits = await _search_brain(text)\n    history = await _recent_turns(str(chat_id), exclude_update_id=update_id)\n    answer_body = _format_answer_for_telegram(await _synthesize_answer(text, hits, history))",
))

# R5 — let the system prompt use the conversation
edits.append((
    '- Never fabricate. Never say "as an AI...". Speak as the brain itself.',
    '- Never fabricate. Never say "as an AI...". Speak as the brain itself.\n'
    '- You are also given the recent conversation; use it to stay coherent and resolve references. '
    'Answering a follow-up from the conversation itself is not fabrication.',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need exactly 1) — no change made.\n  {a[:70]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-givememory-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — 5 edits applied, file compiles. Backup: {bak}")
    print("Now: systemctl restart sh-brain-tgbot")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error, original restored: {e}")
    sys.exit(1)
