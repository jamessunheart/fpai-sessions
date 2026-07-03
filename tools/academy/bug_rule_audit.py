#!/usr/bin/env python3
"""Enforce P8 — every bug becomes a rule. No bug is FIXED without a guard.

Parses core/STATE/BUG_LOG.md and fails (exit 1) if any row marked FIXED lacks a
durable guard (a regression test, a Principle reference, or an automated check).
This turns "every bug becomes a rule for future passes" from a hope into a gate:
run it in CI / the build loop, and a fix that repairs only the instance can't
claim FIXED.

A guard counts if the row's Guard cell names a test (`test_...`/`.py`), a
Principle (`P<n>`), or a check (RCA signature / Constitution Check / circuit
breaker / timer/metric watch). PENDING (⏳) never counts.

Usage: python3 tools/academy/bug_rule_audit.py   (exit 0 clean, 1 if any FIXED bug is unguarded)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
BUG_LOG = REPO / "core" / "STATE" / "BUG_LOG.md"

GUARD_SIGNALS = (
    r"test_[a-z0-9_]+", r"\.py\b", r"\bP\d\b", r"circuit breaker", r"RCA signature",
    r"Constitution Check", r"timer", r"metric", r"check:", r"\btest:", r"guard\b",
)
PENDING_MARK = "⏳"


def parse_bug_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(BUG-\d+)\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # columns: ID | Symptom | Root | Root(P#) | Fix | Guard | Status
        if len(cells) < 7:
            continue
        rows.append({
            "id": cells[0], "symptom": cells[1][:60],
            "guard": cells[-2], "status": cells[-1].upper(),
        })
    return rows


def has_guard(guard_cell: str) -> bool:
    if PENDING_MARK in guard_cell or "PENDING" in guard_cell.upper():
        return False
    return any(re.search(sig, guard_cell, re.IGNORECASE) for sig in GUARD_SIGNALS)


def audit(bug_log: Path = BUG_LOG) -> dict:
    text = bug_log.read_text(encoding="utf-8")
    rows = parse_bug_rows(text)
    unguarded_fixed = [r for r in rows if r["status"].startswith("FIXED") and not has_guard(r["guard"])]
    pending = [r for r in rows if not r["status"].startswith("FIXED")]
    return {
        "total": len(rows),
        "fixed": sum(1 for r in rows if r["status"].startswith("FIXED")),
        "unguarded_fixed": unguarded_fixed,
        "pending_guard": [{"id": r["id"], "status": r["status"], "symptom": r["symptom"]} for r in pending],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bug-log", type=Path, default=BUG_LOG)
    args = ap.parse_args(argv)

    if not args.bug_log.exists():
        print(f"bug log not found: {args.bug_log}", file=sys.stderr)
        return 1
    result = audit(args.bug_log)
    print(f"bugs: {result['total']} · FIXED: {result['fixed']} · "
          f"pending-guard: {len(result['pending_guard'])}")
    for p in result["pending_guard"]:
        print(f"  ⏳ {p['id']} [{p['status']}] {p['symptom']} — owes a guard")
    if result["unguarded_fixed"]:
        print("\n✗ P8 VIOLATION — these bugs are marked FIXED but have NO guard:")
        for r in result["unguarded_fixed"]:
            print(f"  {r['id']}: {r['symptom']}  (guard cell: {r['guard'][:50]!r})")
        return 1
    print("✓ P8 holds — every FIXED bug has a guard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
