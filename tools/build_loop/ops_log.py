#!/usr/bin/env python3
"""ops_log — the operations truth ledger (both labs' #1, 2026-06-15).

Every autonomous loop writes ONE row here per action so the digest + bot report MEASURED
reality (not journal-grep / self-talk). Append-only JSONL. Makes silent failure VISIBLE and
gives the recursion a gradient. $0.

  append:  ops_log.py <loop> <event> [detail] [cost] [artifact] [next_action]
           events: ran · skipped · attempted · succeeded · failed · proposed · merged · reversed
  read:    ops_log.py --summary [hours]      -> JSON {window_h, by_event, fails, last_action, lines}
           ops_log.py --tail [n]             -> last n rows, human-readable
"""
import json, sys, os, datetime

LEDGER = os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl")


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
    }
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    print("logged:", row["loop"], row["event"])


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


def tail(n=15):
    for r in _rows()[-int(n):]:
        print(f"[{r.get('ts','')}] {r.get('loop','?'):12} {r.get('event','?'):10} {r.get('detail','')[:70]}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--summary":
        summary(a[1] if len(a) > 1 else 24)
    elif a and a[0] == "--tail":
        tail(a[1] if len(a) > 1 else 15)
    else:
        append(a)
