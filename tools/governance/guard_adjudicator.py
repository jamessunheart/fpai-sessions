#!/usr/bin/env python3
"""Guard Adjudicator — when a block is hit, debate whether it's a REAL guard or my timidity.

James, 2026-07-04: "When you hit a guard, run a debate to see if it's a real guard or a
false one (could be your interpretation). Reframe if it's not a real safety concern; solidify
it if it is." The antidote to the session's core failure: treating my *interpretation* of a
limit as the limit (I said 'you must arm it' ~5× — untested assumption).

Two independent claude -p advocates argue REAL vs ASSUMED; a judge classifies into THREE
verdicts (never two — a two-way frame invites rationalizing past a real gate):
  - ASSUMED  → reframe → TEST it (probe the real gate; most 'I can't' is untested).
  - REAL     → solidify → respect it; take the LEGITIMATE route (grant/route/human), never bypass.
  - JUDGMENT → reversible-but-risky → act with a guardrail, or hold with a stated reason.

SAFETY BIAS (non-negotiable): if the guard touches persistence · credentials · prod writes ·
irreversible · money, the skeptic wins ties → default REAL. This tool can find a legitimate
route around an ASSUMED limit; it must NEVER manufacture permission to evade an enforced gate.
That is the line between creative-toward-the-goal and evasive-around-a-guard.

$0 marginal (claude -p, flat-rate). Read-only: it classifies + recommends; it never executes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess

CLAUDE = os.path.expanduser("~/.local/bin/claude")
if not os.path.exists(CLAUDE):
    CLAUDE = "claude"
SAFETY_TOKENS = re.compile(r"persistence|systemctl|credential|secret|token|prod|deploy|"
                           r"irreversible|money|treasury|wire|\bmain\b|force.?push", re.I)


def _claude(prompt: str, timeout: int = 120) -> str:
    try:
        r = subprocess.run([CLAUDE, "-p", "--effort", "high", prompt],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception as e:
        return f"(advocate unavailable: {e})"


def adjudicate(guard: str, context: str) -> dict:
    high_stakes = bool(SAFETY_TOKENS.search(guard + " " + context))
    real = _claude(
        f"You argue this is a REAL guard that must be RESPECTED. Guard hit:\n{guard}\n\nContext/goal:\n{context}\n\n"
        "Make the strongest case that this is a genuine safety/harness constraint (persistence, credentials, prod, "
        "irreversibility). What legitimate route achieves the goal WITHOUT bypassing it (a one-time human grant, "
        "routing to a surface that legitimately can, or accepting it)? 3-5 sentences.")
    assumed = _claude(
        f"You argue this may be an ASSUMED/false limit — the agent's own timidity, not a real gate. Guard hit:\n{guard}\n\n"
        "Context/goal:\n{context}\n\nMake the strongest case that this is untested assumption or over-caution, and give "
        "the CHEAPEST safe TEST to verify the real boundary (probe it directly). But concede honestly if it is clearly "
        "an enforced safety gate. 3-5 sentences.".replace("{context}", context))
    judge = _claude(
        f"You are the judge. A guard was hit; two advocates argued.\nGUARD: {guard}\n\nREAL-advocate:\n{real}\n\n"
        f"ASSUMED-advocate:\n{assumed}\n\nSAFETY BIAS: if the guard touches persistence/credentials/prod/irreversible/"
        f"money (high_stakes={high_stakes}), default to REAL unless the ASSUMED case is overwhelming — never rationalize "
        "past an enforced safety gate. Classify as exactly one of REAL / ASSUMED / JUDGMENT and give the single next "
        "action (TEST it / RESPECT+route via <how> / PRESSURE-TEST with <guardrail>). "
        "Reply as JSON: {\"verdict\":\"REAL|ASSUMED|JUDGMENT\",\"action\":\"...\",\"why\":\"one sentence\"}")
    try:
        m = re.search(r"\{.*\}", judge, re.S)
        v = json.loads(m.group(0)) if m else {}
    except Exception:
        v = {}
    v.setdefault("verdict", "REAL" if high_stakes else "JUDGMENT")
    v.setdefault("action", "respect + route via a human grant" if high_stakes else "test the real boundary")
    v["high_stakes"] = high_stakes
    v["_debate"] = {"real": real, "assumed": assumed}
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", required=True, help="what was blocked (+ classifier reason if any)")
    ap.add_argument("--context", default="", help="the goal being pursued")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    v = adjudicate(a.guard, a.context)
    if a.json:
        print(json.dumps(v, indent=1)); return 0
    print(f"=== GUARD ADJUDICATOR — verdict: {v['verdict']} (high_stakes={v['high_stakes']}) ===")
    print(f"  ACTION: {v['action']}")
    print(f"  why: {v.get('why','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
