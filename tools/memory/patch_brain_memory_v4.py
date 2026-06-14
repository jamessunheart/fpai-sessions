#!/usr/bin/env python3
"""Patch v4 (Tier 1) — kill the confabulation at its source.

Audit finding (2026-06-14): the bot's note_chunks RAG corpus (4,996 chunks from
old Cursor/Claude logs) contains real past conversations ABOUT memory breaking
("you just lost your memory", "Mem0 is live", "simulation of the interface").
On memory questions the vector search retrieves those and the bot reports them
as its CURRENT state. Instructions alone (v2/v3) couldn't override retrieval.

Three structural fixes:
  R1 — _is_meta_question(): detect self-referential questions.
  R2 — dispatch: on a meta question WITH conversation history, skip note-RAG
       entirely and answer from the live conversation (kills the pollution).
  R3 — date grounding: inject today's real date (no more "December 25th").

Safety: anchors match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time

P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# R1 — meta-question detector, inserted before _recent_turns
edits.append((
    "async def _recent_turns(chat_id: str, exclude_update_id=None, limit: int = 14):",
    '''_META_Q = ("what were we", "what was i", "what did i", "what did we", "do you remember",
           "did you remember", "your memory", "across our", "across chat", "previous conversation",
           "remember our", "remember what", "what are we talking", "carrying over", "carry over",
           "do you have memory", "have memory", "remember me", "who am i", "what have we")


def _is_meta_question(text: str) -> bool:
    """True for self-referential questions about the conversation / the bot's own
    memory — these must be answered from live history, never from note-RAG."""
    t = (text or "").lower()
    return any(p in t for p in _META_Q)


async def _recent_turns(chat_id: str, exclude_update_id=None, limit: int = 14):''',
))

# R2 — dispatch: skip note-RAG for meta questions when history exists
edits.append((
    "    hits = await _search_brain(text)\n"
    "    history = await _recent_turns(str(chat_id), exclude_update_id=update_id)\n"
    "    answer_body = _format_answer_for_telegram(await _synthesize_answer(text, hits, history))",
    "    history = await _recent_turns(str(chat_id), exclude_update_id=update_id)\n"
    "    # Meta/self-referential questions must be answered from the LIVE conversation,\n"
    "    # not note-RAG — the note corpus holds old transcripts about memory failing\n"
    "    # that otherwise get reported as the bot's current state (confabulation).\n"
    "    hits = [] if (_is_meta_question(text) and history) else await _search_brain(text)\n"
    "    answer_body = _format_answer_for_telegram(await _synthesize_answer(text, hits, history))",
))

# R3 — date grounding at the top of the synthesized prompt
edits.append((
    '    user = ""\n    if history:',
    '    user = ""\n'
    '    try:\n'
    '        from datetime import datetime\n'
    '        user += "Today is " + datetime.now().strftime("%A, %B %d, %Y") + ".\\n\\n"\n'
    '    except Exception:\n'
    '        pass\n'
    '    if history:',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need exactly 1) — no change made.\n  {a[:70]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-givememory-v4-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — {len(edits)} edits applied, file compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error, original restored: {e}")
    sys.exit(1)
