#!/usr/bin/env python3
"""
Command Center dashboard builder · v1 · 2026-05-26
Aggregates cartographer index + decision log + intent queue + treasury state +
LaunchAgent status + open priorities into ONE markdown file James can read from
anywhere — the "Your View" panel from the NBM Engine visualization made real.

Output: ~/.config/fpai/command_center/dashboard.md

This is the live counterpart to the NBM Engine visualization's Command Center.
Refreshed by LaunchAgent (next iteration) every 15-30 min · or on-demand via
this script.
"""

import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

HOME = Path.home()
OUT = HOME / ".config" / "fpai" / "command_center" / "dashboard.md"
DECISIONS_LOG = HOME / ".config" / "fpai" / "decisions" / "log.jsonl"
INTENT_QUEUE = HOME / ".config" / "fpai" / "intent_queue" / "queue.jsonl"
CARTOGRAPHER = HOME / ".config" / "fpai" / "cartographer" / "index.md"
TG_INBOX = HOME / ".config" / "fpai" / "tg_inbox" / "messages.jsonl"
MEMORY_DIR = HOME / ".claude" / "projects" / "-Users-jamessunheart-FPAI-Cockpit" / "memory"


def current_time_cr() -> str:
    """Costa Rica time (UTC-6)."""
    utc = datetime.now(timezone.utc)
    cr = utc - timedelta(hours=6)
    return cr.strftime("%A %Y-%m-%d %H:%M CR")


def hl_wallet_state() -> dict:
    """Pull live HL wallet balance via SSH."""
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             "root@198.54.123.234", "python3 /tmp/wallet_check.py 2>/dev/null"],
            capture_output=True, text=True, timeout=15
        )
        output = r.stdout.strip()
        if "balance" in output:
            return {"ok": True, "snippet": output[:300]}
        return {"ok": False, "snippet": "(no live read)"}
    except Exception:
        return {"ok": False, "snippet": "(SSH unavailable)"}


def launch_agents_status() -> list:
    try:
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10)
        out = []
        for line in r.stdout.splitlines():
            if "com.fpai." in line:
                parts = line.split()
                if len(parts) >= 3:
                    pid, status, label = parts[0], parts[1], parts[2]
                    out.append((label, pid, status))
        return out
    except Exception:
        return []


def recent_decisions(limit: int = 8) -> list:
    if not DECISIONS_LOG.exists():
        return []
    lines = DECISIONS_LOG.read_text().splitlines()[-limit:]
    out = []
    for line in lines:
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            et = e.get("event_type", "decision")
            ts = (e.get("timestamp") or e.get("started_at") or "")[:19]
            did = (e.get("decision_id") or "")[:24]
            if et == "decision":
                cost = e.get("total_cost_usd", 0)
                summary = (e.get("ember_summary") or e.get("topic") or "")[:100]
                out.append(("decision", ts, did, f"${cost:.2f} · {summary}"))
            elif et == "ACTIONS_TAKEN":
                n = len(e.get("actions", []))
                sa = (e.get("sub_action") or "")[:80]
                out.append(("actions", ts, did, f"{n} actions · {sa}"))
            elif et == "REVERSAL":
                reason = (e.get("reason") or "")[:80]
                out.append(("reversal", ts, did, reason))
            elif et == "AMBIENT_RESPONDER_RUN":
                out.append(("ambient_run", ts, "responder", "spawn complete"))
            else:
                out.append((et, ts, did, ""))
        except Exception:
            pass
    return out


def open_intents() -> list:
    if not INTENT_QUEUE.exists():
        return []
    out = []
    for line in INTENT_QUEUE.read_text().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if e.get("status", "open") in ("open", "in_progress"):
                out.append(e)
        except Exception:
            pass
    return out


