#!/usr/bin/env python3
"""Structural coherence invariants — assert that created truth actually PROPAGATES.

James, 2026-07-04: "how would you make the system more coherent from here?" The honest
finding across this whole coherence campaign: every gap was the same shape — a truth
CREATED in one place that failed to REACH the surface that must reflect it. Latest
instance: laws P10/P11 were written in AI_PRINCIPLES but formatted so the doctrine
compiler's grep silently skipped them — every session booted without them for a day.

`metric_coherence.py` catches ONE propagation invariant (a metric vs its measured SSOT).
This is its structural sibling: the class-fix. It asserts the invariants that the
session kept finding broken by hand:

  A. DOCTRINE COMPLETENESS — every principle in AI_PRINCIPLES.md reaches the compiled
     CORE_DOCTRINE.md (the boot pack every session loads). Would have caught P10/P11.
  B. NO DANGLING POINTERS — every tool/hook file the doctrine + protocols reference
     actually exists on disk (the zen-village "module vanished → 502" class).

Read-only. Exit 0 = coherent · exit 1 = drift (listed). Runs in the daily self-audit.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    p = REPO / rel
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def doctrine_completeness() -> list[str]:
    """Every '### P{n}' principle in AI_PRINCIPLES must appear in CORE_DOCTRINE."""
    princ = _read("core/STATE/AI_PRINCIPLES.md")
    doctrine = _read("core/STATE/CORE_DOCTRINE.md")
    if not princ or not doctrine:
        return ["[doctrine] AI_PRINCIPLES or CORE_DOCTRINE unreadable"]
    ids = re.findall(r"^### (P\d+)\b", princ, re.M)
    missing = [pid for pid in ids if not re.search(rf"\b{pid}\b", doctrine)]
    if missing:
        return [f"[doctrine] {', '.join(missing)} in AI_PRINCIPLES but NOT in the compiled "
                f"CORE_DOCTRINE boot pack — run tools/academy/compile_doctrine.py (compiler grep drifted?)"]
    return []


def no_dangling_pointers() -> list[str]:
    """Every tool/hook path referenced by the doctrine + protocol registry must exist."""
    text = _read("core/STATE/CORE_DOCTRINE.md") + _read("core/STATE/ACADEMY/PROTOCOLS.md")
    refs = sorted(set(re.findall(r"tools/[A-Za-z0-9_/]+\.py|\.claude/hooks/[A-Za-z0-9_-]+\.sh", text)))
    return [f"[pointer] doctrine/protocols reference {r} — but it does not exist on disk"
            for r in refs if not (REPO / r).exists()]


def check() -> list[str]:
    return doctrine_completeness() + no_dangling_pointers()


def main() -> int:
    drift = check()
    if not drift:
        print("coherence invariants: OK — doctrine complete, no dangling pointers.")
        return 0
    print("coherence invariants: DRIFT — created truth is not fully propagating:")
    for d in drift:
        print(f"  · {d}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
