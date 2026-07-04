#!/usr/bin/env python3
"""Health self-healer — detect a degradation, apply the SAFE remediation, escalate the rest.

James, 2026-07-04: "implement some kind of self-healing agent on this if you see a concern."
Concern: awareness slid 100→91% over 4h (real — the latest session_insight stopped fitting
the bot's ~1800-char context as insights accumulated to 444).

Design principles (the honest guardrails):
  - NEVER game a metric to make it pass — heal the real thing, or route-to-fix + escalate.
    (Awareness is a known-narrowed metric; "fixing" it by loosening the probe would be theater.)
  - Only take AUTONOMOUS action where a SAFE, REVERSIBLE remediation exists (orphans → reaper).
  - For code-level causes (awareness render), queue the durable fix ONCE and surface it —
    don't mutate live data blindly.
  - Escalate (surface to James/ops) anything it can't safely heal. Never loop on a failure.

Checks + remediations:
  1. build orphans (spec_written+no-branch)   → run build_orphan_reaper  [AUTO-HEAL: safe/reversible]
  2. awareness < THRESHOLD                     → ensure render-fix is queued (once) + log  [ROUTE+ESCALATE]
  3. metric-coherence drift                    → surface (log)  [ESCALATE]

Kill-switch: ~/.config/fpai/health/.disabled  ·  dry-run by default; --execute to act.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
import sys
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
DB = os.environ.get("BRAIN_INDEX_DB_URL",
    "postgres://brain_index:50dc339828327a7a042dca45957a5bab6dc6b4eda3857524ccd014d9acc23a52@127.0.0.1:25432/postgres")
KILL = Path(os.path.expanduser("~/.config/fpai/health/.disabled"))
AWARENESS_THRESHOLD = 0.95
VENV_PY = "/opt/sh-brain-src/.venv/bin/python"


def _db():
    import psycopg
    return psycopg.connect(DB, connect_timeout=5)


def _ops(event, detail):
    try:
        subprocess.run(["python3", str(REPO / "tools/build_loop/ops_log.py"),
                        "self_heal", event, detail[:300], "$0", "", ""], timeout=15)
    except Exception:
        pass


def check_orphans(execute: bool) -> dict:
    with _db() as c, c.cursor() as cur:
        cur.execute("SELECT count(*) FROM brain_index.decisions WHERE spec_written=true "
                    "AND coalesce(build_status,'none')='none' AND coalesce(build_branch,'')=''")
        n = cur.fetchone()[0]
    if n == 0:
        return {"check": "orphans", "state": "ok", "n": 0}
    action = f"{n} build orphans"
    if execute:
        r = subprocess.run([VENV_PY, str(REPO / "tools/build_loop/build_orphan_reaper.py"),
                            "--older-minutes", "30", "--json"], capture_output=True, text=True,
                           timeout=60, env={**os.environ, "BRAIN_INDEX_DB_URL": DB})
        _ops("heal_orphans", f"reaped: {r.stdout.strip()[:200]}")
        return {"check": "orphans", "state": "healed", "n": n, "action": "ran reaper", "out": r.stdout.strip()[:200]}
    return {"check": "orphans", "state": "would-heal", "n": n, "action": "run reaper (safe/reversible)"}


def check_awareness(execute: bool) -> dict:
    try:
        d = json.loads((REPO / "core/BUILD/signals/awareness_reliability.json").read_text())
        rel = float(d["metric"]["reliability"]); reason = d["metric"].get("reason", "")
    except Exception as e:
        return {"check": "awareness", "state": "unknown", "err": str(e)[:100]}
    if rel >= AWARENESS_THRESHOLD:
        return {"check": "awareness", "state": "ok", "reliability": rel}
    # real concern — do NOT game the probe. Ensure the durable render-fix is queued (once).
    tag = "[self-heal:awareness-render]"
    already = False
    try:
        with _db() as c, c.cursor() as cur:
            cur.execute("SELECT count(*) FROM brain_index.decisions WHERE question LIKE %s "
                        "AND coalesce(build_status,'') NOT IN ('merged','rejected')", (f"%{tag}%",))
            already = (cur.fetchone()[0] > 0)
            if execute and not already:
                cur.execute(r"SELECT id FROM brain_index.decisions WHERE id ~ '^d[0-9]+$'")
                did = "d" + str(max(int(r[0][1:]) for r in cur.fetchall()) + 1).zfill(3)
                spec = ("Guarantee the latest session_insight reaches the bot context (awareness root fix). "
                        "verify_awareness/build_context render ~8 insights into ~1800 chars; with 444 insights "
                        "the newest is truncated out → 'latest title missing from bot context' (awareness slid "
                        "100→91%). Fix: in build_context render, ALWAYS include the single latest insight first "
                        "(reserve its char budget before filling older ones), or render newest-first so the "
                        "latest is never the truncated one. Do NOT loosen the probe. Proof: awareness probe "
                        "'latest title in context' passes; reliability recovers. Reversible.")
                cur.execute("INSERT INTO brain_index.decisions (id,question,answer,status,needs_build,"
                            "spec_written,build_spec,build_status,created_at) VALUES "
                            "(%s,%s,'queued by health self-healer (route-to-fix, not metric-gaming)','answered',"
                            "true,false,%s,'none',now())",
                            (did, f"{tag} Latest insight must reach bot context (awareness render fix)", spec))
                c.commit(); _ops("heal_awareness", f"queued render-fix {did} (rel={rel})")
                return {"check": "awareness", "state": "routed-to-fix", "reliability": rel, "queued": did}
    except Exception as e:
        return {"check": "awareness", "state": "concern", "reliability": rel, "err": str(e)[:100]}
    return {"check": "awareness", "state": "concern" if not execute else ("already-queued" if already else "routed"),
            "reliability": rel, "reason": reason, "fix_queued": already}


def check_coherence() -> dict:
    try:
        from tools.governance.metric_coherence import check as mc
        drift = mc()
        if drift:
            _ops("coherence_drift", "; ".join(drift)[:250])
        return {"check": "coherence", "state": "ok" if not drift else "drift-surfaced", "drift": drift}
    except Exception as e:
        return {"check": "coherence", "state": "unknown", "err": str(e)[:100]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="apply safe remediations (default: dry-run)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if KILL.exists():
        print("self-heal disabled (kill-switch present)"); return 0
    results = [check_orphans(a.execute), check_awareness(a.execute), check_coherence()]
    if a.json:
        print(json.dumps(results, indent=1)); return 0
    print(f"=== HEALTH SELF-HEAL ({'EXECUTE' if a.execute else 'dry-run'}) ===")
    for r in results:
        mark = {"ok": "🟢", "healed": "🔧", "would-heal": "🔧?", "routed-to-fix": "📋",
                "already-queued": "📋", "drift-surfaced": "🟡", "concern": "🔴"}.get(r.get("state"), "·")
        print(f"  {mark} {r['check']}: {r['state']}" + (f" — {r}" if r.get("state") not in ("ok",) else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
