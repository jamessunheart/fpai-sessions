#!/usr/bin/env python3
"""Patch v5 (Tier 2) — wire conversation memory to run automatically + rank it.

Proven 2026-06-14: conversation_memory.compress_and_store() distills a chat into
durable facts, embeds them, stores as note_chunks(source='tg-memory'), and the
existing vector search retrieves them (ranked top). This patch makes it live:
  R1 — a per-chat turn counter.
  R2/R3 — boost source='tg-memory' in retrieval so durable memories beat the
          noisy old Cursor/Claude logs.
  R4 — after each reply, every 10 turns, compress recent conversation into memory
       (non-blocking background task).

Safety: anchors match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# R1 — per-chat memory turn counter (prepend to the _META_Q block from v4)
edits.append((
    '_META_Q = ("what were we", "what was i", "what did i", "what did we", "do you remember",',
    '_MEM_TURN_COUNTER: dict = {}\n\n'
    '_META_Q = ("what were we", "what was i", "what did i", "what did we", "do you remember",',
))

# R2 — boost tg-memory in the retrieval score
edits.append((
    "               1 - (embedding <=> %s::vector) AS score",
    "               (1 - (embedding <=> %s::vector)) + (CASE WHEN source = 'tg-memory' THEN 0.15 ELSE 0 END) AS score",
))

# R3 — boost tg-memory in the retrieval ordering
edits.append((
    "         ORDER BY embedding <=> %s::vector",
    "         ORDER BY (embedding <=> %s::vector) - (CASE WHEN source = 'tg-memory' THEN 0.15 ELSE 0 END)",
))

# R4 — fire compression every 10 turns after a reply
edits.append((
    '    await _log_tg_message(str(chat_id), "bot", answer)',
    '    await _log_tg_message(str(chat_id), "bot", answer)\n'
    '    # Tier 2: every ~10 turns, compress the conversation into durable retrievable memory.\n'
    '    try:\n'
    '        _MEM_TURN_COUNTER[str(chat_id)] = _MEM_TURN_COUNTER.get(str(chat_id), 0) + 1\n'
    '        if _MEM_TURN_COUNTER[str(chat_id)] % 10 == 0:\n'
    '            from .conversation_memory import compress_and_store\n'
    '            _mt = await _recent_turns(str(chat_id), limit=20)\n'
    '            asyncio.create_task(compress_and_store(str(chat_id), _mt))\n'
    '    except Exception as _e:\n'
    '        log.warning("memory compaction trigger failed: %s", _e)',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need 1): {a[:60]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-givememory-v5-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — {len(edits)} edits applied, file compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error: {e}")
    sys.exit(1)
