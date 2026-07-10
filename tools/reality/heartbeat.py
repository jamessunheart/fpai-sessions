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
    # Four dependency-ordered layers (James 2026-07-10). Each depends on the one above:
    # no engagement without reach, no transformation without engagement, no sustainability
    # without transformation. Transformation is the only irreplaceable step — everything
    # else exists to produce it. The north star is human transformation, not "reality change".
    return {
        "schema": "reality-heartbeat.v2",
        "north_star": "Did we create more human TRANSFORMATION than last week?",
        "direction": {
            "mission": "Unlock every human's full potential (Future Capability / IUM)",
            "current_priority": "Close ONE complete transformation loop (1 post→1 life→1 testimonial)",
            "primary_constraint": "Insufficient Qualified Attention",
            "constraint_note": "created via compelling ideas · trust · distribution · conversation · proof",
        },
        "layers": {
            "L1_reach": {
                "question": "Did anyone notice us?",
                "attention_views": reality["attention_earned_views"],
                "profile_visits": 0,
                "followers_new": 0,
                "dms_received": 0,
            },
            "L2_engagement": {
                "question": "Did anyone engage?",
                "conversations": 0,
                "frameworks_delivered": 0,
                "calls": 0,
                "assessments_real": n_leads,
            },
            "L3_transformation": {  # the irreplaceable step
                "question": "Did anyone benefit?",
                "clients": 0,
                "successes": 0,
                "testimonials": 0,
                "referrals": 0,
                "lives_changed": 0,
            },
            "L4_sustainability": {
                "question": "Can we continue helping people?",
                "revenue_usd": 0,
                "ad_spend_usd": reality["ad_spend_usd"],
                "cash_liquid_usd": 122000,
                "runway": "long (subscription-covered, ~$0 real burn)",
            },
        },
        "learning": {
            "latest_proof": proof["latest_proof"],
            "latest_proof_date": proof["latest_proof_date"],
            "what_worked": "observability un-blinded (2026-07-09) — green now means real",
            "what_failed": "build loop churns funnel-meta-specs (d210-d214); 0 reality change",
        },
        "build": {"capability": "Sufficient", "detail": f"{build_progress()['builds_total']} built, inner-loop proven — NOT the constraint"},
    }


def render_md(hb: dict) -> str:
    d = hb["direction"]
    L = hb["layers"]
    r1, r2, r3, r4 = L["L1_reach"], L["L2_engagement"], L["L3_transformation"], L["L4_sustainability"]
    tz = "🔴" if r3["lives_changed"] == 0 else "🟢"
    lines = [
        "# 🫀 REALITY HEARTBEAT",
        f"_North star · **{hb['north_star']}**_",
        "",
        "## 🧭 DIRECTION",
        f"- Priority · {d['current_priority']}",
        f"- ★ Primary Constraint · **{d['primary_constraint']}**",
        f"  ↳ {d['constraint_note']}",
        "",
        f"## ① REACH — _{r1['question']}_",
        f"- Attention · {r1['attention_views']} views · Profile visits · {r1['profile_visits']} · Followers +{r1['followers_new']} · DMs · {r1['dms_received']}",
        "",
        f"## ② ENGAGEMENT — _{r2['question']}_",
        f"- Conversations · {r2['conversations']} · Frameworks · {r2['frameworks_delivered']} · Calls · {r2['calls']} · Real assessments · {r2['assessments_real']}",
        "",
        f"## ③ TRANSFORMATION {tz} — _{r3['question']}_ (the irreplaceable step)",
        f"- **Lives changed · {r3['lives_changed']}** · Clients · {r3['clients']} · Testimonials · {r3['testimonials']} · Referrals · {r3['referrals']}",
        "",
        f"## ④ SUSTAINABILITY — _{r4['question']}_",
        f"- Revenue · **${r4['revenue_usd']}** · Ad spend · ${r4['ad_spend_usd']} · Cash · ${r4['cash_liquid_usd']:,} · Runway · {r4['runway']}",
        "",
        "## 📚 LEARNING",
        f"- Worked · {hb['learning']['what_worked']}",
        f"- Failed · {hb['learning']['what_failed']}",
        "",
        f"## 🔧 BUILD · Capability: **{hb['build']['capability']}** _(not the constraint)_",
        "",
        "> No git commits. No lines of code. No agent counts.",
        "> Only evidence that intelligence is changing a human life.",
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
