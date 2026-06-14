#!/usr/bin/env python3
"""Patch v8 — fix money + 'ai' pronunciation in Ember's voice.

v7 turned "$6k" into "6 dollarsk" (suffix stranded) and left bare "ai" awkward.
This handles $N k/m/b -> "N thousand/million/billion dollars" and standalone
"ai" -> "AI" (which the speech model pronounces correctly).

Safety: anchor match-once-or-abort, backup, compile-check, auto-revert.
"""
import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()

A = '    text = re.sub(r"\\$\\s*(\\d)", r"\\1 dollars", text)'
B = ('    text = re.sub(r"\\$\\s*(\\d[\\d,]*(?:\\.\\d+)?)\\s*[kK]\\b", r"\\1 thousand dollars", text)\n'
     '    text = re.sub(r"\\$\\s*(\\d[\\d,]*(?:\\.\\d+)?)\\s*[mM]\\b", r"\\1 million dollars", text)\n'
     '    text = re.sub(r"\\$\\s*(\\d[\\d,]*(?:\\.\\d+)?)\\s*[bB]\\b", r"\\1 billion dollars", text)\n'
     '    text = re.sub(r"\\$\\s*(\\d[\\d,]*(?:\\.\\d+)?)", r"\\1 dollars", text)\n'
     '    text = re.sub(r"\\bai\\b", "AI", text, flags=re.IGNORECASE)')

n = src.count(A)
if n != 1:
    print(f"ABORT: anchor matched {n}x (need 1).")
    sys.exit(1)
src = src.replace(A, B)

bak = P + ".bak-tts-v8-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — applied, compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P)
    print(f"REVERTED — syntax error: {e}")
    sys.exit(1)
