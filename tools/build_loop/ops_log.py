#!/usr/bin/env python3
"""ops_log — the operations truth ledger (both labs' #1, 2026-06-15).

Every autonomous loop writes ONE row here per action so the digest + bot report MEASURED
reality (not journal-grep / self-talk). Append-only JSONL. Makes silent failure VISIBLE and
gives the recursion a gradient. $0.

  append:  ops_log.py <loop> <event> [detail] [cost] [artifact] [next_action]
           events: ran · skipped · attempted · succeeded · failed · proposed · merged · reversed
           SURFACE: set env FPAI_SURFACE to tag which rung handled it (the descent-ladder instrument).
           values: terminal · phone-ssh · phone-claude · tg-trigger · system-proposed · auto-merge
                   (default 'auto-loop' = the autonomous server loop wrote it)
  read:    ops_log.py --summary [hours]      -> JSON {window_h, by_event, fails, last_action, lines}
           ops_log.py --tail [n]             -> last n rows, human-readable
           ops_log.py --surfaces [days]      -> the descent-ladder rollup: % of builds that still
                                                needed the laptop (rung 0). "Builder mode shrinking"
                                                stops being a hope and becomes a line on a chart.
"""
import json, sys, os, datetime

LEDGER = os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl")

# The descent ladder (James 2026-06-15): a build enters at whatever rung the system can handle;
# over time each task-class ratchets DOWN a rung as trust + tooling improve = less James.
RUNG = {
    "terminal": 0,         # laptop Claude Code — heaviest
    "phone-claude": 1,     # full Claude Code agent from the phone (SSH+tmux / web) — laptop power, no laptop
    "phone-ssh": 1,        # raw pocket shell on 162
    "tg-trigger": 2,       # James types "build: X" in Telegram → loop builds
    "system-proposed": 3,  # loop surfaces issue AND fix → James rules
    "auto-merge": 4,       # AI-approved safe builds self-merge → James notified, can veto — lightest
    "auto-loop": 4,        # autonomous server loop default
}


def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def append(argv):
    row = {
        "ts": _now(),
        "loop": argv[0] if len(argv) > 0 else "?",
        "event": argv[1] if len(argv) > 1 else "?",
        "detail": argv[2] if len(argv) > 2 else "",
        "cost": argv[3] if len(argv) > 3 else "$0",
        "artifact": argv[4] if len(argv) > 4 else "",
        "next": argv[5] if len(argv) > 5 else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    print("logged:", row["loop"], row["event"], "·", row["surface"])


def _rows(hours=None):
    if not os.path.exists(LEDGER):
        return []
    cutoff = None
    if hours:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=float(hours))
    out = []
    for ln in open(LEDGER, errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if cutoff:
            try:
                if datetime.datetime.strptime(r["ts"], "%Y-%m-%dT%H:%M:%SZ") < cutoff:
                    continue
            except Exception:
                pass
        out.append(r)
    return out


def summary(hours=24):
    rows = _rows(hours)
    by = {}
    for r in rows:
        by[r.get("event", "?")] = by.get(r.get("event", "?"), 0) + 1
    fails = [r for r in rows if r.get("event") in ("failed", "error")]
    actions = [r for r in rows if r.get("next")]
    print(json.dumps({
        "window_h": hours,
        "by_event": by,
        "fails": [f"{r['loop']}: {r['detail']}" for r in fails][:5],
        "last_action_needed": (actions[-1]["next"] if actions else ""),
        "lines": len(rows),
    }))


def surfaces(days=7):
    """The descent-ladder rollup: where did build-work happen, and what share still needed the laptop?"""
    rows = [r for r in _rows(float(days) * 24) if r.get("event") in ("succeeded", "merged", "proposed", "attempted", "failed", "ran")]
    by_surface = {}
    for r in rows:
        s = r.get("surface", "unlabeled")
        by_surface[s] = by_surface.get(s, 0) + 1
    total = sum(by_surface.values())
    rung0 = by_surface.get("terminal", 0)
    laptop_share = round(100.0 * rung0 / total, 1) if total else 0.0
    # average rung (lower = lighter = less James); unlabeled excluded from the average
    weighted = [(by_surface[s] * RUNG[s], by_surface[s]) for s in by_surface if s in RUNG]
    avg_rung = round(sum(w for w, _ in weighted) / sum(n for _, n in weighted), 2) if weighted else None
    print(json.dumps({
        "window_days": float(days),
        "total_build_actions": total,
        "by_surface": dict(sorted(by_surface.items(), key=lambda kv: RUNG.get(kv[0], 9))),
        "rung0_laptop_share_pct": laptop_share,
        "avg_rung_lower_is_lighter": avg_rung,
        "north_star": "drive rung0_laptop_share toward 0 per task-class = builder mode shrinking",
    }, indent=2))


def tail(n=15):
    for r in _rows()[-int(n):]:
        print(f"[{r.get('ts','')}] {r.get('loop','?'):12} {r.get('event','?'):10} {r.get('surface','?'):14} {r.get('detail','')[:60]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--summary":
        summary(a[1] if len(a) > 1 else 24)
    elif a and a[0] == "--tail":
        tail(a[1] if len(a) > 1 else 15)
    elif a and a[0] == "--surfaces":
        surfaces(a[1] if len(a) > 1 else 7)
    else:
        append(a)
