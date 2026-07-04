#!/usr/bin/env python3
"""
heartbeat · the anti-rot monitor. Every self-running loop registers here with an
EVIDENCE file (something it must touch when it runs) and a cadence. This checker
compares evidence mtime vs cadence and writes a red/green board to the vault.

Why: July 2–3 forensics — proof log (dead 27d), buildstream board, email canary,
and 162's ALIGNMENT copy all rotted SILENTLY. Rot must become visible in hours.

Runs: launchd com.fpai.heartbeat every 4h + as an fpull step.
Output: vault 02_CONTEXT/Memory/HEARTBEATS.md (+ exit summary for logs).
"""
import json, os, subprocess, datetime
from pathlib import Path

HOME = Path.home()
VAULT = Path(os.environ.get("FPAI_VAULT", HOME / "Documents" / "FPOS" / "Full Potential OS"))
OUT = VAULT / "02_CONTEXT/Memory" / "HEARTBEATS.md"

# name · where · cadence_min · grace(×cadence) · evidence
REGISTRY = [
    # public funnel surfaces (URL liveness)
    {"name": "assessment page (funnel front door)", "where": "url", "cadence": 1440, "grace": 2,
     "evidence": "https://fullpotential.com/assessment"},
    {"name": "remember page (movement door)", "where": "url", "cadence": 1440, "grace": 2,
     "evidence": "https://fullpotential.com/remember"},
    # laptop loops
    {"name": "vault-sync (BRAIN/HOT STATE → vault)", "where": "laptop", "cadence": 30, "grace": 4,
     "evidence": str(HOME / ".config/fpai/vault_sync/vault-sync.stdout.log")},
    {"name": "leads-mailer (applications → email)", "where": "laptop", "cadence": 10, "grace": 12,
     "evidence": str(HOME / ".config/fpai/leads_mailer/stdout.log")},
    {"name": "vault-gardener (nightly hygiene)", "where": "laptop", "cadence": 1440, "grace": 2,
     "evidence": str(VAULT / "02_CONTEXT/Memory" / "VAULT GARDEN LOG.md")},
    {"name": "email canary (POP3 health)", "where": "laptop", "cadence": 360, "grace": 3,
     "evidence": str(HOME / ".config/fpai/email_health/log.jsonl")},
    {"name": "autoloop (2h tick)", "where": "laptop", "cadence": 120, "grace": 4,
     "evidence": str(HOME / ".config/fpai/autoloop/runs.log")},
    {"name": "daily_sync → HOME stamp (via fpull/autoloop)", "where": "laptop", "cadence": 1440, "grace": 2,
     "evidence": str(VAULT / "00_SYSTEM" / "HOME.md")},
    {"name": "burn-audit (weekly · no unmetered burn)", "where": "laptop", "cadence": 10080, "grace": 1.5,
     "evidence": str(VAULT / "02_CONTEXT/Memory" / "BURN AUDIT.md")},
    # 162 loops (checked over ssh in one batch)
    {"name": "162 build loop (10-min tick)", "where": "162", "cadence": 10, "grace": 12,
     "evidence": "journal:fpai-build-loop.service"},
    {"name": "162 build lifecycle alerts (10-min tick)", "where": "162", "cadence": 10, "grace": 12,
     "evidence": "file:/root/.config/fpai/build_alert_state.json"},
    {"name": "162 HOT_STATE synth (30-min)", "where": "162", "cadence": 30, "grace": 4,
     "evidence": "file:/root/.config/fpai/hot_memory/HOT_STATE.md"},
    {"name": "162 campaign watch (2x/day)", "where": "162", "cadence": 720, "grace": 2,
     "evidence": "file:/root/.config/fpai/ads/status.json"},
    {"name": "162 provider burn reconciliation (weekly)", "where": "162", "cadence": 10080, "grace": 1.5,
     "evidence": "file:/root/.config/fpai/burn_audit/reports"},
    {"name": "162 awareness probe (2h)", "where": "162", "cadence": 120, "grace": 4,
     "evidence": "journal:fpai-awareness-reliability.service"},
    {"name": "162 nightly metabolism", "where": "162", "cadence": 1440, "grace": 2,
     "evidence": "journal:fpai-metabolism.service"},
]

