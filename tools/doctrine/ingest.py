#!/usr/bin/env python3
"""Upsert repo doctrine markdown into brain_index.note_chunks.

Source of truth stays in core/STATE/*.md. This script sends bounded, public
doctrine files through the existing local embedding endpoint so Telegram brain
search can retrieve the governing laws with source path, commit, and file date.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BRAIN_BASE = os.environ.get("SH_BRAIN_BASE", "https://brain.sunheart.com")
DEFAULT_MAX_CHARS = int(os.environ.get("SH_DOCTRINE_INGEST_MAX_CHARS", "220000"))

DOCTRINE_FILES: tuple[str, ...] = (
    "core/STATE/CORE_DOCTRINE.md",
    "core/STATE/ALLOCATION_INTELLIGENCE.md",
    "core/STATE/CONSTITUTION.md",
    "core/STATE/STEWARDSHIP_CONSTITUTION.md",
    "core/STATE/AI_PRINCIPLES.md",
    "core/STATE/FOUNDATION.md",
)


@dataclass(frozen=True)
class DoctrineNote:
    rel_path: str
    source_path: str
    content: str
    commit_sha: str
    updated_at: str
    tags: list[str]


def _run_git(repo: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()


def current_commit(repo: Path) -> str:
    try:
        return _run_git(repo, ["rev-parse", "HEAD"])
    except Exception:
        return "working-tree"


def _file_updated_at(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        ts = datetime.now(timezone.utc).timestamp()
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:200] or fallback
    return fallback


def load_doctrine_note(repo: Path, rel_path: str, commit_sha: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> DoctrineNote | None:
    if rel_path not in DOCTRINE_FILES:
        return None
    path = (repo / rel_path).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    body = path.read_text(encoding="utf-8", errors="replace").strip()
    if not body:
        return None
    if len(body) > max_chars:
        tail = f"\n\n---\n*(truncated after {max_chars} chars; open `{rel_path}` for the full doctrine source)*"
        body = body[: max_chars - len(tail)] + tail
    updated_at = _file_updated_at(path)
    title = _title_from_markdown(body, path.stem)
    content = (
        f"**Doctrine source:** `{rel_path}`\n"
        f"**Doctrine title:** {title}\n"
        f"**Repo commit:** `{commit_sha[:12]}`\n"
        f"**File updated:** {updated_at}\n"
        "**Freshness rule:** cite this file/date when using this doctrine; if another source conflicts, call out the conflict.\n\n"
        f"{body}"
    )
    stem_tag = path.stem.lower().replace("_", "-")
    return DoctrineNote(
        rel_path=rel_path,
        source_path=f"repo-doctrine/{rel_path}",
        content=content,
        commit_sha=commit_sha,
        updated_at=updated_at,
        tags=sorted({"doctrine", "repo-doctrine", stem_tag}),
    )


def collect_doctrine_notes(repo: Path, paths: list[str] | None = None) -> list[DoctrineNote]:
    commit_sha = current_commit(repo)
    selected = paths or list(DOCTRINE_FILES)
    notes: list[DoctrineNote] = []
    for rel_path in selected:
        normalized = rel_path.replace("\\", "/").strip("/")
        note = load_doctrine_note(repo, normalized, commit_sha)
        if note:
            notes.append(note)
    return notes


class BrainIndexClient:
    def __init__(self, base: str, token: str):
        import httpx

        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=120, headers={"Authorization": f"Bearer {token}"})

    def close(self) -> None:
        self.http.close()

    def upsert_doctrine_note(self, note: DoctrineNote) -> dict:
        payload = {
            "source_path": note.source_path,
            "content": note.content,
            "commit_sha": note.commit_sha,
            "updated_at": note.updated_at,
            "tags": note.tags,
            "prefer": "local",
            "sensitivity": "🟢 Public",
        }
        index_base = self.base
        if not index_base.endswith("/index") and "127.0.0.1" not in index_base and "localhost" not in index_base:
            index_base += "/index"
        response = self.http.post(f"{index_base}/ingest/memory_git_note", json=payload)
        response.raise_for_status()
        return response.json()


def build_report(notes: list[DoctrineNote], results: list[dict], *, dry_run: bool) -> dict:
    return {
        "ok": True,
        "dry_run": dry_run,
        "notes": len(notes),
        "source_paths": [note.source_path for note in notes],
        "content_sha1": {note.source_path: hashlib.sha1(note.content.encode()).hexdigest() for note in notes},
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert core/STATE doctrine markdown into brain_index.note_chunks")
    parser.add_argument("--repo", default=os.environ.get("FPAI_REPO_ROOT", "."), help="FPAI_Cockpit repository path")
    parser.add_argument("--brain-base", default=DEFAULT_BRAIN_BASE)
    parser.add_argument("--token", default=os.environ.get("SH_INGEST_TOKEN"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--path", action="append", dest="paths", help="Explicit doctrine path; repeatable")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    notes = collect_doctrine_notes(repo, args.paths)
    results: list[dict] = []

    if not args.dry_run and notes:
        if not args.token:
            print("SH_INGEST_TOKEN is required unless --dry-run is set", file=sys.stderr)
            return 2
        client = BrainIndexClient(args.brain_base, args.token)
        try:
            for note in notes:
                results.append(client.upsert_doctrine_note(note))
        finally:
            client.close()

    report = build_report(notes, results, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        verb = "would upsert" if args.dry_run else "upserted"
        print(f"doctrine ingest: {verb} {len(notes)} doctrine note(s)")
        for source_path in report["source_paths"]:
            print(f"  - {source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
