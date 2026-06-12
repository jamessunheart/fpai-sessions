#!/usr/bin/env python3
"""
Zen Village applicant scorer · v1 · 2026-05-26
Scores incoming work-exchange + practitioner applications against the canonical
5-dimension scoring system (Alignment · Skills · Community Fit · Readiness ·
Application Depth · 100 pts total).

Usage:
  # Score a single application JSON file
  python3 score_applicant.py path/to/application.json

  # Score all unscored applications in inbox
  python3 score_applicant.py --batch

  # Pipe an application JSON from stdin
  cat application.json | python3 score_applicant.py --stdin

System prompt source: core/INTENT/SPECS/zen_village_scoring_prompt.md
Anthropic API key: ~/.config/fpai/api.token

Inbox + scored output:
  ~/.config/fpai/zen_village/applicants/inbox/     · raw applications dropped here
  ~/.config/fpai/zen_village/applicants/scored/    · scored JSONs land here
  ~/.config/fpai/zen_village/applicants/processed/ · raw apps moved here after scoring

Dashboard integration: Command Center reads scored/ and surfaces recent + top entries.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
REPO = Path("/Users/jamessunheart/FPAI_Cockpit")
SYSTEM_PROMPT_FILE = REPO / "core" / "INTENT" / "SPECS" / "zen_village_scoring_prompt.md"
INBOX = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "inbox"
SCORED = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "scored"
PROCESSED = HOME / ".config" / "fpai" / "zen_village" / "applicants" / "processed"
LOG = HOME / ".config" / "fpai" / "zen_village" / "scorer.log"

CLAUDE_BIN = HOME / ".local" / "bin" / "claude"
# Use Claude Sonnet for cost-balance (~$0.01-0.02 per scoring)
MODEL_ALIAS = "sonnet"


def log(msg: str):
    """Append-only scorer log."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
    print(msg, file=sys.stderr)


def load_system_prompt() -> str:
    """Extract the SYSTEM PROMPT code block from the canonical spec file."""
    if not SYSTEM_PROMPT_FILE.exists():
        raise FileNotFoundError(f"system prompt spec missing: {SYSTEM_PROMPT_FILE}")
    text = SYSTEM_PROMPT_FILE.read_text()
    # The system prompt is in the first ``` ... ``` code block after "## SYSTEM PROMPT"
    m = re.search(r"## SYSTEM PROMPT[^\n]*\n+```\n(.*?)```", text, re.DOTALL)
    if not m:
        raise ValueError("could not extract system prompt block from spec file")
    return m.group(1).strip()


def call_claude(system_prompt: str, application_json: dict) -> str:
    """Call Claude via the local claude CLI (already authenticated). Returns raw response text."""
    user_msg = f"Please score this application:\n\n{json.dumps(application_json, indent=2)}"

    # claude CLI arg order: --model first, then --system-prompt, then -p, then prompt
    cmd = [
        str(CLAUDE_BIN),
        "--model", MODEL_ALIAS,
        "--system-prompt", system_prompt,
        "-p",
        "--output-format", "json",
        user_msg,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI exit {r.returncode}: {r.stderr[:300]}")

    # claude CLI with --output-format json returns {"result": "...", "usage": {...}, ...}
    try:
        data = json.loads(r.stdout)
        return data.get("result", r.stdout)
    except json.JSONDecodeError:
        # fallback: treat as raw text
        return r.stdout


def parse_scored(raw: str) -> dict:
    """Strip any markdown fences and parse JSON. Robust to model wrapping."""
    clean = raw.strip()
    # Strip markdown fences if present
    clean = re.sub(r"^```(?:json)?\s*", "", clean)
    clean = re.sub(r"\s*```$", "", clean)
    clean = clean.strip()
    return json.loads(clean)


def score_application(application: dict) -> dict:
    """Score a single application dict. Returns the structured score object."""
    system_prompt = load_system_prompt()
    raw = call_claude(system_prompt, application)
    scored = parse_scored(raw)
    # Add metadata
    scored["_meta"] = {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "model_alias": MODEL_ALIAS,
        "scorer_version": "v1",
    }
    return scored


def safe_filename(name: str, total: int, lane: str) -> str:
    """Generate filename: NN_lane_name.json where NN is score."""
    name_part = re.sub(r"[^a-zA-Z0-9_-]", "_", name.replace(" ", "_"))[:40]
    lane_part = lane.replace("-", "")
    return f"{total:03d}_{lane_part}_{name_part}.json"


def process_one(application_path: Path) -> dict:
    """Score one application, write scored JSON, move raw to processed."""
    log(f"scoring {application_path.name}")
    with open(application_path) as f:
        application = json.load(f)

    scored = score_application(application)
    total = scored.get("total", 0)
    name = scored.get("name", "Unknown")
    lane = scored.get("lane", "work-exchange")

    SCORED.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    out_filename = safe_filename(name, total, lane)
    out_path = SCORED / out_filename
    with open(out_path, "w") as f:
        json.dump(scored, f, indent=2, ensure_ascii=False)

    # Move raw to processed
    shutil.move(str(application_path), str(PROCESSED / application_path.name))

    log(f"  scored: {name} · {total}/100 · {scored.get('tier','?')} · {out_filename}")
    return scored


def batch():
    """Score every JSON in INBOX."""
    INBOX.mkdir(parents=True, exist_ok=True)
    files = sorted(INBOX.glob("*.json"))
    if not files:
        print("inbox empty · drop application JSONs into:", INBOX)
        return
    print(f"processing {len(files)} application(s)...")
    for f in files:
        try:
            scored = process_one(f)
            print(f"  ✓ {scored.get('name')} · {scored.get('total')}/100 · {scored.get('tier_emoji','')} {scored.get('tier','')}")
        except Exception as e:
            log(f"FAILED on {f.name}: {e}")
            print(f"  ✗ {f.name}: {e}")
    print(f"\nDone. Scored output in: {SCORED}")


def single(path_str: str):
    path = Path(path_str)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        scored = process_one(path)
        print(json.dumps(scored, indent=2, ensure_ascii=False))
    except Exception as e:
        log(f"FAILED on {path.name}: {e}")
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


def stdin_mode():
    """Score application JSON piped via stdin."""
    raw = sys.stdin.read()
    try:
        application = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"invalid JSON from stdin: {e}", file=sys.stderr)
        sys.exit(2)
    try:
        scored = score_application(application)
        print(json.dumps(scored, indent=2, ensure_ascii=False))
    except Exception as e:
        log(f"FAILED stdin scoring: {e}")
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="Path to single application JSON")
    ap.add_argument("--batch", action="store_true", help="Process all JSONs in inbox")
    ap.add_argument("--stdin", action="store_true", help="Read application JSON from stdin")
    args = ap.parse_args()

    if args.stdin:
        stdin_mode()
    elif args.batch:
        batch()
    elif args.path:
        single(args.path)
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
