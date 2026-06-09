#!/usr/bin/env python3
"""Closeout — one pass that re-weaves every self-refreshing surface so the whole
mirror is coherent, instead of James/Ember weaving the latest truth by hand.

Runs, in order: index of indexes · self-model (buildstream+upgrades) ·
reflections resurface · HOME/NEXT daily sync. Each step only regenerates
auto-blocks from canonical sources — no money / network / service action.

Usage:  python3 tools/closeout/run.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

STEPS = [
    ("index of indexes", ["tools/index/refresh.py"]),
    ("self-model", ["tools/selfmodel/refresh.py"]),
    ("reflections", ["tools/reflect/log.py", "--resurface"]),
    ("codex queue", ["tools/handoff/dispatch.py", "--refresh"]),  # drop built specs so James never rebuilds
    ("HOME / NEXT", ["tools/decisions/daily_sync.py"]),
]


def main() -> int:
    os.chdir(REPO)
    print("🔄 CLOSEOUT — re-weaving every surface from canonical truth:\n")
    failures = 0
    for name, cmd in STEPS:
        script = cmd[0]
        if not (REPO / script).exists():
            print(f"  · {name}: skip (missing {script})")
            continue
        try:
            r = subprocess.run(
                [sys.executable, *cmd], capture_output=True, text=True, timeout=180
            )
            if r.returncode == 0:
                last = (r.stdout.strip().splitlines() or ["done"])[-1]
                print(f"  ✓ {name}: {last[:140]}")
            else:
                failures += 1
                err = (r.stderr.strip() or r.stdout.strip() or "error").splitlines()[-1]
                print(f"  ✗ {name}: {err[:140]}")
        except Exception as e:  # noqa: BLE001 — report any step failure, keep going
            failures += 1
            print(f"  ✗ {name}: {e}")
    print(f"\n{'✅ all surfaces re-woven' if not failures else f'⚠️ {failures} step(s) need a look'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