def remote_ages():
    """One ssh round-trip: epoch ages (seconds) for all 162 evidence."""
    cmds = []
    for e in REGISTRY:
        if e["where"] != "162":
            continue
        ev = e["evidence"]
        if ev.startswith("file:"):
            cmds.append(f'echo "{e["name"]}|$(( $(date +%s) - $(stat -c %Y "{ev[5:]}" 2>/dev/null || echo 0) ))"')
        else:  # journal:unit
            unit = ev.split(":", 1)[1]
            cmds.append(
                'echo "' + e["name"] + '|$(( $(date +%s) - $(date -d "$(journalctl -u ' + unit +
                ' -n 1 --no-pager -o short-iso 2>/dev/null | tail -1 | cut -d\" \" -f1)" +%s 2>/dev/null || echo 0) ))"')
    try:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=12", "root@162.0.208.88", "; ".join(cmds)],
                           capture_output=True, text=True, timeout=30)
        out = {}
        for line in r.stdout.splitlines():
            if "|" in line:
                k, v = line.rsplit("|", 1)
                try: out[k] = int(v.strip())
                except ValueError: pass
        return out
    except Exception:
        return {}

def check_url(target):
    try:
        r = subprocess.run(["curl", "-sL", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "15", target],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip() == "200"
    except Exception:
        return False

def main():
    now = datetime.datetime.now()
    r_ages = remote_ages()
    rows, missed = [], 0
    for e in REGISTRY:
        limit_min = e["cadence"] * e["grace"]
        if e["where"] == "laptop":
            p = Path(e["evidence"])
            age_min = (now.timestamp() - p.stat().st_mtime) / 60 if p.exists() else None
        elif e["where"] == "url":
            age_min = 0 if check_url(e["evidence"]) else None
        else:
            s = r_ages.get(e["name"])
            age_min = (s / 60) if s and s > 0 and s < 10**9 else None
        if age_min is None:
            status, detail = "🔴 NO EVIDENCE", "evidence file/journal unreadable"
            missed += 1
        elif age_min > limit_min:
            status, detail = "🔴 MISSED", f"last beat {age_min/60:.1f}h ago (limit {limit_min/60:.1f}h)"
            missed += 1
        else:
            status, detail = "🟢", f"{age_min:.0f}m ago"
        rows.append(f"| {status} | {e['name']} | every {e['cadence']}m | {detail} |")

    # unregistered fpai launchd jobs → visibility
    try:
        lj = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
        jobs = [l.split()[-1] for l in lj.splitlines() if "com.fpai." in l]
    except Exception:
        jobs = []
    known_hint = ["vault-sync", "leads-mailer", "vault-gardener", "email-health", "autoloop", "heartbeat"]
    unreg = [j for j in jobs if not any(k in j for k in known_hint)]

    md = "\n".join([
        "---", "type: generated", "status: live",
        f"source: heartbeat check · {now.strftime('%Y-%m-%d %H:%M')}", "---", "",
        "# 💓 HEARTBEATS — every self-running loop, one board",
        "",
        f"*{now.strftime('%Y-%m-%d %H:%M')} · {'🟢 ALL BEATING' if missed == 0 else f'🔴 {missed} loop(s) missed their beat — investigate before anything else'}*",
        "",
        "| status | loop | cadence | last beat |",
        "|---|---|---|---|",
        *rows,
        "",
        f"**Other com.fpai launchd jobs (unmonitored):** {', '.join(unreg) if unreg else 'none'}",
        "",
        "*A 🔴 here means a mirror or automation is silently rotting — the exact failure class that ate the proof log for 27 days. Fix the loop, not the symptom.*",
    ])
    OUT.write_text(md)
    print(f"heartbeat: {len(rows)} loops · missed={missed} → {OUT.name}")

if __name__ == "__main__":
    main()
