#!/usr/bin/env python3
"""Recursive Allocation Self-Audit — the stack improves its own Allocation Score.

James, 2026-07-03: "why can't we leverage our stack to do the thing to improve the
scores? why does it feel natural to you to default to me?" — the Sunheart Principle:
route to substrate everything the substrate can do; James-time is the APEX, the last
resort, never the default.

So this runs the Allocation Intelligence Audit on OUR OWN stack, then for each
improvement it decides — via the Constitution Check already wired into the system —
whether it is AUTONOMOUS (reversible + within cap + aligned → queue it as a build
decision; the loop executes it without James) or RESERVED (money move · James's
personal voice · direction → the short list only James can act on).

The default flips: substrate does the reversible work; James sees only the irreducible.
Run daily (timer) → findings become build missions → build loop improves the scores →
re-audit → repeat. Recursion applied to our own allocation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# The audit's Intelligence Blueprint — each a candidate improvement to a score.
# In v1 the improvements are curated from AUDIT_001; the scorer that regenerates
# them from live metrics is the next iteration (build it from real re-audits).
BLUEPRINT = [
    {"id": "infra-retire-postfix", "dim": "infra",
     "action": "Retire postfix on 198 (outbound already via Brevo); reversible service stop + doc.",
     "build_spec": "Stop+disable postfix on 198, confirm Brevo covers outbound, log rollback. Reversible."},
    {"id": "infra-cruft-services", "dim": "infra",
     "action": "Stop cruft services (cocoon, whaletrack-magnet) flagged in FLEET_SNAPSHOT; free RAM/compute.",
     "build_spec": "Audit + stop non-earning services cocoon/whaletrack on 198 behind a reversible flag; measure RAM reclaimed."},
    {"id": "infra-209-disk", "dim": "infra",
     "action": "Identify top growth dirs on 209 before disk hits 90% (~6mo runway).",
     "build_spec": "Report 209 top-growth directories; propose reversible cleanup. Read-only analysis first."},
    {"id": "capital-yield-56k", "dim": "capital",
     "action": "Move $56k MACU @ 0% to safe yield (~$2.8k/yr) OR release against proof milestones.",
     "build_spec": "MOVE MONEY $56k from MACU to yield. Treasury signature required."},
    {"id": "revenue-send-audit-1", "dim": "revenue",
     "action": "Send the first Allocation Audit offer to a warm contact.",
     "build_spec": "SEND public outreach under James's name to a warm relationship contact."},
    {"id": "revenue-inbound-funnel", "dim": "revenue",
     "action": "Run the ai-builders inbound funnel + publish Audit #001 as the proof asset.",
     "build_spec": "Publish the FPOS Allocation Score proof page + keep the ai-builders funnel warm. Reversible, no personal outreach."},
]


def churn_signal(db_url: str) -> dict | None:
    """The 'churn bites' sensor — turns the vague promise into a measured trigger.

    James asked: is there a trigger for when wake-churn/polling latency actually
    bites, so the event-driven rebuild (#2) builds itself? This is it.

    The reliable, available signal is BACKLOG PERSISTENCE: decisions that sit
    answered + needs_build + unbuilt past 2× the build poll interval (10min → 20min).
    A few of those = polling can't drain fast enough → event-driven firing pays off.
    Threshold ≥3 so a single stalled/orphaned spec (a stall is RCA's job, not a
    polling problem) does not false-trigger.

    Returns an event-driven BLUEPRINT item (which then flows through the same
    classify → queue pipe as every other finding) or None if the signal is quiet.
    """
    try:
        import psycopg
    except Exception:
        return None
    try:
        with psycopg.connect(db_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), coalesce(max(extract(epoch from (now()-created_at))/60)::int,0) "
                "FROM brain_index.decisions "
                "WHERE needs_build=true AND coalesce(build_status,'none')='none' "
                "AND status='answered' AND created_at < now() - interval '20 min'")
            n, age = cur.fetchone() or (0, 0)
    except Exception:
        return None
    if (n or 0) < 3:
        return None
    return {
        "id": "infra-loops-event-driven", "dim": "infra",
        "action": f"Loop churn bites: {n} decisions unbuilt >20min (oldest {age}min) — "
                  "polling can't drain. Fire build loop on decision-queued event, not clock.",
        "build_spec": "Make the build loop event-driven: fire on a decision reaching "
                      "answered+needs_build (DB NOTIFY / queue trigger) instead of a fixed "
                      "10-min poll. Keep the timer as a fallback heartbeat. Reversible.",
    }


def classify(item: dict) -> dict:
    """AUTONOMOUS vs RESERVED — decided by the Constitution Check, not by deference."""
    try:
        from tools.governance.constitution_check import check_proposal
        cc = check_proposal({"title": item["action"], "kind": "self_audit_improvement",
                             "build_spec": item.get("build_spec", "")}, write_ledger=False)
        return {"lane": "autonomous" if cc.get("accepted") else "reserved",
                "reasons": cc.get("reasons", [])}
    except Exception as e:
        return {"lane": "reserved", "reasons": [f"check unavailable: {e}"]}


def queue_decision(item: dict, db_url: str) -> str | None:
    """Queue an autonomous improvement as a build decision (the loop executes it)."""
    try:
        import psycopg
    except Exception:
        return None
    tag = f"[self-audit:{item['id']}]"
    q = f"{tag} Improve Allocation Score ({item['dim']}): {item['action']}"
    try:
        with psycopg.connect(db_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM brain_index.decisions WHERE question LIKE %s "
                        "AND created_at > NOW() - make_interval(days => 7) "
                        "AND coalesce(build_status,'') NOT IN ('merged','rejected')", (f"%{tag}%",))
            if (cur.fetchone() or [0])[0] > 0:
                return "dedup"
            cur.execute(r"SELECT id FROM brain_index.decisions WHERE id ~ '^d[0-9]+$'")
            nums = [int(r[0][1:]) for r in cur.fetchall()]
            did = "d" + str((max(nums) + 1) if nums else 1).zfill(3)
            cur.execute("INSERT INTO brain_index.decisions (id, question, answer, status, needs_build, "
                        "spec_written, build_spec, build_status, created_at) VALUES "
                        "(%s,%s,'queued by recursive self-audit (Sunheart: substrate does the reversible work)',"
                        "'answered', true, false, %s, 'none', now())",
                        (did, q, item.get("build_spec", "")[:8000]))
            conn.commit()
            return did
    except Exception:
        return None


def run(execute: bool) -> dict:
    autonomous, reserved = [], []
    blueprint = list(BLUEPRINT)
    # Dynamic finding: the churn sensor appends the event-driven build only when it bites.
    db = os.environ.get("BRAIN_INDEX_DB_URL", "")
    if db:
        sig = churn_signal(db)
        if sig:
            blueprint.append(sig)
    for item in blueprint:
        c = classify(item)
        (autonomous if c["lane"] == "autonomous" else reserved).append({**item, **c})
    result = {"autonomous": autonomous, "reserved": reserved}
    if execute:
        db = os.environ.get("BRAIN_INDEX_DB_URL", "")
        if db:
            for item in autonomous:
                item["queued"] = queue_decision(item, db)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true", help="Queue autonomous improvements as build decisions.")
    args = ap.parse_args(argv)
    r = run(args.execute)
    print("=== AUTONOMOUS (substrate does these — build loop executes, no James) ===")
    for i in r["autonomous"]:
        print(f"  [{i['dim']}] {i['action']}" + (f"  → {i.get('queued')}" if args.execute else ""))
    print("\n=== RESERVED (only James — money · his voice · direction) ===")
    for i in r["reserved"]:
        print(f"  [{i['dim']}] {i['action']}  ({'; '.join(i['reasons'])[:60]})")
    print(f"\n{len(r['autonomous'])} autonomous · {len(r['reserved'])} reserved — "
          "the default flipped from James to substrate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
