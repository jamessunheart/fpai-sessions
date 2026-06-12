#!/usr/bin/env python3
"""
now_mirror · v1 · 2026-05-31

Mirror the live founder-state SSOT (core/STATE/NOW.md) into the Obsidian vault
as a READABLE, redaction-safe snapshot. So James + AI can see what the active
system believes is true — without exposing sensitive material.

  FPAI_Cockpit/core/STATE/NOW.md   (read-only source)
        │  read · redact (IPs, $ figures, private names) · trim bulk
        ▼
  vault  00_MEMORY/NOW MIRROR.md

Redaction is CONSERVATIVE by design (over-redact rather than leak):
  - IPv4 addresses        → [REDACTED IP · SOURCE ONLY]
  - dollar figures        → [REDACTED $ · SOURCE ONLY]
  - known private names   → [NAME · SOURCE ONLY]
Source path is preserved at the top so the original can be opened later IF
James explicitly approves.

Manual command. Read-only. No background job.

Usage:
  python3 now_mirror.py          # write the redacted mirror into the vault
  python3 now_mirror.py --print  # print to stdout, write nothing
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SOURCE = HOME / "FPAI_Cockpit" / "core" / "STATE" / "NOW.md"
SOURCE_REL = "FPAI_Cockpit/core/STATE/NOW.md"

VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
MIRROR_FILE = VAULT / "00_MEMORY" / "NOW MIRROR.md"

# Private people-names that appear in the source (invite cohort + hire candidate).
# Redacted so private personal details never land in the vault.
PRIVATE_NAMES = ["Atlás", "Atlas", "Halley", "Josh", "Sierra", "Delaney", "Cheyenne", "Alice"]

IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
# $500-1,500 · $2.5-10k · $805 · $2,222 · $2.5k+
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s?[kK]?\+?(?:\s?[-–]\s?\$?\d[\d,]*(?:\.\d+)?\s?[kK]?\+?)?")


def redact(text: str) -> tuple[str, dict]:
    counts = {"ip": 0, "money": 0, "name": 0}

    def ip_sub(m):
        counts["ip"] += 1
        return "[REDACTED IP · SOURCE ONLY]"

    def money_sub(m):
        counts["money"] += 1
        return "[REDACTED $ · SOURCE ONLY]"

    text = IP_RE.sub(ip_sub, text)
    text = MONEY_RE.sub(money_sub, text)
    for name in PRIVATE_NAMES:
        new, n = re.subn(rf"\b{re.escape(name)}\b", "[NAME · SOURCE ONLY]", text)
        if n:
            counts["name"] += n
            text = new
    return text, counts


def collapse_loops_table(text: str) -> str:
    """Replace the long LOOPS SHIPPED table rows with a one-line summary (cuts bulk)."""
    lines = text.splitlines()
    out, in_loops, rows, replaced = [], False, 0, False
    for ln in lines:
        if ln.startswith("## ") and "LOOPS SHIPPED" in ln:
            in_loops = True
            out.append(ln)
            continue
        if in_loops:
            if ln.startswith("## "):  # next section — stop collapsing
                in_loops = False
                out.append(ln)
                continue
            if re.match(r"^\s*\|", ln):  # a table row
                if re.search(r"\|\s*#\s*\|", ln) or re.match(r"^\s*\|[\s\-:|]+\|?\s*$", ln):
                    continue  # header / separator
                rows += 1
                if not replaced:
                    out.append(f"_({{N}} loops shipped — full table in source: `{SOURCE_REL}`)_")
                    replaced = True
                continue
        out.append(ln)
    text = "\n".join(out)
    return text.replace("{N}", str(rows))


def build(raw: str) -> tuple[str, dict]:
    body = collapse_loops_table(raw)
    body, counts = redact(body)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        "# NOW MIRROR\n\n"
        "*Readable, redaction-safe snapshot of the live founder-state SSOT. "
        "This is what the active system believes is true. Not the original — a "
        "scrubbed mirror.*\n\n"
        f"- **Source:** `{SOURCE_REL}` (read-only)\n"
        f"- **Mirrored:** {when}\n"
        f"- **Redacted:** {counts['ip']} IP(s) · {counts['money']} $ figure(s) · "
        f"{counts['name']} private name(s) → all marked `SOURCE ONLY`\n"
        "- 🟡 To see redacted originals, open the source file — requires James's explicit OK.\n\n"
        "---\n\n"
    )
    # Drop the source's own H1 to avoid a double title.
    body = re.sub(r"^#\s+.*\n", "", body, count=1)
    return header + body.lstrip("\n"), counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="print_only")
    args = ap.parse_args()

    if not SOURCE.exists():
        print(f"source not found: {SOURCE}", file=sys.stderr)
        return 1

    raw = SOURCE.read_text(encoding="utf-8")
    out, counts = build(raw)

    if args.print_only:
        print(out)
        return 0

    MIRROR_FILE.parent.mkdir(parents=True, exist_ok=True)
    MIRROR_FILE.write_text(out)
    print(f"wrote NOW MIRROR.md · redacted {counts['ip']} IP · "
          f"{counts['money']} $ · {counts['name']} names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
