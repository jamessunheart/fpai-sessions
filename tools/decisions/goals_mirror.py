#!/usr/bin/env python3
"""
goals_mirror · v1 · 2026-05-31

Build a clear PRIORITY MAP in the Obsidian vault: what the system believes
matters most. Pulls the SAFE structured sections from two read-only sources and
assembles them under one readable map.

  FPAI_Cockpit/core/STATE/AI_GOALS.md   (G1–G4 working goals + open AI questions)
  FPAI_Cockpit/core/STATE/NOW.md        (founder top-3 goals + project ranking)
        │  extract SAFE sections only · redact (reuse now_mirror guard + key/balance net)
        ▼
  vault  00_MEMORY/GOALS MIRROR.md

SAFETY:
  - Deliberately SKIPS AI_GOALS.md's "AI-TO-AI HANDOFF NOTES" block — that's where
    API keys, /etc/*.env paths, and credit balances live. Never extracted.
  - Reuses the now_mirror redaction guard (IPs · $ · private names) as a 2nd net,
    plus extra patterns for API keys + balances.
  - Manual command. Read-only. No background job.

Usage:
  python3 goals_mirror.py          # write the priority map into the vault
  python3 goals_mirror.py --print  # print to stdout, write nothing
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import now_mirror as nm  # reuse the exact same redaction guard

HOME = Path.home()
AI_GOALS = HOME / "FPAI_Cockpit" / "core" / "STATE" / "AI_GOALS.md"
NOW = HOME / "FPAI_Cockpit" / "core" / "STATE" / "NOW.md"

VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
OUT = VAULT / "00_MEMORY" / "GOALS MIRROR.md"

# Defense-in-depth: catch credential/balance shapes the base guard doesn't.
KEY_RE = re.compile(r"\bfps_[A-Za-z0-9]+|\b[0-9a-f]{8,}\.\.\.|\b[0-9a-f]{24,}\b")
BAL_RE = re.compile(r"\b\d[\d,]*\s*fp_credits\b", re.IGNORECASE)


def extract_section(text: str, start_contains: str) -> str:
    """Return a '## ' section whose heading contains start_contains, up to the next '## '."""
    lines = text.splitlines()
    out, capturing = [], False
    for ln in lines:
        if ln.startswith("## ") and start_contains in ln:
            capturing = True
            out.append(ln)
            continue
        if capturing and ln.startswith("## "):
            break
        if capturing:
            out.append(ln)
    return "\n".join(out).strip()


def full_redact(text: str) -> tuple[str, dict]:
    text, counts = nm.redact(text)            # IPs · $ · private names
    text, k = KEY_RE.subn("[REDACTED KEY · SOURCE ONLY]", text)
    text, b = BAL_RE.subn("[REDACTED BALANCE · SOURCE ONLY]", text)
    counts["key"] = k
    counts["balance"] = b
    return text, counts


def build() -> tuple[str, dict]:
    ai = AI_GOALS.read_text(encoding="utf-8")
    now = NOW.read_text(encoding="utf-8")

    # SAFE sections only. The handoff-notes block of AI_GOALS is never read.
    ai_working = extract_section(ai, "ACTIVE AI WORKING GOALS")
    ai_questions = extract_section(ai, "OPEN AI QUESTIONS")
    now_top3 = extract_section(now, "GOALS — top 3")
    now_ranking = extract_section(now, "PROJECT RANKING")

    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Blockers + recommendation are Ember's synthesis (no secrets, authored — not
    # scraped from the key-laden block).
    blockers = (
        "## Blockers\n\n"
        "- **Distribution, not features** — 0 non-James humans in the funnel; this gates the #1 goal.\n"
        "- **Mirror #1 (Founding Steward) unpaired** — Field Coherence's Witness component stays at 0 until James picks a Distance-Weighted Witness.\n"
        "- **No paid offer sold yet** — the 30-day revenue goal needs the first Bottleneck Session out the door.\n"
        "- **Parallel-session drift** — multiple AI sessions edit NOW.md; coordination is manual.\n"
    )
    reco = (
        "## Recommended next action\n\n"
        "★ **Ship + sell the first paid offer (Bottleneck Session).** It's the single move that "
        "both brings a human into the funnel (goal #1) and lands first revenue (the 30-day target). "
        "Everything else is substrate that's already saturated.\n\n"
        "_(Ember's read, 2026-05-31 — derived from the goals + ranking above.)_\n"
    )

    parts = [
        "# GOALS MIRROR",
        "",
        "*The current priority stack — what the system believes matters most. "
        "Readable, redaction-safe map assembled from two SSOTs.*",
        "",
        "- **Sources:** `core/STATE/AI_GOALS.md` + `core/STATE/NOW.md` (read-only)",
        f"- **Mirrored:** {when}",
        "- 🟡 The AI handoff-notes block (API keys, balances) is intentionally **not** mirrored — open the source with James's OK to see it.",
        "",
        "---",
        "",
        "## Top active goals",
        "",
        "### Founder top 3 — from NOW.md",
        "",
        now_top3 if now_top3 else "_(section not found in source)_",
        "",
        "### AI working goals — from AI_GOALS.md",
        "",
        ai_working if ai_working else "_(section not found in source)_",
        "",
        "---",
        "",
        now_ranking if now_ranking else "## PROJECT RANKING\n\n_(not found)_",
        "",
        "---",
        "",
        "## Open decisions",
        "",
        ai_questions if ai_questions else "_(section not found in source)_",
        "",
        "---",
        "",
        blockers,
        "---",
        "",
        reco,
        "---",
        "",
        "*Assembled by `goals_mirror.py` · read-only · no secrets. See [[NOW MIRROR]] · [[PIPELINE MAP]].*",
        "",
    ]
    body = "\n".join(parts)
    body, counts = full_redact(body)
    return body, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="print_only")
    args = ap.parse_args()

    for src in (AI_GOALS, NOW):
        if not src.exists():
            print(f"source not found: {src}", file=sys.stderr)
            return 1

    out, c = build()

    if args.print_only:
        print(out)
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out)
    print(f"wrote GOALS MIRROR.md · redacted {c['ip']} IP · {c['money']} $ · "
          f"{c['name']} names · {c['key']} key · {c['balance']} balance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
