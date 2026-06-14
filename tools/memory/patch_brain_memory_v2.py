#!/usr/bin/env python3
"""Patch v2 — make the brain USE its conversation memory, not drown it in notes.

v1 (patch_brain_memory.py) wired _recent_turns into the reply path — verified
loading 106 messages. But the bot still confabulated ("I can see Mem0 is live
from December 25th, but I don't have cross-conversation memory") because:
  - its system prompt says "answer using ONLY the snippets from your notes"
  - so it reports a NOTE about a memory system as its own status, and
    under-weights the actual conversation history now in the prompt.

This fixes the framing (run ON server 162, in /opt/sh-brain-src):
  R1 — system prompt: conversation is your REAL memory; notes are reference
       facts, NOT your own state.
  R2 — explicit rules: answer from the conversation first; never report a
       note's content as your status; you DO have cross-chat memory now.
  R3 — relabel the prompt sections so the model can tell conversation (memory)
       from notes (background).

Safety: anchors match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time

P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# R1 — reframe the opening of the system prompt
edits.append((
    "You answer questions using only the snippets retrieved\nfrom his notes, AI conversations, and papers. Style:",
    "You have TWO sources, and they are different:\n"
    "1. OUR CONVERSATION (shown below) — this IS your real memory of talking with James. "
    "It carries across messages and days. When he asks what you remember or what you discussed, answer from this.\n"
    "2. BACKGROUND NOTES — snippets from his notes/papers. Reference facts only, NOT your own memory or status.\n"
    "Style:",
))

# R2 — replace the weaker conversation rule with strong anti-confabulation rules
edits.append((
    '- You are also given the recent conversation; use it to stay coherent and resolve references. Answering a follow-up from the conversation itself is not fabrication.',
    '- Answer from OUR CONVERSATION first; use notes only as supporting facts.\n'
    '- Never report a note\'s content as your own state. Do NOT say things like "I can see Mem0 is live" — '
    'that is a note, not you. Speak about what YOU and James actually said.\n'
    '- You DO have cross-conversation memory now — the conversation below proves it. '
    'Never claim each chat starts fresh.',
))

# R3a — relabel the conversation block as the real memory
edits.append((
    '        user += ("Recent conversation with James (oldest first). Use it to resolve what "\n'
    '                 "\'that\', \'it\', or \'you said\' refer to, and to stay coherent:\\n")',
    '        user += ("OUR CONVERSATION — your real memory across chats (oldest first). "\n'
    '                 "Answer from this; resolve \'that\'/\'it\'/\'you said\' here:\\n")',
))

# R3b — relabel the snippets block as background (not memory)
edits.append((
    '        user += "Relevant snippets from your brain:\\n\\n"',
    '        user += "Background reference notes (supporting facts, NOT your memory):\\n\\n"',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need exactly 1) — no change made.\n  {a[:70]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-givememory-v2-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — {len(edits)} edits applied, file compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error, original restored: {e}")
    sys.exit(1)
