#!/usr/bin/env python3
"""Persist bounded build-session context for the next process.

The registry is the source of truth for build status. This module snapshots the
parts a fresh session needs quickly: active builds, current branch, changed
files, a short progress note, and recent result artifacts. It stores plain JSON
so it works before the live brain DB is available.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_STATE_DIR = Path(os.environ.get("FPAI_SESSION_STATE_DIR", "/opt/fpai-build/session_state"))
MAX_ACTIVE_BUILDS = 12
MAX_CHANGED_FILES = 80
MAX_RECENT_RESULTS = 8
MAX_NOTE_CHARS = 4000


@dataclass(frozen=True)
class BuildProgress:
    id: str
    status: str
    branch: str = ""
    spec: str = ""
    tests_passed: bool | None = None
    notes: str = ""


@dataclass(frozen=True)
class SessionSnapshot:
    schema: str = "fpai-session-snapshot.v1"
    session_id: str = "unknown"
    surface: str = "codex"
    saved_at: str = ""
    repo_root: str = ""
    branch: str = ""
    head: str = ""
    changed_files: list[str] = field(default_factory=list)
    active_builds: list[BuildProgress] = field(default_factory=list)
    recent_results: list[str] = field(default_factory=list)
    progress_note: str = ""


def build_snapshot(
    *,
    repo_root: Path = REPO_ROOT,
    session_id: str = "unknown",
    surface: str = "codex",
    progress_note: str = "",
    changed_files: list[str] | None = None,
) -> SessionSnapshot:
    root = Path(repo_root)
    return SessionSnapshot(
        session_id=_clean(session_id, 120) or "unknown",
        surface=_clean(surface, 40) or "other",
        saved_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        branch=_git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        head=_git(root, "rev-parse", "--short", "HEAD"),
        changed_files=(changed_files if changed_files is not None else git_changed_files(root))[:MAX_CHANGED_FILES],
        active_builds=active_builds(root)[:MAX_ACTIVE_BUILDS],
        recent_results=recent_results(root)[:MAX_RECENT_RESULTS],
        progress_note=_clean(progress_note, MAX_NOTE_CHARS),
    )


def active_builds(repo_root: Path = REPO_ROOT) -> list[BuildProgress]:
    registry = Path(repo_root) / "core" / "BUILD" / "REGISTRY.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = data.get("active_builds") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []

    priority = {"building": 0, "queued": 1, "ready": 2, "done": 3, "blocked": 4, "merged": 5}
    builds: list[BuildProgress] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = _clean(str(row.get("status") or "unknown"), 40)
        if status == "merged":
            continue
        builds.append(
            BuildProgress(
                id=_clean(str(row.get("slug") or row.get("id") or "unknown"), 160),
                status=status,
                branch=_clean(str(row.get("branch") or ""), 180),
                spec=_clean(str(row.get("spec") or ""), 220),
                tests_passed=_bool_or_none(row.get("tests_passed")),
                notes=_clean(str(row.get("notes") or ""), 500),
            )
        )
    builds.sort(key=lambda item: (priority.get(item.status, 9), item.id))
    return builds


def git_changed_files(repo_root: Path = REPO_ROOT) -> list[str]:
    out = _git(Path(repo_root), "status", "--short")
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[2:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        if path:
            files.append(path)
    return files


def recent_results(repo_root: Path = REPO_ROOT) -> list[str]:
    results_dir = Path(repo_root) / "core" / "BUILD" / "results"
    if not results_dir.exists():
        return []
    paths = sorted(results_dir.glob("SPEC_*.result.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [path.name for path in paths[:MAX_RECENT_RESULTS]]


def save_snapshot(snapshot: SessionSnapshot, *, state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = snapshot_to_dict(snapshot)
    target = state_dir / "latest.json"
    session_target = state_dir / f"{_safe_name(snapshot.session_id)}.json"
    _atomic_write_json(target, payload)
    _atomic_write_json(session_target, payload)
    return target


def load_latest(*, state_dir: Path = DEFAULT_STATE_DIR) -> SessionSnapshot | None:
    path = Path(state_dir) / "latest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return snapshot_from_dict(data)


def render_snapshot(snapshot: SessionSnapshot, *, max_items: int = 6, max_chars: int = 1600) -> str:
    lines = [
        "Persisted session progress:",
        f"- Session: {snapshot.session_id} · {snapshot.surface} · {snapshot.saved_at}",
        f"- Branch: {snapshot.branch or 'unknown'} · head {snapshot.head or 'unknown'}",
    ]
    if snapshot.progress_note:
        lines.append(f"- Progress: {snapshot.progress_note}")
    if snapshot.active_builds:
        lines.append("- Active builds:")
        for item in snapshot.active_builds[:max_items]:
            tests = "tests passed" if item.tests_passed is True else "tests pending" if item.tests_passed is False else "tests unknown"
            lines.append(f"  - {item.id} · {item.status} · {tests} · {item.branch}")
    if snapshot.changed_files:
        lines.append("- Changed files: " + ", ".join(snapshot.changed_files[:max_items]))
    if snapshot.recent_results:
        lines.append("- Recent results: " + ", ".join(snapshot.recent_results[:max_items]))
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 20)].rsplit("\n", 1)[0] + "\n- ... bounded"


def snapshot_to_dict(snapshot: SessionSnapshot) -> dict[str, Any]:
    return asdict(snapshot)


def snapshot_from_dict(data: dict[str, Any]) -> SessionSnapshot | None:
    if not isinstance(data, dict) or data.get("schema") != "fpai-session-snapshot.v1":
        return None
    builds = []
    for item in data.get("active_builds") or []:
        if isinstance(item, dict):
            builds.append(
                BuildProgress(
                    id=str(item.get("id") or "unknown"),
                    status=str(item.get("status") or "unknown"),
                    branch=str(item.get("branch") or ""),
                    spec=str(item.get("spec") or ""),
                    tests_passed=_bool_or_none(item.get("tests_passed")),
                    notes=str(item.get("notes") or ""),
                )
            )
    return SessionSnapshot(
        session_id=str(data.get("session_id") or "unknown"),
        surface=str(data.get("surface") or "other"),
        saved_at=str(data.get("saved_at") or ""),
        repo_root=str(data.get("repo_root") or ""),
        branch=str(data.get("branch") or ""),
        head=str(data.get("head") or ""),
        changed_files=[str(item) for item in data.get("changed_files") or []],
        active_builds=builds,
        recent_results=[str(item) for item in data.get("recent_results") or []],
        progress_note=str(data.get("progress_note") or ""),
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
        tmp = Path(fh.name)
    tmp.replace(path)


def _git(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _clean(value: str, limit: int) -> str:
    return " ".join((value or "").split())[:limit]


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value.strip())
    return (safe or "unknown")[:160]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("save", "show"))
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--session-id", default=os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or "unknown")
    parser.add_argument("--surface", default=os.environ.get("FPAI_SESSION_SURFACE", "codex"))
    parser.add_argument("--progress-note", default=os.environ.get("FPAI_SESSION_PROGRESS", ""))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.command == "save":
        snapshot = build_snapshot(
            repo_root=args.repo_root,
            session_id=args.session_id,
            surface=args.surface,
            progress_note=args.progress_note,
        )
        path = save_snapshot(snapshot, state_dir=args.state_dir)
        payload = snapshot_to_dict(snapshot)
        print(json.dumps(payload, sort_keys=True) if args.json else f"session snapshot saved: {path}")
        return 0

    snapshot = load_latest(state_dir=args.state_dir)
    if snapshot is None:
        print("no persisted session snapshot found", file=sys.stderr)
        return 1
    print(json.dumps(snapshot_to_dict(snapshot), sort_keys=True) if args.json else render_snapshot(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
