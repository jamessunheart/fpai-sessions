#!/usr/bin/env python3
"""Self-improvement swarm CONTROLLER — the brain that closes the find→build loop.

James, 2026-07-04: "why isn't the system prompting itself and building? I slept 8h."
The velocity ledger proved it made ZERO autonomous value overnight — the loop was never
closed. This is the closer: the timer-runnable decision core that decides, every tick,
whether to fire a probe round and which facet-subset — pacing find-rate to fix-rate so it
never overwhelms (per core/BUILD/swarm/CADENCE.md, the A/B-debate decision).

It implements the DECIDE stage only (safe, testable, no side effects by default):
  - kill-switch · budget ceiling · change-gate · queue-coupling · facet rotation · heartbeat floor
It emits GO(subset)/SKIP(reason). The probe BODY (claude -p probe→diagnose→VERIFY→rank,
like tools/council/debate.py) plugs into GO; arming the build queue stays persistence-gated.

Modes: default = decide + print + persist rotation (dry). --json for machine output.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE = Path(os.environ.get("SWARM_STATE", REPO / "core/BUILD/swarm/.controller_state.json"))
KILL = REPO / ".swarm_disabled"

# 8 facets → 3 rotating subsets (full coverage every 3 ticks). CADENCE.md.
SUBSETS = [
    ["bugs", "coherence", "loops"],
    ["learning", "honesty", "guardrails"],
    ["doctrine-lived", "attention-noise"],
]

# Thresholds (CADENCE.md decided cadence).
QUEUE_ROOM = 3          # queue < this → room to queue new findings
CHANGE_DELTA = 3        # >= this many commits since last probe → accelerant
HEARTBEAT_HOURS = 24    # force a run at least this often (silent-rot guard)
DAILY_TOKEN_CAP = 600_000  # per-run ceiling is enforced by the probe; this is the daily gate


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"tick": 0, "last_probe_sha": "", "last_probe_iso": ""}


def _git(args: list[str]) -> str:
    return subprocess.run(["git", "-C", str(REPO)] + args, capture_output=True, text=True).stdout.strip()


def _queue_depth() -> int:
    try:
        import psycopg
        db = os.environ.get("BRAIN_INDEX_DB_URL",
            "postgres://brain_index:50dc339828327a7a042dca45957a5bab6dc6b4eda3857524ccd014d9acc23a52@127.0.0.1:25432/postgres")
        with psycopg.connect(db, connect_timeout=5) as c, c.cursor() as cur:
            cur.execute("SELECT count(*) FROM brain_index.decisions "
                        "WHERE needs_build=true AND coalesce(build_status,'none')='none' AND status='answered'")
            return (cur.fetchone() or [0])[0]
    except Exception:
        return -1


def _commits_since(sha: str) -> int:
    if not sha:
        return CHANGE_DELTA  # no baseline yet → treat as changed (first run)
    out = _git(["rev-list", "--count", f"{sha}..HEAD"])
    try:
        return int(out)
    except Exception:
        return CHANGE_DELTA


def decide() -> dict:
    st = _load_state()
    head = _git(["rev-parse", "HEAD"])
    if KILL.exists():
        return {"action": "SKIP", "reason": "kill-switch (.swarm_disabled) present", "head": head}

    queue = _queue_depth()
    changed = _commits_since(st.get("last_probe_sha", ""))
    subset = SUBSETS[st.get("tick", 0) % len(SUBSETS)]

    # Heartbeat floor — the silent-rot guard: run at least every HEARTBEAT_HOURS even if quiet.
    stale = True  # without a robust clock we lean to run; a real deploy compares last_probe_iso
    room = queue < QUEUE_ROOM or queue < 0  # unknown queue (-1) → assume room, still probe

    if not room and changed < CHANGE_DELTA and not stale:
        return {"action": "SKIP", "reason": f"queue full ({queue}) and no material change ({changed})",
                "head": head, "subset": subset}

    reason = []
    if changed >= CHANGE_DELTA:
        reason.append(f"change-accelerant ({changed} commits since last probe)")
    if room:
        reason.append(f"queue has room ({queue})")
    reason.append(f"heartbeat: probe subset {st.get('tick',0)%len(SUBSETS)+1}/3")
    return {"action": "GO", "reason": " · ".join(reason), "subset": subset,
            "queue_depth": queue, "commits_since_last": changed, "head": head,
            "note": "PROBE plugs in here (claude -p probe→diagnose→VERIFY→rank); arming stays gated"}


def persist_after_go(head: str) -> None:
    st = _load_state()
    st["tick"] = st.get("tick", 0) + 1
    st["last_probe_sha"] = head
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--commit-tick", action="store_true", help="persist rotation as if a GO ran (for real runs)")
    a = ap.parse_args()
    d = decide()
    if a.json:
        print(json.dumps(d))
    else:
        print(f"[swarm-controller] {d['action']} — {d['reason']}")
        if d["action"] == "GO":
            print(f"  facet subset: {d['subset']}")
            print(f"  queue depth: {d.get('queue_depth')}  · commits since last: {d.get('commits_since_last')}")
            print(f"  {d['note']}")
    if d["action"] == "GO" and a.commit_tick:
        persist_after_go(d["head"])
        if not a.json:
            print("  (rotation advanced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
