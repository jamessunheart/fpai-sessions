#!/usr/bin/env python3
"""
privacy_audit · v1 · 2026-05-31
Classify every vault note into a privacy tier (frontmatter `privacy:` or an inferred
proposal) and flag leak risk — sensitive markers sitting in shareable notes. The
foundation of the Personal Brain security model. Reports match TYPES, never the
secret values themselves. Read-only; writes one report. Runs with `fpull`.
"""
import re, glob, os
from datetime import datetime, timezone
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
OUT = VAULT / "00_MEMORY" / "PRIVACY AUDIT.md"

# name/path hints that imply PRIVATE
PRIV_HINTS = ("treasury", "sensitive", "resources_sensitive", "server map", "now mirror",
              "comms inbox", "ask ember", "goals mirror", "cost ledger", "financial",
              "your plate", "intent", "next action", "scan ledger", "permission matrix")
# HIGH-severity leak markers (report type, not value)
LEAK = {
    "IP address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ETH/0x address": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "API key/secret": re.compile(r"(?i)\b(?:api[_-]?key|secret|password|private key|seed phrase|mnemonic|sk-[a-z0-9]{8,})\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b"),
}

def fm_tier(t):
    m = re.search(r"^privacy:\s*(private|shared|public)", t, re.M | re.I)
    return m.group(1).lower() if m else None

def fm_type(t):
    m = re.search(r"^type:\s*(\S+)", t, re.M)
    return m.group(1).lower() if m else ""

def infer(path, t):
    low = (str(path) + " " + t[:400]).lower()
    typ = fm_type(t)
    if any(h in str(path).lower() for h in PRIV_HINTS):
        return "private (proposed)"
    if path.suffix == ".gpg":
        return "private (encrypted)"
    if typ in ("concept", "moc", "hub", "blueprint"):
        return "public-candidate (proposed)"
    if typ in ("inbox", "dialogue", "policy", "generated"):
        return "private (proposed)"
    return "review (proposed)"

def main():
    tiers = {}
    leaks = []
    shareable = []
    for p in VAULT.rglob("*.md"):
        if "_archive" in str(p):
            continue
        t = p.read_text(errors="ignore")
        tier = fm_tier(t) or infer(p, t)
        tiers[tier] = tiers.get(tier, 0) + 1
        is_shareable = tier.startswith("public") or tier.startswith("shared")
        if is_shareable:
            shareable.append(p.stem)
            hits = [name for name, rx in LEAK.items() if rx.search(t)]
            if hits:
                leaks.append((p.stem, hits))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = ["---", "type: generated", "status: live", f"source: privacy_audit · {ts}", "---", "",
         "# 🔐 PRIVACY AUDIT", "",
         f"*Vault privacy posture · {ts} · re-run `privacy_audit.py` (or `fpull`). Reports match-types, never secret values. Standard: [[PRIVACY]].*", "",
         "## Tier counts", ""]
    for k, v in sorted(tiers.items(), key=lambda x: -x[1]):
        L.append(f"- **{k}**: {v}")
    L += ["", f"## Bridge-exposable now ({len(shareable)} notes)",
          "*Only these could leave the device over the [[Brain Bridge]] (public/shared tiers). Everything else stays 🔒 local.*", ""]
    if leaks:
        L += ["", "## ⚠️ LEAK FLAGS — sensitive markers in shareable notes (review!)", ""]
        for name, hits in leaks:
            L.append(f"- 🔴 **{name}** — contains: {', '.join(hits)} → re-tag `privacy: private` or redact")
    else:
        L += ["", "## ✅ No leak flags", "*No high-severity markers (IPs / addresses / keys / emails) found in shareable-tier notes.*"]
    L += ["", "---", "", "*Most notes default to 🔒 private until tagged. Standard: [[PRIVACY]] · kit: [[PERSONAL BRAIN STARTER KIT]].*", ""]
    OUT.write_text("\n".join(L))
    print(f"privacy audit → {OUT.name} · tiers={tiers} · shareable={len(shareable)} · leak-flags={len(leaks)}")

if __name__ == "__main__":
    main()
