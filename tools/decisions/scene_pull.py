#!/usr/bin/env python3
"""
scene_pull · v1 · 2026-05-30

Pulls scenes captured by /scene on the brain server into the Obsidian vault,
so James can SEE what the AI captured. One direction: server → vault.

  brain server  /opt/sh-brain-src/scenes.jsonl   (written by curator tgbot /scene)
        │  ssh read
        ▼
  vault  00_MEMORY/SCENES.md                      (readable in Obsidian)

Idempotent: tracks the last-pulled timestamp; only new scenes are appended.

Usage:
  python3 scene_pull.py          # pull new scenes into the vault
  python3 scene_pull.py --dry    # show what would be pulled, no writes
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SERVER = "root@162.0.208.88"
REMOTE_FILE = "/opt/sh-brain-src/scenes.jsonl"
STATE_FILE = HOME / ".config" / "fpai" / "tg_inbox" / "scene_pull_last_ts.txt"

VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
SCENES_FILE = VAULT / "00_MEMORY" / "SCENES.md"

HEADER = (
    "# SCENES\n\n"
    "*Captured intentions from `/scene` in @sunheartbrain_bot. "
    "Newest on top. One scene per entry. Synced from the brain server — "
    "this is what the AI sees.*\n\n"
    "---\n\n"
)
MARKER = "---\n\n"


def fetch_remote() -> list[dict]:
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", SERVER,
         f"cat {REMOTE_FILE} 2>/dev/null || true"],
        capture_output=True, text=True, timeout=40,
    )
    scenes = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            scenes.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return scenes


def last_ts() -> str:
    return STATE_FILE.read_text().strip() if STATE_FILE.exists() else ""


def save_ts(ts: str):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(ts)


def insert_scenes(entries: list[dict]):
    """Insert entries newest-on-top, just after the --- marker."""
    if not SCENES_FILE.exists():
        SCENES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCENES_FILE.write_text(HEADER)
    content = SCENES_FILE.read_text()
    # Build a block: oldest of the new batch first so newest ends up on top.
    block = ""
    for e in entries:  # entries come oldest→newest; prepend each so newest tops
        when = e.get("ts", "").replace("T", " ")[:16] + " UTC"
        block = f"### {when}\n\n{e.get('scene','').strip()}\n\n---\n\n" + block
    idx = content.find(MARKER)
    if idx == -1:
        SCENES_FILE.write_text(content + "\n" + block)
    else:
        cut = idx + len(MARKER)
        SCENES_FILE.write_text(content[:cut] + block + content[cut:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    scenes = fetch_remote()
    scenes.sort(key=lambda e: e.get("ts", ""))
    seen = last_ts()
    fresh = [e for e in scenes if e.get("ts", "") > seen]

    if not fresh:
        print("no new scenes")
        return 0

    if args.dry:
        for e in fresh:
            print(f"[dry] {e.get('ts')}: {e.get('scene','')[:60]!r}")
        print(f"[dry] would pull {len(fresh)} scene(s)")
        return 0

    insert_scenes(fresh)
    save_ts(fresh[-1]["ts"])
    print(f"pulled {len(fresh)} scene(s) → {SCENES_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
