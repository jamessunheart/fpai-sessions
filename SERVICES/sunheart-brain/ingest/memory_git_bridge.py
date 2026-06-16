#!/usr/bin/env python3
"""Bridge committed markdown files from the git-backed memory repo into RAG.

Intended for `/opt/fpai-build/memory/.git/hooks/post-commit` on server 162.
The hook should call this script from inside the memory repository.
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
from typing import Iterable

import httpx

from filters import SKIP_TAGS, classify

DEFAULT_BRAIN_BASE = os.environ.get("SH_BRAIN_BASE", "https://brain.sunheart.com")
DEFAULT_MAX_CHARS = int(os.environ.get("SH_MEMORY_GIT_MAX_CHARS", "200000"))

SECRET_PATH_PARTS = {
    ".git",
    ".obsidian",
    ".trash",
    "archive-private",
    "banking",
    "credentials",
    "key-info",
    "keyinfo",
    "keys",
    "legal",
    "medical",
    "passwords",
    "private",
    "secret",
    "secrets",
    "sensitive",
}


@dataclass(frozen=True)
class MemoryGitNote:
    rel_path: str
    source_path: str
    title: str
    content: str
    commit_sha: str
    updated_at: str
    tags: list[str]


def _run_git(repo: Path, args: list[str]) -> str:
    out = subprocess.check_output(["git", *args], cwd=repo, text=True)
    return out.strip()


def current_commit(repo: Path) -> str:
    return _run_git(repo, ["rev-parse", "HEAD"])


def changed_paths(repo: Path, commit: str = "HEAD") -> list[str]:
    """Return paths changed by one commit.

    `git diff --name-only HEAD` is empty inside a post-commit hook because the
    worktree already points at HEAD, so use diff-tree for the committed file set.
    """
    try:
        output = _run_git(
            repo,
            ["diff-tree", "--no-commit-id", "--name-only", "--diff-filter=ACMRT", "-r", commit],
        )
    except subprocess.CalledProcessError:
        output = ""
    if not output:
        output = _run_git(repo, ["show", "--pretty=", "--name-only", "--diff-filter=ACMRT", commit])
    return [line.strip() for line in output.splitlines() if line.strip()]


def extract_markdown_tags(content: str) -> list[str]:
    tags: set[str] = set()
    for token in content.replace("\n", " ").split():
        if token.startswith("#") and len(token) > 1:
            tag = token.lstrip("#").strip(".,;:!?()[]{}\"'`").lower()
            if tag:
                tags.add(tag)
    return sorted(tags)


def path_is_allowed(rel_path: str) -> bool:
    path = rel_path.replace("\\", "/").strip("/")
    if not path or path.startswith("../") or "/../" in path:
        return False
    if not path.lower().endswith(".md"):
        return False
    parts = [part.lower() for part in path.split("/")]
    if any(part.startswith(".") for part in parts):
        return False
    if any(part in SECRET_PATH_PARTS or part in SKIP_TAGS for part in parts):
        return False
    lowered = path.lower()
    return not any(
        marker in lowered
        for marker in (
            "api-key",
            "api_key",
            "private-key",
            "private_key",
            "recovery-phrase",
            "seed-phrase",
            "seed_phrase",
        )
    )


def _title_from_markdown(content: str, fallback: str) -> str:
    for line in content.splitlines()[:30]:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()[:200] or fallback
    return fallback


def load_note(repo: Path, rel_path: str, commit_sha: str, max_chars: int = DEFAULT_MAX_CHARS) -> MemoryGitNote | None:
    if not path_is_allowed(rel_path):
        return None
    full_path = (repo / rel_path).resolve()
    try:
        full_path.relative_to(repo.resolve())
    except ValueError:
        return None
    if not full_path.is_file():
        return None
    body = full_path.read_text(encoding="utf-8", errors="replace").strip()
    if not body:
        return None

    tags = extract_markdown_tags(body)
    classification = classify(body, tags, default_sensitivity="🟡 Personal")
    if classification.decision == "skip":
        return None

    if len(body) > max_chars:
        tail = f"\n\n---\n*(truncated after {max_chars} chars; open original memory file for full text)*"
        body = body[: max_chars - len(tail)] + tail

    rel = rel_path.replace("\\", "/").strip("/")
    content = f"**File:** `{rel}`\n**Commit:** `{commit_sha[:12]}`\n\n{body}"
    try:
        mtime = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        mtime = datetime.now(timezone.utc)
    tags = sorted(set([*tags, "memory-git", classification.decision]))
    return MemoryGitNote(
        rel_path=rel,
        source_path=f"memory-git/{rel}",
        title=_title_from_markdown(body, full_path.stem),
        content=content,
        commit_sha=commit_sha,
        updated_at=mtime.isoformat(),
        tags=tags,
    )


def collect_notes(repo: Path, paths: Iterable[str] | None = None, commit: str = "HEAD") -> list[MemoryGitNote]:
    commit_sha = current_commit(repo) if commit == "HEAD" else _run_git(repo, ["rev-parse", commit])
    rel_paths = list(paths) if paths is not None else changed_paths(repo, commit)
    notes: list[MemoryGitNote] = []
    seen: set[str] = set()
    for rel_path in rel_paths:
        normalized = rel_path.replace("\\", "/").strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        note = load_note(repo, normalized, commit_sha)
        if note:
            notes.append(note)
    return notes


class BrainIndexClient:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=120, headers={"Authorization": f"Bearer {token}"})

    def close(self) -> None:
        self.http.close()

    def upsert_memory_git_note(self, note: MemoryGitNote) -> dict:
        payload = {
            "source_path": note.source_path,
            "content": note.content,
            "commit_sha": note.commit_sha,
            "updated_at": note.updated_at,
            "tags": note.tags,
            "prefer": "local",
            "sensitivity": "🟡 Personal",
        }
        r = self.http.post(f"{self.base}/index/ingest/memory_git_note", json=payload)
        r.raise_for_status()
        return r.json()


def build_report(notes: list[MemoryGitNote], results: list[dict], *, dry_run: bool) -> dict:
    return {
        "ok": True,
        "dry_run": dry_run,
        "notes": len(notes),
        "source_paths": [note.source_path for note in notes],
        "content_sha1": {
            note.source_path: hashlib.sha1(note.content.encode()).hexdigest()
            for note in notes
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert committed memory markdown into brain_index.note_chunks")
    parser.add_argument("--repo", default=".", help="Memory git repository path")
    parser.add_argument("--commit", default="HEAD", help="Commit/ref to inspect")
    parser.add_argument("--brain-base", default=DEFAULT_BRAIN_BASE)
    parser.add_argument("--token", default=os.environ.get("SH_INGEST_TOKEN"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--path", action="append", dest="paths", help="Explicit changed path; repeatable")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    notes = collect_notes(repo, args.paths, args.commit)
    results: list[dict] = []

    if not args.dry_run and notes:
        if not args.token:
            print("SH_INGEST_TOKEN is required unless --dry-run is set", file=sys.stderr)
            return 2
        client = BrainIndexClient(args.brain_base, args.token)
        try:
            for note in notes:
                results.append(client.upsert_memory_git_note(note))
        finally:
            client.close()

    report = build_report(notes, results, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        verb = "would upsert" if args.dry_run else "upserted"
        print(f"memory-git bridge: {verb} {len(notes)} markdown note(s)")
        for source_path in report["source_paths"]:
            print(f"  - {source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
