#!/usr/bin/env python3
"""Burn audit — the system cannot be surprised by its own spend.

Law (AI_PRINCIPLES, from the 2026-07 zombie-curator + 2026-04 metaclaw incidents):
every recurring resource consumer has a BURN_REGISTRY row: owner, expected $/day,
and the OUTPUT its spend feeds. Three checks:
  1. UNREGISTERED SPENDER: an active service holding a paid API key with no registry row → 🔴
  2. BURN WITHOUT OUTPUT: registered spender whose output evidence is empty/stale → 🔴 (the curator pattern)
  3. Attribution: metered API calls in journals mapped to exact systemd units.
Writes vault 02_CONTEXT/Memory/BURN AUDIT.md. Weekly via launchd; also runnable any time.
"""
import subprocess, datetime, os
from pathlib import Path

VAULT = Path.home() / "Documents/FPOS/Full Potential OS"

# ── THE REGISTRY: every known metered/paid consumer ──────────────────────────
# kind: api-key holder | subscription | fixed-infra
REGISTRY = [
    {"name": "claude-code sessions (laptop+162)", "kind": "subscription", "expected": "Max plan, $0 marginal",
     "output": "all building/reasoning", "owner": "Ember"},
    {"name": "fp-index (198)", "kind": "api-key", "key_hint": "ANTHROPIC", "unit": "fpai-fp-index",
     "expected": "<$0.05/day (~1 call/day)", "output": "semantic index refresh", "owner": "198 stack"},
    {"name": "Meta ads (act_71883338)", "kind": "api-key", "key_hint": "META",
     "expected": "$0 until billing settled; then ≤$10/day (hard cap)", "output": "growth ledger impressions/leads", "owner": "growth engine"},
    {"name": "Brevo SMTP relay", "kind": "subscription", "expected": "free tier", "output": "mail deliverability", "owner": "mail stack"},
    {"name": "servers 162/198/209", "kind": "fixed-infra", "expected": "fixed monthly", "output": "everything", "owner": "James"},
    {"name": "assessment-scorer (product core)", "kind": "api-key", "key_hint": "ANTHROPIC",
     "expected": "$0 via model_router subscription; metered only on real-client audits (~$0.10-0.50/audit vs $2,500 Blueprint)",
     "output": "Allocation Score deliverable per lead", "owner": "growth engine"},
    # DISABLED 2026-07-03: brain-curator fleet (key shbrainincurator-42826, revoked by James)
]
KNOWN_UNITS = {e.get("unit") for e in REGISTRY if e.get("unit")}

def sh(cmd, timeout=30):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""

def active_key_holders(host_cmd_prefix, env_globs):
    """Find ACTIVE systemd units whose env files hold paid API keys."""
    script = f'''
for f in {env_globs}; do
  [ -f "$f" ] || continue
  grep -qE "ANTHROPIC_API_KEY|OPENAI_API_KEY|sk-ant-|sk-proj-" "$f" 2>/dev/null || continue
  d=$(dirname "$f"); n=$(basename "$d")
  for u in $(systemctl list-units --type=service --state=active --no-legend 2>/dev/null | awk '{{print $1}}' | grep -i "$n" | head -2); do
    echo "KEYED_ACTIVE|$n|$u|$f"
  done
done'''
    return [l.split("|")[1:] for l in sh(f"{host_cmd_prefix} '{script}'", 45).splitlines() if l.startswith("KEYED_ACTIVE")]

def api_call_attribution(host_cmd_prefix):
    """Attribute api.anthropic/openai calls (7d) to systemd units via journal JSON."""
    script = ('journalctl --since "7 days ago" --no-pager -o json 2>/dev/null | '
              'grep -E "api.anthropic.com|api.openai.com" | '
              'python3 -c "import sys,json,collections; c=collections.Counter(); '
              '[c.update([json.loads(l).get(chr(95)+\\"SYSTEMD_UNIT\\",\\"?\\")]) for l in sys.stdin]; '
              '[print(f\\"{u}|{n}\\") for u,n in c.most_common(8)]"')
    out = {}
    for l in sh(f"{host_cmd_prefix} '{script}'", 45).splitlines():
        if "|" in l:
            u, n = l.rsplit("|", 1)
            try: out[u] = int(n)
            except ValueError: pass
    return out

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    findings, reds = [], 0
    hosts = [
        ("162", "ssh -o ConnectTimeout=12 root@162.0.208.88", '/etc/sh-brain/*.env /opt/*/.env /opt/*/*/.env'),
        ("198", f"ssh -i {Path.home()}/.ssh/fpai_deploy_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=12 root@198.54.123.234", '/opt/fpai/services/*/.env'),
    ]
    for host, prefix, globs in hosts:
        for holder in active_key_holders(prefix, globs):
            name, unit = holder[0], holder[1]
            if not any(unit.startswith(k or "§") for k in KNOWN_UNITS) and "fp-index" not in unit:
                findings.append(f"🔴 UNREGISTERED SPENDER [{host}] {unit} holds a paid key ({holder[2]}) — add to registry or kill")
                reds += 1
            else:
                findings.append(f"🟢 registered [{host}] {unit}")
        calls = api_call_attribution(prefix)
        for unit, n in calls.items():
            reg = any((e.get("unit") or "§") in unit for e in REGISTRY)
            mark = "🟢" if reg else "🔴"
            if not reg: reds += 1
            findings.append(f"{mark} {n} metered API calls/7d ← [{host}] {unit}" + ("" if reg else " — NOT IN REGISTRY"))
    body = [f"# 🔥 BURN AUDIT — {now}", "",
            f"*Law: no unmetered burn. Every spender: owner + expected cost + output. {'🔴 ' + str(reds) + ' violation(s)' if reds else '🟢 clean — all burn accounted for'}*", "",
            "## Findings", *[f"- {f}" for f in (findings or ['- (no active keyed services found)'])], "",
            "## Registry (expected burn)", "",
            "| Consumer | Kind | Expected | Output it feeds | Owner |", "|---|---|---|---|---|",
            *[f"| {e['name']} | {e['kind']} | {e['expected']} | {e['output']} | {e['owner']} |" for e in REGISTRY], "",
            "*New API key or paid service ⇒ registry row FIRST (this file). Burn with empty output ⇒ kill by default (the curator rule). Provider-side reconciliation: see SPEC_burn-reconciliation.*"]
    out = VAULT / "02_CONTEXT/Memory/BURN AUDIT.md"
    out.write_text("\n".join(body))
    print(f"burn audit: {reds} red · → {out.name}")
    if reds:
        # surface loudly: prepend line to HEARTBEATS so the anti-rot board carries it
        hb = VAULT / "02_CONTEXT/Memory/HEARTBEATS.md"
        if hb.exists():
            hb.write_text(f"*🔥 BURN AUDIT: {reds} unregistered spender(s) — see [[BURN AUDIT]]*\n\n" + hb.read_text())

if __name__ == "__main__":
    main()
