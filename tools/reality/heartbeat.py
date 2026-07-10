#!/usr/bin/env python3
"""Reality Heartbeat — the executive dashboard for OPERATING Full Potential OS.

James 2026-07-10: the shift from BUILDING FPOS → OPERATING FPOS. The metric that
matters is no longer "how sophisticated is the system" but "did it transform reality
more effectively than last week." So this dashboard measures the OUTER LOOP only:

    Reality → Attention → Conversation → Transformation → Proof → Attention

Four quadrants (Direction / Reality / Learning / Build). The Reality quadrant is the
star and deliberately contains NO git commits, NO lines of code, NO agent counts —
those measure the CPU, and the CPU was never the constraint. Only evidence that
intelligence is changing reality: attention earned, conversations, calls, clients,
revenue, proof.

Honest by construction: reads real signal sources, excludes synthetic/test entries,
defaults to 0 (not "unknown") so an empty outer loop reads as the zero it is.

Run: python3 tools/reality/heartbeat.py [--json]
Writes: ~/.config/fpai/reality/heartbeat_latest.{md,json}
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
REPO = Path(__file__).resolve().parents[2]
OUT = HOME / ".config" / "fpai" / "reality"
OUT.mkdir(parents=True, exist_ok=True)

# Anything matching these in a lead/conversation id is a test/synthetic entry, NOT
# real reality. Keep this list honest — a real human never has "smoke-test" in their id.
SYNTHETIC = ("smoke-test", "spottest", "ignore", "probe", "-test", "test-", "alex-rivera",
             "assessment-chat-")  # alex-rivera + the 07-05 chat id are confirmed test leads


def _is_real_lead(name: str) -> bool:
    low = name.lower()
    return not any(marker in low for marker in SYNTHETIC)


def real_leads() -> tuple[int, list[str]]:
    """Real (non-synthetic) leads captured, ever."""
    seen = HOME / ".config/fpai/leads_mailer/seen.txt"
    real: list[str] = []
    try:
        for line in seen.read_text(encoding="utf-8", errors="replace").splitlines():
            name = line.strip()
            if name and _is_real_lead(name):
                real.append(name)
    except OSError:
        pass
    return len(real), real


def attention_signal() -> dict:
    """External attention earned. Today: whatever the one ad shot produced. No inward metrics."""
    ads = HOME / ".config/fpai/ads/live_campaigns.md"
    views = spend = 0.0
    try:
        text = ads.read_text(encoding="utf-8", errors="replace")
        m_v = re.search(r"(\d+)\s+landing-page views", text)
        m_s = re.search(r"Spend\s+\$([\d.]+)", text)
        if m_v:
            views = int(m_v.group(1))
        if m_s:
            spend = float(m_s.group(1))
    except OSError:
        pass
    return {"landing_page_views_total": int(views), "ad_spend_usd_total": round(spend, 2)}


def recent_proof() -> dict:
    """Newest real proof of reality-change (not build proof)."""
    pdir = REPO / "core/INTENT/AGREEMENTS/proofs"
    try:
        proofs = sorted((p.name for p in pdir.glob("*.md")), reverse=True)
    except OSError:
        proofs = []
    newest = proofs[0] if proofs else None
    # date prefix YYYY-MM-DD
    days = None
    if newest:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", newest)
        if m:
            days = m.group(0)
    return {"latest_proof": newest, "latest_proof_date": days, "total_proofs": len(proofs)}


def build_progress() -> dict:
    """The Build quadrant — deliberately minimized. CPU stats, kept small on purpose."""
    audit = HOME / ".config/fpai/reality/_last_activation_audit.json"
    inert = total = None
    try:
        data = json.loads(audit.read_text())
        total = data.get("total")
        inert = data.get("unexplained_inert_count")
    except (OSError, json.JSONDecodeError):
        pass
    return {"builds_total": total, "dead_inert": inert,
            "note": "CPU stats — minimized on purpose; not the constraint"}


def build_heartbeat() -> dict:
    n_leads, leads = real_leads()
    att = attention_signal()
    proof = recent_proof()
    # The Reality quadrant — the outer loop. All real, mostly zero today.
    reality = {
        "attention_earned_views": att["landing_page_views_total"],
        "ad_spend_usd": att["ad_spend_usd_total"],
        "conversations": 0,          # no real conversation store has fired
        "frameworks_delivered": 0,   # only test deliveries (Alex Rivera)
        "calls_booked": 0,
        "clients": 0,
        "revenue_usd": 0,
        "testimonials": 0,
        "referrals": 0,
        "real_leads_ever": n_leads,
        "_excluded_from_this_quadrant": "git commits, lines of code, agent counts (CPU metrics)",
    }
    return {
        "schema": "reality-heartbeat.v1",
        "direction": {
            "north_star": "Unlock every human's full potential (Future Capability / IUM)",
            "current_priority": "Close the OUTER LOOP — Reality→Attention→Proof (not more Build)",
            "biggest_constraint": "NO LIVE DEMAND — nothing drives real humans to the funnel",
        },
        "reality": reality,
        "learning": {
            "latest_proof": proof["latest_proof"],
            "latest_proof_date": proof["latest_proof_date"],
            "total_proofs": proof["total_proofs"],
            "what_worked": "observability un-blinded (2026-07-09) — green now means real",
            "what_failed": "build loop churns funnel-meta-specs (d210-d214); 0 reality change",
        },
        "build": build_progress(),
    }


def render_md(hb: dict) -> str:
    r = hb["reality"]
    d = hb["direction"]
    lz = "🔴" if r["revenue_usd"] == 0 else "🟢"
    lines = [
        "# 🫀 REALITY HEARTBEAT",
        "_Operating FPOS · the metric is: did reality change more than last week?_",
        "",
        "## 🧭 DIRECTION",
        f"- North Star · {d['north_star']}",
        f"- Priority · {d['current_priority']}",
        f"- ★ Biggest Constraint · {d['biggest_constraint']}",
        "",
        "## 🌍 REALITY (the outer loop — no CPU metrics)",
        f"- {lz} Revenue · **${r['revenue_usd']}**",
        f"- Clients · {r['clients']}  ·  Calls booked · {r['calls_booked']}  ·  Testimonials · {r['testimonials']}",
        f"- Conversations · {r['conversations']}  ·  Frameworks delivered · {r['frameworks_delivered']}",
        f"- Attention earned · {r['attention_earned_views']} views (ad spend ${r['ad_spend_usd']})",
        f"- Real leads (ever) · {r['real_leads_ever']}",
        "",
        "## 📚 LEARNING",
        f"- Latest proof · {hb['learning']['latest_proof']} ({hb['learning']['latest_proof_date']})",
        f"- Worked · {hb['learning']['what_worked']}",
        f"- Failed · {hb['learning']['what_failed']}",
        "",
        "## 🔧 BUILD (minimized — not the constraint)",
        f"- Builds · {hb['build']['builds_total']}  ·  Dead/inert · {hb['build']['dead_inert']}",
        "",
        "> No git commits. No lines of code. No agent counts.",
        "> Only evidence that intelligence is changing reality.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    hb = build_heartbeat()
    (OUT / "heartbeat_latest.json").write_text(json.dumps(hb, indent=2), encoding="utf-8")
    md = render_md(hb)
    (OUT / "heartbeat_latest.md").write_text(md, encoding="utf-8")
    if "--json" in sys.argv:
        print(json.dumps(hb, indent=2))
    else:
        print(md, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
