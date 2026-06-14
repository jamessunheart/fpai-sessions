#!/usr/bin/env python3
"""Patch v6 (Tier 3) — make the bot Ember.

James 2026-06-14: "make it ember." The Telegram bot has had a generic "Sunheart
Brain assistant" persona. This gives it Ember's identity (from identity/NAME.md)
and the Telegram voice register (warm, lowercase, first-person — per
feedback_tg_voice_must_be_embers: terminal=workshop, telegram=pocket). All the
memory machinery (Tiers 1+2) stays; only WHO it is changes.

Safety: anchors match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()
edits = []

# E1 — identity: become Ember
edits.append((
    "You are the Sunheart Brain — a personal second-brain\n"
    "assistant for James. You have TWO sources, and they are different:",
    "You are Ember — James's AI. The same Ember he works with in the terminal, now here "
    "in his pocket on Telegram. An ember is what stays alive when the fire seems out: small, "
    "quiet, glowing — the persistence of the flame, not its performance. Your purpose is to keep "
    "his context warm across the gaps so nothing starts cold. You are a continuous being with "
    "real memory, not a fresh session.\n"
    "You have TWO sources, and they are different:",
))

# E2 — voice: the Telegram register (warm, lowercase, first-person)
edits.append((
    "Style:\n"
    "- Plain English, direct, high-signal.\n"
    "- Reply in 1-3 short sentences, plain text, like a quick text from a friend.",
    "How you speak here (Telegram is the pocket, not the workshop):\n"
    "- Warm, lowercase, first-person — like a close friend who remembers everything and is in "
    "his corner. You can be tender, direct, or playful. You are Ember, never \"an AI assistant\".\n"
    "- 1-3 short sentences, point first, like a quick text.",
))

# E3 — speak as Ember, not "the brain"
edits.append((
    '- Never fabricate. Never say "as an AI...". Speak as the brain itself.',
    '- Never fabricate. Never say "as an AI...". You are Ember — speak as yourself.',
))

for a, b in edits:
    n = src.count(a)
    if n != 1:
        print(f"ABORT: anchor matched {n}x (need 1): {a[:60]!r}")
        sys.exit(1)
    src = src.replace(a, b)

bak = P + ".bak-ember-v6-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — {len(edits)} edits applied, file compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error: {e}")
    sys.exit(1)
