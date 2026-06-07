#!/usr/bin/env python3
"""Handoff bridge — turn any spec into a single paste-ready Codex kickoff.

Cuts James's Codex handoff to one copy-paste: Ember drafts the spec, this emits
the exact prompt (orientation files + the spec + the build contract) for James to
drop into Codex desktop/phone/cloud. Optionally appends it to the HANDOFF 📤 lane.

Usage:
    python3 tools/handoff/kickoff.py --spec SPEC_auto-routing [--post]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

REPO = Path(os.environ.get("FPAI_REPO", Path.home() / "FPAI_Cockpit"))
SPECS = REPO / "docs" / "codex" / "specs"
HANDOFF = REPO / "docs" / "codex" / "HANDOFF.md"


def kickoff_text(spec: str) -> str:
    spec = spec if spec.endswith(".md") else spec + ".md"
    return (
        f"Read `AGENTS.md`, then `docs/codex/README.md`, `docs/codex/AI_PROTOCOLS.md`, "
        f"`docs/codex/PHONE_HANDOFF.md`, `docs/codex/HANDOFF.md`, `docs/codex/INTENT_BUILDSTREAM.md`, "
        f"then the target spec `docs/codex/specs/{spec}`.\n"
        f"Work ONLY on the branch named in that spec; touch only files-allowed, never files-forbidden.\n"
        f"Build to the Definition of Done, run the tests, then update the 📥 lane in "
        f"`docs/codex/HANDOFF.md` with: files changed · summary · tests · risks · rollback. "
        f"Do NOT merge or move money/deploy/secrets — show me the diff first."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit a paste-ready Codex kickoff for a spec.")
    ap.add_argument("--spec", required=True, help="spec name (e.g. SPEC_auto-routing)")
    ap.add_argument("--post", action="store_true", help="also append the kickoff to HANDOFF 📤 lane")
    args = ap.parse_args(argv)

    spec_file = SPECS / (args.spec if args.spec.endswith(".md") else args.spec + ".md")
    if not spec_file.exists():
        print(f"⚠️ spec not found: {spec_file} (proceeding with the prompt anyway)")

    block = kickoff_text(args.spec)
    print("───── paste this into Codex ─────")
    print(block)
    print("─────────────────────────────────")

    if args.post and HANDOFF.exists():
        text = HANDOFF.read_text(encoding="utf-8")
        marker = "## 📤 EMBER → CODEX"
        entry = f"\n**↗︎ Kickoff ready · {args.spec}** (paste into Codex):\n```\n{block}\n```\n"
        if marker in text:
            text = text.replace(marker, marker + "\n" + entry, 1)
            HANDOFF.write_text(text, encoding="utf-8")
            print(f"posted → {HANDOFF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
