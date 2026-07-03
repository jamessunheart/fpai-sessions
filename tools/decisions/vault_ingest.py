#!/usr/bin/env python3
"""vault_ingest — Obsidian → brain_index.session_insights

Scans vault 02_CONTEXT/Memory/ (with 00_MEMORY fallback) for notes James wrote or edited between sessions,
pushes them as session_insights so the next session (and bot) sees them
without James having to repeat himself.

Auto-generated notes (BRAIN STATE, HOT STATE, BRAIN DIGEST, GOALS MIRROR,
NOW MIRROR, etc.) are skipped — only human-authored content ingests.

Runs as the second step of the vault-sync LaunchAgent, after mirror_pull.py.
Also runs standalone: python3 vault_ingest.py

Flow:
  Obsidian vault 02_CONTEXT/Memory/*.md  (human-authored, modified since last run)
        │  SSH  · remote python · INSERT only (never reads private data)
        ▼
  brain_index.session_insights  (type='james_note', weight=7)
        │
        ▼
  Next session / bot context window  (surfaces automatically)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SERVER = "root@162.0.208.88"
ENV_FILE = "/etc/sh-brain/curator.env"
VENV_PY = "/opt/sh-brain-src/.venv/bin/python"
REMOTE_CMD = f"set -a; . {ENV_FILE} 2>/dev/null; set +a; {VENV_PY} -"

_VAULT_DOCS = HOME / "Documents" / "FPOS" / "Full Potential OS"
_VAULT_ICLOUD = (
    HOME
    / "Library"
    / "Mobile Documents"
    / "iCloud~md~obsidian"
    / "Documents"
    / "Full Potential OS"
)
_EXPLICIT_VAULT = os.environ.get("FPAI_VAULT")

STAMP_FILE = HOME / ".config" / "fpai" / "vault_sync" / "vault_ingest_last_run.txt"

# Notes written by mirror_pull / daily_sync — skip these
AUTO_GENERATED = {
    "BRAIN STATE.md",
    "BRAIN DIGEST.md",
    "HOT STATE.md",
    "NOW — Current Priorities.md",
    "AI GOALS.md",
    "SYSTEM ARCHITECTURE.md",
    "GOALS MIRROR.md",
    "NOW MIRROR.md",
    "PROOF LOG.md",
    "SURFACED CONCEPTS.md",
    "DECISIONS.md",
    "SYSTEM READINESS.md",
    "SCHEDULE.md",
    "NEXT MOVE DETAIL.md",
    "SERVICE REGISTRY.md",
    "SERVICE REGISTRY — SORTED.md",
    "FPOS NORTH STAR.md",
}


def _vault() -> Path | None:
    if _EXPLICIT_VAULT:
        p = Path(_EXPLICIT_VAULT).expanduser()
        return p if p.exists() else None
    for candidate in [_VAULT_DOCS, _VAULT_ICLOUD]:
        if candidate.exists():
            return candidate
    return None


def _last_run_ts() -> float:
    """Unix timestamp of last ingest run, or 0 (ingest everything)."""
    try:
        return float(STAMP_FILE.read_text().strip())
    except (OSError, ValueError):
        return 0.0


def _save_stamp() -> None:
    STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAMP_FILE.write_text(str(datetime.now(timezone.utc).timestamp()))


# Memory-note directories to scan, in preference order. James reorganized the
# vault 2026-07-02 (00_MEMORY -> 02_CONTEXT/Memory); scan the new home first and
# keep the old one as a fallback so ingest survives the reorg. Override with
# FPAI_VAULT_NOTE_DIRS (comma-separated, vault-relative).
_DEFAULT_NOTE_DIRS = ("02_CONTEXT/Memory", "00_MEMORY")


def _note_dirs() -> tuple[str, ...]:
    raw = os.environ.get("FPAI_VAULT_NOTE_DIRS", "").strip()
    if raw:
        return tuple(d.strip() for d in raw.split(",") if d.strip())
    return _DEFAULT_NOTE_DIRS


def _human_notes(vault: Path, since_ts: float) -> list[Path]:
    """Return human-authored *.md notes modified after since_ts across the memory
    dirs, excluding auto-generated mirror files. Reorg-safe (see _note_dirs)."""
    results = []
    for rel in _note_dirs():
        mem_dir = vault / rel
        if not mem_dir.exists():
            continue
        for p in mem_dir.glob("*.md"):
            if p.name in AUTO_GENERATED or p.name.startswith("_"):
                continue
            if p.stat().st_mtime > since_ts:
                results.append(p)
    return sorted(results, key=lambda p: p.stat().st_mtime)


def _read_note(path: Path, max_chars: int = 3000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return ""
    return text[:max_chars]


REMOTE_INGEST_PY = r'''
import os, json, asyncio, psycopg, sys
from datetime import datetime, timezone

DB = os.environ.get("BRAIN_INDEX_DB_URL")

DEDUP_SQL = "SELECT count(*) FROM brain_index.session_insights WHERE title = %s AND ts > NOW() - INTERVAL '24 hours'"
INSERT_SQL = "INSERT INTO brain_index.session_insights (session_id, surface, insight_type, title, body, weight) VALUES (%s, 'obsidian_vault', 'james_note', %s, %s, 7)"

async def main():
    notes = json.loads(sys.argv[1])
    if not notes:
        print(json.dumps({"ok": True, "inserted": 0}))
        return
    conn = await psycopg.AsyncConnection.connect(DB, autocommit=True)
    inserted = 0
    async with conn.cursor() as cur:
        for note in notes:
            await cur.execute(DEDUP_SQL, (note["title"],))
            if (await cur.fetchone())[0] > 0:
                continue
            session_id = "vault-ingest-" + datetime.now(timezone.utc).strftime("%Y%m%d")
            await cur.execute(INSERT_SQL, (session_id, note["title"], note["body"]))
            inserted += 1
    await conn.close()
    print(json.dumps({"ok": True, "inserted": inserted}))

asyncio.run(main())
'''


def _push_notes(notes: list[dict]) -> dict:
    """SSH to 162 and insert notes into brain_index.session_insights."""
    payload = json.dumps(notes)
    # Pass payload as argv[1] to the remote script
    remote_script = f"import sys; sys.argv = ['', {repr(payload)}]\n" + REMOTE_INGEST_PY
    r = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=12", "-o", "BatchMode=yes", SERVER, REMOTE_CMD],
        input=remote_script,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()[:300]}
    for line in reversed(r.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {"ok": False, "error": "no JSON in response"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", type=float, default=None,
                    help="Unix timestamp cutoff (default: last run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be ingested, don't write")
    ap.add_argument("--all", action="store_true", dest="all_notes",
                    help="Ingest all notes regardless of modification time")
    args = ap.parse_args(argv)

    vault = _vault()
    if not vault:
        print(json.dumps({"ok": False, "reason": "vault not found"}))
        return 1

    since_ts = 0.0 if args.all_notes else (args.since if args.since is not None else _last_run_ts())
    notes_paths = _human_notes(vault, since_ts)

    if not notes_paths:
        print(json.dumps({"ok": True, "inserted": 0, "reason": "no new human notes"}))
        if not args.dry_run:
            _save_stamp()
        return 0

    notes = []
    for path in notes_paths:
        body = _read_note(path)
        if not body:
            continue
        notes.append({
            "title": f"Obsidian: {path.stem}",
            "body": body,
        })

    if args.dry_run:
        print(json.dumps({"dry_run": True, "would_ingest": [n["title"] for n in notes]}))
        return 0

    result = _push_notes(notes)
    print(json.dumps(result))

    if result.get("ok"):
        _save_stamp()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