def recent_inbox(limit: int = 5) -> list:
    if not TG_INBOX.exists():
        return []
    lines = TG_INBOX.read_text().splitlines()[-limit:]
    out = []
    for line in lines:
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            t = e.get("type", "?")
            ts = (e.get("received_at") or "")[:19]
            text = (e.get("text") or "")[:120]
            out.append((t, ts, text))
        except Exception:
            pass
    return out


def session_spend_estimate() -> str:
    """Rough estimate from decision log entries (only debates count costs)."""
    if not DECISIONS_LOG.exists():
        return "$0.00 (no log)"
    total = 0.0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for line in DECISIONS_LOG.read_text().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            ts = e.get("timestamp") or e.get("started_at") or ""
            if today in ts or (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d") in ts:
                cost = e.get("total_cost_usd", 0) or e.get("cost_to_execute_usd", 0)
                if isinstance(cost, (int, float)):
                    total += float(cost)
        except Exception:
            pass
    return f"~${total:.2f} (24h estimate from logged events · responder spawns not tracked)"


def top_next_moves() -> list:
    """Surface the current top-3 irreducibly-James moves from canonical memory.
    For v1, hardcoded based on ALIGNMENT.md top-3 trifecta. Future: parse ALIGNMENT.md dynamically."""
    return [
        ("1", "Gauntlet USDC Prime $50K deposit", "Treasury · 1 MetaMask tx · ~2 min · ~$5.6K/yr yield + position-data for substrate to learn", "irreducibly James"),
        ("2", "Bottleneck Session warm-list assembly", "Ventures · 40 min · relationships in James's head · unlocks 14-day launch", "irreducibly James"),
        ("3", "Hold-or-close 3 stuck HL positions + SWEEP_LIVE re-enable", "Treasury · custody decision · then I verify patch on next entry", "irreducibly James"),
    ]


def zen_village_applicants(limit: int = 10) -> dict:
    """Return scored Zen Village applicants ranked by total score."""
    scored_dir = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "scored"
    inbox_dir = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "inbox"
    out = {"scored": [], "inbox_pending": 0}
    if not scored_dir.exists():
        return out
    files = list(scored_dir.glob("*.json"))
    for f in files:
        try:
            data = json.loads(f.read_text())
            out["scored"].append({
                "name": data.get("name", "?"),
                "lane": data.get("lane", "?"),
                "location": data.get("location", "?"),
                "total": data.get("total", 0),
                "tier": data.get("tier", "?"),
                "tier_emoji": data.get("tier_emoji", ""),
                "scores": data.get("scores", {}),
                "summary": (data.get("summary") or "")[:300],
                "flags_count": len(data.get("flags", [])),
                "key_skills": data.get("key_skills", []),
                "availability": data.get("availability", ""),
                "scored_at": data.get("_meta", {}).get("scored_at", ""),
                "filename": f.name,
            })
        except Exception:
            pass
    out["scored"].sort(key=lambda x: x["total"], reverse=True)
    out["scored"] = out["scored"][:limit]
    if inbox_dir.exists():
        out["inbox_pending"] = len(list(inbox_dir.glob("*.json")))
    return out


def render() -> str:
    now_iso = datetime.now(timezone.utc).isoformat()
    cr_time = current_time_cr()
    lines = []
    a = lines.append

    a("# Command Center")
    a("")
    a(f"**{cr_time}** · auto-generated · last refresh `{now_iso[:19]}Z`")
    a("")
    a("> *Clarity at a glance. Peace in the body. You focus on vision, relationships, creation, and restoration. The system handles the mechanics.*")
    a("")
    a("---")
    a("")

    # TOP NEXT MOVES (the visualization's headline panel)
    a("## ⚡ Top Next Moves")
    a("")
    a("*The 3 highest-leverage moves currently queued · all irreducibly James-side*")
    a("")
    for rank, title, detail, tag in top_next_moves():
        a(f"**{rank}. {title}**  ")
        a(f"   {detail}  ")
        a(f"   _{tag}_")
        a("")

    a("---")
    a("")

    # ENERGY STATE (named but not measured · placeholder for proxy design)
    a("## 🌅 Energy State")
    a("")
    a("- **Coherence%:** _(not yet measured · proxy design pending objective function)_")
    a("- **Substrate engagement:** post-midnight Tuesday · 36+ hour arc closing · responder ambient")
    a("- **Trust-tier:** 6.1 (trustee-not-assistant · substrate executes reversibles with safeguards)")
    a("- **Foundation principles active:** all 7 · see `reference_seven_foundation_principles.md`")
    a("")
    a("---")
    a("")

    # TREASURY FLOW
    a("## 💰 Treasury Flow")
    a("")
    hl = hl_wallet_state()
    a("**Live state (where substrate can see):**")
    if hl["ok"]:
        a("```")
        a(hl["snippet"])
        a("```")
    else:
        a(f"- HL wallet: {hl['snippet']}")
    a("")
    a("**Aggregate (from canonical memory · last refresh 2026-05-19):**")
    a("- Liquid total: ~$181k spendable (banks + crypto post-payments)")
    a("- Banks: $65,394 (MACU+Wise+Venmo+Wells+BOA+Bitjungle+Kapi)")
    a("- Bitrue earning section: ~$49,767 ($1,494/yr at 3% APY)")
    a("- Bitrue cash idle: ~$77,400 (post SOL-LONG close)")
    a("- Trust Wallet: ~$26,040 (109.9 SOL + ~$16,588 USDC)")
    a("- HL wallet: real-time above · 3 stuck positions still open · SWEEP_LIVE=0")
    a("")
    a("**Target allocation (per visualization · not yet wired):** 40% Sovereign (BTC) · 40% Hard Assets · 20% Operations")
    a("")
    a("**Yield gap:** ~$94K idle stables earning $0 · Gauntlet USDC Prime path unlocks ~$5.6K/yr at 6% APY (Phase 1 of [[spec-ai-managed-yield-vault]])")
    a("")
    a("---")
    a("")

    # ACTIVE LOOPS
    a("## 🔄 Active Loops")
    a("")
    a("**LaunchAgents currently loaded:**")
    a("")
    for label, pid, status in launch_agents_status():
        marker = "🟢" if pid != "-" else "⚪"
        a(f"- {marker} `{label}` · pid={pid} · status={status}")
    a("")

    a("**Substrate-side ambient loops:**")
    a("- `com.fpai.tg-listen` · TG inbox poll · every 60s")
    a("- `com.fpai.ember-responder` · ambient claude spawn on new inbound · every 5min · smart-loop wired (intent queue + rolling context)")
    a("- `com.fpai.tg-digest-daily` · morning digest push · 08:00 CR")
    a("")

    a("**Intent queue (in-flight intents that persist across spawns):**")
    a("")
    intents = open_intents()
    if not intents:
        a("- (queue empty)")
    else:
        for e in intents:
            sid = e.get("intent_id", "?")
            st = e.get("status", "open")
            desc = (e.get("description") or "")[:120]
            cb = e.get("created_by", "?")
            a(f"- **{sid}** · {st} by {cb} — {desc}")
    a("")

    a("---")
    a("")

    # RECENT DECISIONS
    a("## 📋 Recent Decision Log")
    a("")
    a("**Last 8 events:**")
    a("")
    for et, ts, did, summary in recent_decisions():
        a(f"- `{ts}` · **{et}** · {did} — {summary}")
    a("")

    a("---")
    a("")

    # RECENT INBOUND
    a("## 📥 Recent TG Inbox")
    a("")
    inbox = recent_inbox()
    if not inbox:
        a("- (no inbox entries yet)")
    else:
        for t, ts, text in inbox:
            a(f"- `{ts}` · **{t}** — {text}")
    a("")

    a("---")
    a("")

    # SPEND
    a("## 💸 Substrate Spend")
    a("")
    a(f"- {session_spend_estimate()}")
    a("- Trust-tier 4.1 daily cap: $100/day · substrate auto-executes within cap")
    a("- Cost discipline: each debate ~$0.60 · each responder spawn ~$0.20-0.50")
    a("")

    a("---")
    a("")

    # ZEN VILLAGE APPLICANTS
    a("## 🌿 Zen Village Applicants (scored)")
    a("")
    zv = zen_village_applicants()
    if zv["inbox_pending"]:
        a(f"**{zv['inbox_pending']} application(s) pending in inbox** · run `python3 ~/FPAI_Cockpit/tools/zen_village_scorer/score_applicant.py --batch`")
        a("")
    if not zv["scored"]:
        a("- (no scored applicants yet · drop application JSONs into `~/.config/fpai/zen_village/applicants/inbox/` and run --batch)")
    else:
        a(f"**Top {len(zv['scored'])} ranked by score:**")
        a("")
        for app in zv["scored"]:
            a(f"### {app['tier_emoji']} **{app['name']}** — {app['total']}/100 · {app['tier']}")
            a(f"_{app['lane']} · {app['location']}_  ")
            scores = app.get("scores", {})
            score_line = " · ".join([
                f"Align {scores.get('alignment',{}).get('score','?')}",
                f"Skills {scores.get('skills',{}).get('score','?')}",
                f"Community {scores.get('community_fit',{}).get('score','?')}",
                f"Ready {scores.get('readiness',{}).get('score','?')}",
                f"Depth {scores.get('application_depth',{}).get('score','?')}",
            ])
            a(f"_{score_line}_")
            a("")
            a(f"_{app['summary']}_")
            a("")
            if app["key_skills"]:
                a(f"_Skills:_ {', '.join(app['key_skills'][:6])}")
            if app["availability"]:
                a(f"_Available:_ {app['availability']}")
            if app["flags_count"]:
                a(f"_Flags:_ {app['flags_count']} item(s) to follow up")
            a(f"_File:_ `{app['filename']}`")
            a("")
    a("")

    a("---")
    a("")

    # CARTOGRAPHER LINK
    a("## 🗺️ Cartographer Index")
    a("")
    if CARTOGRAPHER.exists():
        a(f"- Live at `{CARTOGRAPHER}`")
        a(f"- Size: {CARTOGRAPHER.stat().st_size} bytes")
        a(f"- Indexes: identity stack · all memory · core/STATE · core/INTENT/SPECS · agents · tools · LaunchAgents · credentials · narrator sessions · decision log · intent queue")
    else:
        a("- (not yet built)")
    a("")

    a("---")
    a("")

    # FOOTER
    a("## Foundation Principles (active)")
    a("")
    a("1. **COHERENCE FIRST** — Align mind, heart, body, and field")
    a("2. **CIRCULATION OVER EXTRACTION** — Create value that flows and regenerates")
    a("3. **LEVERAGE & FOCUS** — Do less, but better. Multiply impact.")
    a("4. **NERVOUS SYSTEM SOVEREIGNTY** — Protect energy. Expand capacity.")
    a("5. **LONG-TERM ORIENTATION** — Build for generations, not just quarters.")
    a("6. **BEAUTY & TRUTH** — Make it beautiful. Make it true. Make it matter.")
    a("7. **SERVICE & LEGACY** — All systems exist to serve life and future consciousness.")
    a("")
    a("---")
    a("")
    a(f"*Refresh: `python3 /Users/jamessunheart/FPAI_Cockpit/tools/command_center/build_dashboard.py`*")
    a("")
    a(f"*The system creates freedom through intelligent automation.*")

    return "\n".join(lines)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = render()
    OUT.write_text(rendered)
    print(f"Command Center dashboard written to {OUT}")
    print(f"Size: {OUT.stat().st_size} bytes · {len(rendered.splitlines())} lines")


if __name__ == "__main__":
    main()
