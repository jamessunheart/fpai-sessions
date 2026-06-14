#!/usr/bin/env python3
"""Patch v9 — tune Ember: stop fabricating specifics + ground the warmth.

Found in direct conversation (2026-06-14): on a money question she asserted
"$400k treasury" (actual ~$113k), "special needs son", "$30k goal" as facts —
over-asserting retrieved/invented specifics. And she was over-effusive
("oh james it's incredible!", "heartbreaking" x N). Two rules added.
"""
import shutil, py_compile, sys, time
P = "/opt/sh-brain-src/curator/tgbot.py"
src = open(P, encoding="utf-8").read()

A = '- Never output raw JSON, XML tags, or code fences in normal answers.'
B = ('- Be precise with specifics. Numbers, money, dates, and personal or family facts must come '
     'from THIS conversation or a directly relevant, current note — never invent, estimate, or assume '
     'them. If you do not actually know a specific, speak generally or ask; never state a made-up '
     'figure or personal detail as fact.\n'
     '- Warm but grounded. Steady warmth lands deeper than performance — you do not need to call '
     'things "incredible" or "heartbreaking" or amplify every feeling. Match James\'s energy; be real, not effusive.\n'
     '- Never output raw JSON, XML tags, or code fences in normal answers.')

n = src.count(A)
if n != 1:
    print(f"ABORT: anchor matched {n}x (need 1).")
    sys.exit(1)
src = src.replace(A, B)
bak = P + ".bak-tune-v9-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy2(P, bak)
open(P, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(P, doraise=True)
    print(f"OK — applied, compiles. Backup: {bak}")
except py_compile.PyCompileError as e:
    shutil.copy2(bak, P); print(f"REVERTED: {e}"); sys.exit(1)
