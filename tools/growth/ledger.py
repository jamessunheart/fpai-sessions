#!/usr/bin/env python3
"""Growth Ledger (G1) — the attribution spine of the Marketing Engine.

Every marketing asset is a GENOME (frame·hook·audience·channel·format); every
outcome is a row. Without this, no loop closes — the ad engine can't breed
winners, the Allocator can't score, the CPL half-life can't be measured. This is
the dependency every other component (content/ad/nurture/allocator) writes to.

Design (from vault 'The Marketing Engine — Architecture' + 'Growth Stack Architecture'):
- asset: id, type, genome(json), parent_id, generation, status(alive|killed|champion), cost
- event: asset_id, kind(impression|click|lead|audit|deal), value_usd, ts
- UTM contract: every emitted URL carries utm_campaign=<asset_id> so leads self-attribute.

Growth CCD (the north star, capability-weighted): value-weighted pipeline per $+hour.
Cycle-time is the interest rate (James 2026-07-03) — so we also log build_seconds per
asset, making the acceleration measurable.

$0 — pure SQLite, no external calls. Usage:
  ledger.py --init                              # create the db
  ledger.py --seed-live                         # register the already-live surfaces
  ledger.py --add --type ad --genome '{...}'    # register an asset
  ledger.py --event <asset_id> --kind lead --value 0
  ledger.py --report                            # Growth CCD + per-asset scores
"""
import argparse, json, sqlite3, os, sys
from pathlib import Path

DB = Path(os.environ.get("FPAI_GROWTH_DB", Path.home() / ".config/fpai/growth/ledger.db"))

# route-value weights (BBB v1.4): a Partnership lead is worth more than a newsletter signup
ROUTE_WEIGHT = {"partnership": 5, "blueprint": 4, "savings_split": 4, "advisory": 5,
                "builder": 3, "audit": 2, "signup": 1, "unknown": 1}

SCHEMA = """
CREATE TABLE IF NOT EXISTS asset (
  id TEXT PRIMARY KEY, type TEXT NOT NULL, genome TEXT NOT NULL,
  parent_id TEXT, generation INTEGER DEFAULT 0,
  status TEXT DEFAULT 'alive', cost_usd REAL DEFAULT 0,
  build_seconds REAL, created TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS event (
  id INTEGER PRIMARY KEY AUTOINCREMENT, asset_id TEXT NOT NULL,
  kind TEXT NOT NULL, route TEXT DEFAULT 'unknown', value_usd REAL DEFAULT 0,
  ts TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(asset_id) REFERENCES asset(id)
);
CREATE INDEX IF NOT EXISTS ix_event_asset ON event(asset_id);
"""


def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.executescript(SCHEMA); return c


def add_asset(c, asset_id, type_, genome: dict, parent_id=None, generation=0,
              cost_usd=0.0, build_seconds=None):
    c.execute("INSERT OR REPLACE INTO asset(id,type,genome,parent_id,generation,cost_usd,build_seconds)"
              " VALUES(?,?,?,?,?,?,?)",
              (asset_id, type_, json.dumps(genome), parent_id, generation, cost_usd, build_seconds))
    c.commit(); return asset_id


def record_event(c, asset_id, kind, route="unknown", value_usd=0.0):
    c.execute("INSERT INTO event(asset_id,kind,route,value_usd) VALUES(?,?,?,?)",
              (asset_id, kind, route, value_usd)); c.commit()


def score(c, asset_id) -> dict:
    """CCD score for one asset: capability-weighted pipeline per dollar+hour."""
    a = c.execute("SELECT * FROM asset WHERE id=?", (asset_id,)).fetchone()
    if not a: return {}
    evs = c.execute("SELECT kind,route,value_usd FROM event WHERE asset_id=?", (asset_id,)).fetchall()
    impressions = sum(1 for e in evs if e["kind"] == "impression")
    leads = [e for e in evs if e["kind"] == "lead"]
    pipeline = sum(ROUTE_WEIGHT.get(e["route"], 1) for e in leads)
    deal_value = sum(e["value_usd"] for e in evs if e["kind"] == "deal")
    cost = (a["cost_usd"] or 0) + (a["build_seconds"] or 0) / 3600 * 0  # build time is time-cost, tracked separately
    ccd = (pipeline + deal_value / 1000) / max(cost, 0.01) if cost else pipeline
    return {"id": asset_id, "type": a["type"], "status": a["status"],
            "impressions": impressions, "leads": len(leads),
            "pipeline_weighted": pipeline, "deal_value": deal_value,
            "cost_usd": round(cost, 2), "ccd": round(ccd, 2)}


def report(c) -> str:
    assets = c.execute("SELECT id FROM asset WHERE status!='killed'").fetchall()
    scored = sorted((score(c, a["id"]) for a in assets), key=lambda s: -s["ccd"])
    tot_leads = sum(s["leads"] for s in scored)
    tot_pipe = sum(s["pipeline_weighted"] for s in scored)
    tot_cost = sum(s["cost_usd"] for s in scored)
    growth_ccd = round((tot_pipe) / max(tot_cost, 0.01), 2) if tot_cost else tot_pipe
    lines = [f"# Growth Ledger — {len(scored)} live assets",
             f"Growth CCD (weighted pipeline / $): **{growth_ccd}** · {tot_leads} leads · ${tot_cost} spent", "",
             "| asset | type | impr | leads | pipe | ccd |", "|---|---|---|---|---|---|"]
    for s in scored[:20]:
        lines.append(f"| {s['id'][:28]} | {s['type']} | {s['impressions']} | {s['leads']} | {s['pipeline_weighted']} | {s['ccd']} |")
    return "\n".join(lines)


def seed_live(c):
    """Register the surfaces already live so the ledger reflects reality from row 1."""
    live = [
        ("assessment-promise", "page-variant", {"frame": "promise", "channel": "web", "url": "/assessment"}),
        ("assessment-exec", "page-variant", {"frame": "exec", "channel": "web", "url": "/assessment"}),
        ("assessment-savings", "page-variant", {"frame": "savings", "channel": "web", "url": "/assessment"}),
        ("remember-door", "page", {"frame": "movement", "channel": "web", "url": "/remember"}),
        ("article-allocation-intelligence", "article", {"hook": "the one question", "channel": "seo", "url": "/learn/allocation-intelligence.html"}),
        ("ai-builders", "page", {"frame": "builder", "channel": "web", "url": "/ai-builders"}),
    ]
    for aid, typ, genome in live:
        add_asset(c, aid, typ, genome)
    return len(live)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--seed-live", action="store_true")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--type"); ap.add_argument("--genome"); ap.add_argument("--id")
    ap.add_argument("--event"); ap.add_argument("--kind"); ap.add_argument("--route", default="unknown")
    ap.add_argument("--value", type=float, default=0.0)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    c = conn()
    if a.init: print(f"ledger ready → {DB}")
    if a.seed_live: print(f"seeded {seed_live(c)} live assets")
    if a.add:
        aid = a.id or f"{a.type}-{c.execute('SELECT count(*) FROM asset').fetchone()[0]}"
        add_asset(c, aid, a.type or "asset", json.loads(a.genome or "{}")); print(f"added {aid}")
    if a.event:
        record_event(c, a.event, a.kind or "impression", a.route, a.value); print(f"event: {a.event} {a.kind}")
    if a.report or not any([a.init, a.seed_live, a.add, a.event]):
        print(report(c))


if __name__ == "__main__":
    main()
