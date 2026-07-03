#!/usr/bin/env python3
"""Metric coherence guard — the map must match the territory.

James, 2026-07-03: "what would make the system more coherent?" The deepest
incoherence found: the system reports THREE different values for one metric
across its own canonical files (NOW: 100%, HOT_STATE: 100%, ALIGNMENT: 41.3%)
while a machine SSOT (core/BUILD/signals/awareness_reliability.json) already
holds the measured truth. Metrics live as hand-typed prose, so they drift.

This guard reads the signal JSONs (the measured truth) and flags any canonical
state file whose hand-typed number diverges from it. It is the STATE analog of
constitution_check: constitution_check gates PROPOSALS against law; this gates
REPORTED STATE against measured reality. Honesty-first, made structural.

Exit 0 = coherent · exit 1 = drift found (list printed). Read-only; never edits.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Each metric: the JSON SSOT, how to read its value, and the canonical files that
# quote it in prose. Extend as more signals gain a machine source.
SIGNALS = [
    {
        "name": "awareness_reliability",
        "json": REPO / "core" / "BUILD" / "signals" / "awareness_reliability.json",
        "read": lambda d: float(d["metric"]["reliability"]) * 100.0,
        "files": [
            REPO / "core" / "STATE" / "NOW.md",
            REPO / "core" / "STATE" / "identity" / "ALIGNMENT.md",
        ],
        # matches "awareness ... 88%" / "awareness → 100%" / "awareness 41.3%"
        "pat": re.compile(r"awareness[^.\n]{0,40}?(\d{1,3}(?:\.\d+)?)\s*%", re.I),
        "tol": 1.0,  # percentage points
    },
]

# A number is HISTORY/FORECAST (not drift) only when the LINE is explicitly marked
# as such — a date-stamp or an "archived/historical" label. We do NOT excuse a live
# measurement just because a forecast word appears elsewhere in the sentence
# (e.g. "score 41.3% ... climbing" is a stale CURRENT claim, not a forecast).
_HISTORICAL = re.compile(r"\d{4}-\d{2}-\d{2}|archived|historical", re.I)
# Approximate/target values (~95%, → 100%) are not asserted measurements — but only
# when the tilde/arrow is ADJACENT to the number, not merely present in the line.
_APPROX_ADJACENT = re.compile(r"[~→]\s*$")


def current_section(text: str) -> str:
    """Files like ALIGNMENT.md stack dated snapshots newest-first; only the top one
    is the live claim. Everything from the first 'archived' marker down is history.
    Scan only the current section so old checkpoints aren't mistaken for drift."""
    out = []
    for line in text.splitlines():
        if "archived" in line.lower():
            break
        out.append(line)
    return "\n".join(out)


def check() -> list[str]:
    drift: list[str] = []
    for sig in SIGNALS:
        jpath = sig["json"]
        if not jpath.exists():
            continue
        try:
            truth = sig["read"](json.loads(jpath.read_text()))
        except Exception as e:  # SSOT unreadable = its own incoherence
            drift.append(f"[{sig['name']}] SSOT unreadable ({jpath.name}): {e}")
            continue
        for fpath in sig["files"]:
            if not fpath.exists():
                continue
            for line in current_section(fpath.read_text()).splitlines():
                if _HISTORICAL.search(line):
                    continue  # explicitly dated/archived history is allowed to differ
                m = sig["pat"].search(line)
                if not m:
                    continue
                # approximate/target only if ~ or → sits immediately before the number
                if _APPROX_ADJACENT.search(line[:m.start(1)]):
                    continue
                stated = float(m.group(1))
                if abs(stated - truth) > sig["tol"]:
                    drift.append(
                        f"[{sig['name']}] {fpath.relative_to(REPO)}: "
                        f"states {stated:g}% but SSOT measures {truth:g}% "
                        f"(source: {jpath.name})")
    return drift


def main() -> int:
    drift = check()
    if not drift:
        print("metric coherence: OK — all canonical prose matches the measured SSOT.")
        return 0
    print("metric coherence: DRIFT — reported state contradicts measured truth:")
    for d in drift:
        print(f"  · {d}")
    print("\nFix: correct the prose to the SSOT value (with source+timestamp), "
          "or better — render it from the JSON instead of hand-typing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
