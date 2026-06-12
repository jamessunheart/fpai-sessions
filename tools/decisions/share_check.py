#!/usr/bin/env python3
"""
share_check · v1 · 2026-05-31  ·  THE SHARING GAUNTLET (the security gate)
Before ANY note leaves the device — to a Notion adapter, the Brain Bridge, or a
teammate — it must pass this. Verifies privacy tier + consent + leak scan, returns
ALLOW / BLOCK with reason. Every adapter and bridge call goes through here.

Usage:
  share_check.py "<path-or-glob>" [--to NAME]   # check specific note(s)
  share_check.py --bridge                        # what's safe to expose right now
Reports match-TYPES, never secret values. Read-only.
"""
import re, sys, glob, argparse
from pathlib import Path

VAULT = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
PRIV_HINTS = ("treasury", "sensitive", "resources_sensitive", "server map", "now mirror",
              "comms inbox", "ask ember", "goals mirror", "cost ledger", "financial",
              "the plate", "your plate", "intent", "next action", "privacy", "work ledger", "daily")
LEAK = {
    "IP address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ETH/0x address": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "API key/secret": re.compile(r"(?i)\b(?:api[_-]?key|secret|password|private key|seed phrase|mnemonic|sk-[a-z0-9]{8,})\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b"),
}

def tier(path, t):
    m = re.search(r"^privacy:\s*(private|shared|public)", t, re.M | re.I)
    if m: return m.group(1).lower()
    typ = re.search(r"^type:\s*(\S+)", t, re.M)
    typ = typ.group(1).lower() if typ else ""
    if path.suffix == ".gpg" or any(h in str(path).lower() for h in PRIV_HINTS): return "private"
    if typ in ("concept", "moc", "hub", "blueprint"): return "public"
    return "private"  # default-private (safe)

def share_with(t):
    m = re.search(r"^share_with:\s*\[(.+?)\]", t, re.M)
    return [x.strip().strip('"\'') for x in m.group(1).split(",")] if m else []

def check(path, to):
    t = path.read_text(errors="ignore")
    tr = tier(path, t)
    if tr == "private":
        return ("🔴 BLOCK", "private tier — stays local")
    if tr == "shared":
        allow = share_with(t)
        if not to or to not in allow:
            return ("🔴 BLOCK", f"shared only with {allow or '(none set)'}; recipient '{to}' not authorized")
    hits = [n for n, rx in LEAK.items() if rx.search(t)]
    if hits:
        return ("🔴 BLOCK", f"leak markers present ({', '.join(hits)}) — redact or re-tag private")
    return ("✅ ALLOW", f"{tr} tier, clean")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default="--bridge")
    ap.add_argument("--to", default=None)
    ap.add_argument("--bridge", action="store_true")
    a = ap.parse_args()
    if a.bridge or a.target == "--bridge":
        files = [p for p in VAULT.rglob("*.md") if "_archive" not in str(p)]
        allow = sum(1 for p in files if check(p, None)[0].startswith("✅"))
        print(f"BRIDGE EXPOSURE: {allow} of {len(files)} notes would pass the gauntlet (rest stay local).")
        for p in files:
            v, r = check(p, None)
            if v.startswith("✅"):
                pass
        return
    targets = [Path(x) for x in glob.glob(str(VAULT / a.target)) or glob.glob(a.target)]
    if not targets:
        print("no match:", a.target); return
    for p in targets:
        v, r = check(p, a.to)
        print(f"{v}  {p.name}  — {r}")

if __name__ == "__main__":
    main()
