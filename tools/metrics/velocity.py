#!/usr/bin/env python3
"""Velocity ledger — the system's measure of its own TIME vs VALUE PRODUCED.

James, 2026-07-04: "I was asleep 8 hours. A smart system would make progress in that
time. Does it have a measure of its own time against the clock and what it produces of
value?" The honest answer was NO — and that blindness is why the system idled all night
(it can't feel that it produced nothing). This is the mirror.

It measures, over a window: VALUE-producing events (capability-increasing, verifiable) vs
elapsed hours, split by AUTONOMOUS (the system acting on its own) vs INTERACTIVE (produced
during a James/Ember session). The gap between the two is the whole question: a smart
self-standing system should produce value in the autonomous column while James sleeps.

Value = things that leave the system more capable, VERIFIABLE (not activity theater):
  - git commits of substance (feat/fix/verify/doctrine/feat) — real capability changes
  - decisions merged (build_status='merged')
Idle-hour = an hour whose only events were monitoring (probe/log/scan), zero value.

Read-only. Usage: velocity.py [--hours N]. Prints the ledger + an honest verdict.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VALUE_COMMIT = re.compile(r"^(feat|fix|verify|doctrine|coherence|design|perf)\b", re.I)
# Proof-weight (a proxy for the DREAM→COMPOUNDING ladder until LIVE-verification is wired):
# a LIVE/verified fix is worth more than a doc. True weight needs post_merge_reality_check
# to confirm live — this is the honest interim scale, not the final one.
PROOF_WEIGHT = {"feat": 1.0, "fix": 0.9, "verify": 0.7, "perf": 0.7,
                "coherence": 0.6, "design": 0.4, "doctrine": 0.4, "docs": 0.1, "chore": 0.1}
# Regressions — SUBTRACT these (net capability gain, not gross activity):
REGRESSION = re.compile(r"\brevert\b|reality-dead|false-merge|rolled? ?back|broke\b|regress", re.I)


def _weight(subject: str) -> float:
    m = re.match(r"^(\w+)", subject or "")
    return PROOF_WEIGHT.get(m.group(1).lower(), 0.2) if m else 0.2
# Interactive authors = a live session; autonomous = the build runner / timers.
AUTONOMOUS_AUTHORS = re.compile(r"build.?runner|codex|timer|cron|council|metabolism", re.I)


def _git(args: list[str]) -> str:
    return subprocess.run(["git", "-C", str(REPO)] + args, capture_output=True, text=True).stdout


def commits_in_window(hours: float) -> list[tuple[str, str, str]]:
    since = f"{int(round(hours))} hours ago"  # git rejects "8.0 hours ago" → silently empty
    out = _git(["log", f"--since={since}", "--pretty=%h\x1f%an\x1f%s"])
    rows = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            rows.append(tuple(parts))  # (sha, author, subject)
    return rows


def merged_decisions(hours: float) -> int:
    try:
        import psycopg, os
        db = os.environ.get("BRAIN_INDEX_DB_URL",
            "postgres://brain_index:50dc339828327a7a042dca45957a5bab6dc6b4eda3857524ccd014d9acc23a52@127.0.0.1:25432/postgres")
        with psycopg.connect(db, connect_timeout=5) as c, c.cursor() as cur:
            cur.execute("SELECT count(*) FROM brain_index.decisions "
                        "WHERE merged_at > now() - make_interval(hours => %s)", (int(hours),))
            return (cur.fetchone() or [0])[0]
    except Exception:
        return -1  # unknown (merged_at is known-unreliable — BUG in the queue)


def run(hours: float) -> dict:
    commits = commits_in_window(hours)
    value = [c for c in commits if VALUE_COMMIT.search(c[2])]
    autonomous = [c for c in value if AUTONOMOUS_AUTHORS.search(c[1])]
    interactive = [c for c in value if not AUTONOMOUS_AUTHORS.search(c[1])]
    # proof-weighted, NET of regressions (the savvy productivity score, not raw count)
    gross = sum(_weight(c[2]) for c in value)
    regress = sum(1.0 for c in commits if REGRESSION.search(c[2]))
    net_score = round(gross - regress, 2)
    auton_score = round(sum(_weight(c[2]) for c in autonomous) - regress, 2)
    return {
        "hours": hours,
        "commits_total": len(commits),
        "value_commits": len(value),
        "autonomous_value": len(autonomous),
        "interactive_value": len(interactive),
        "regressions": int(regress),
        "productivity_net": net_score,               # proof-weighted value − regressions
        "productivity_per_hour": round(net_score / hours, 3) if hours else 0,
        "autonomous_productivity_per_hour": round(auton_score / hours, 3) if hours else 0,
        "merged_decisions": merged_decisions(hours),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=8.0)
    r = run(ap.parse_args().hours)
    print(f"=== PRODUCTIVITY LEDGER — last {r['hours']:g}h ===")
    print(f"  value commits:  {r['value_commits']} of {r['commits_total']}  ·  regressions: {r['regressions']}")
    print(f"  PRODUCTIVITY (proof-weighted, net of regressions): {r['productivity_net']}  "
          f"→ {r['productivity_per_hour']}/hr")
    print(f"  · AUTONOMOUS: {r['autonomous_productivity_per_hour']}/hr   · interactive value: {r['interactive_value']}")
    md = r["merged_decisions"]
    print(f"  decisions merged: {'unknown (merged_at unreliable — a known bug)' if md < 0 else md}")
    print()
    if r["autonomous_value"] == 0:
        print("  ⚠ VERDICT: ZERO autonomous productivity — it monitored, did not advance.")
        print("     Utilization gap ≈ 100%: the $0 substrate could produce; it didn't (loop not closed).")
    else:
        print(f"  VERDICT: {r['autonomous_productivity_per_hour']}/hr autonomous. "
              "Track across windows for acceleration (is the rate itself rising?).")
    print("  (Interim proof-weights by commit-type; TRUE weight needs LIVE-verification wired — intent #3.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
