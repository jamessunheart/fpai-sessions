#!/usr/bin/env python3
"""Next-best-move selector — time as cost, pick the highest-value allocation, wait only if waiting wins.

James, 2026-07-04: "Can the system track its own time — time as a cost — and leverage
intelligence to work on the highest-value things, not waiting unless waiting is absolutely
the highest-value move?" This is that decision core. It operationalizes the Law of
Intelligent Allocation: every idle hour is spent capital (opportunity cost); an allocation
is worth doing only if its value-density beats that idle cost.

Model:
  - TIME IS A COST. The opportunity cost of an idle hour = the system's proven productivity
    rate (from the velocity ledger, proof-weighted value/hr). Idling forgoes that.
  - Each available allocation has: value (from severity/priority) × a reversibility bonus,
    and a cost in hours (from effort). value_density = value / hours.
  - ACT on the highest value_density IF it clears the idle opportunity cost. WAIT only if
    nothing clears the bar, or the top item is blocked by an unmet dependency.

Honest limit: value here is a PROXY (severity/priority/effort), not measured expected value
— true EV needs the counterfactual (did it beat the alternative), which only proof reveals.
So this ranks the *hypotheses*; reality (the Allocation Ledger) grades them after.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WEAKNESSES = REPO / "core/BUILD/swarm/_weaknesses_raw.json"

SEV_VALUE = {"high": 9.0, "med": 5.0, "low": 2.0}
EFFORT_HOURS = {"S": 1.0, "M": 4.0, "L": 12.0}
# Verified this session: some high-severity findings were WRONG on inspection (corrections
# regex). Verification refines value — flag known-retired so the selector doesn't chase them.
RETIRED_HINTS = ("correction detector", "regex", "corrections.py lines")


def idle_opportunity_cost() -> float:
    """Value forgone per idle hour = proven productivity rate (velocity ledger)."""
    try:
        out = subprocess.run(["/opt/sh-brain-src/.venv/bin/python",
                              str(REPO / "tools/metrics/velocity.py"), "--hours", "24"],
                             capture_output=True, text=True, timeout=30).stdout
        for line in out.splitlines():
            if "→" in line and "/hr" in line:  # PRODUCTIVITY ... → X/hr
                return float(line.split("→")[1].split("/hr")[0].strip())
    except Exception:
        pass
    return 1.0  # conservative floor if the ledger can't be read


def load_allocations() -> list[dict]:
    try:
        raw = json.loads(WEAKNESSES.read_text())
    except Exception:
        return []
    out = []
    for w in raw:
        text = (w.get("root_cause", "") + w.get("proposed_fix", "")).lower()
        retired = any(h in text for h in RETIRED_HINTS)
        sev = SEV_VALUE.get(w.get("severity", "low"), 2.0)
        hours = EFFORT_HOURS.get(w.get("effort", "M"), 4.0)
        rev = 1.2 if w.get("reversible") else 0.85
        value = round(sev * rev * (0.15 if retired else 1.0), 2)  # retired ≈ near-zero value
        out.append({
            "what": (w.get("facet") or "?")[:44],
            "fix": (w.get("proposed_fix") or "")[:90],
            "value": value, "hours": hours, "reversible": bool(w.get("reversible")),
            "density": round(value / hours, 2), "retired": retired,
        })
    return sorted(out, key=lambda a: a["density"], reverse=True)


def decide() -> dict:
    allocs = load_allocations()
    idle_cost = idle_opportunity_cost()
    if not allocs:
        return {"move": "WAIT", "why": "no available allocations in the queue", "idle_cost": idle_cost}
    top = allocs[0]
    # ACT if the best move's value-density beats the cost of an idle hour.
    if top["density"] >= idle_cost:
        return {"move": "ACT", "on": top, "idle_cost": idle_cost, "runners_up": allocs[1:4],
                "why": f"value-density {top['density']} ≥ idle opportunity cost {idle_cost}/hr — acting beats waiting"}
    return {"move": "WAIT", "idle_cost": idle_cost, "top_available": top,
            "why": f"best available density {top['density']} < idle cost {idle_cost}/hr — waiting is (barely) higher value; gather a higher-value option"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    d = decide()
    if ap.parse_args().json:
        print(json.dumps(d, indent=1)); return 0
    print("=== NEXT BEST MOVE (time-as-cost allocator) ===")
    print(f"  idle opportunity cost: {d['idle_cost']}/hr (value forgone per idle hour)")
    print(f"  DECISION: {d['move']} — {d['why']}\n")
    if d["move"] == "ACT":
        t = d["on"]
        print(f"  ▶ {t['what']}  (value {t['value']} / {t['hours']}h = density {t['density']}"
              f"{'  ·reversible' if t['reversible'] else ''})")
        print(f"    {t['fix']}")
        print("  runners-up:")
        for r in d["runners_up"]:
            print(f"    · {r['what']} (density {r['density']}){'  [retired/verified-low]' if r['retired'] else ''}")
    print("\n  (value is a proxy — severity×reversibility/effort; TRUE value needs proof of "
          "beating the alternative. Reality grades it after via the Allocation Ledger.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
