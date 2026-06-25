#!/usr/bin/env python3
"""Scan build specs and registry state into a hot-memory delta.

Uses brain_index.decisions as the source of truth for what's built/merged.
Falls back to file-system checks when DB is unavailable.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

from tools.hot_memory.common import DEFAULT_HOT_DIR, REPO_ROOT, compact_facts, fact, file_date, write_scan

DEFAULT_DB_URL = os.environ.get("BRAIN_INDEX_DB_URL", os.environ.get("DATABASE_URL", ""))


def collect(repo_root: Path = REPO_ROOT, db_url: str = DEFAULT_DB_URL):
    facts = []
    if db_url:
        facts.extend(_db_facts(db_url, repo_root))
    else:
        facts.extend(_file_facts(repo_root))
    return compact_facts(facts, limit=10)


def _db_facts(db_url: str, repo_root: Path) -> list:
    try:
        import psycopg
    except ImportError:
        return _file_facts(repo_root)
    rows = []
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Total merged count + most recent merged specs
                cur.execute(
                    """
                    SELECT COUNT(*) FROM brain_index.decisions
                    WHERE build_status = 'merged'
                    """
                )
                total_merged = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT id, build_branch FROM brain_index.decisions
                    WHERE build_status = 'merged'
                    ORDER BY id DESC
                    LIMIT 5
                    """
                )
                recent = cur.fetchall()
                if recent:
                    latest_id = recent[0][0]
                    latest_branch = (recent[0][1] or "").split("/")[-1][:40]
                    others = ", ".join(r[0] for r in recent[1:4])
                    rows.append(fact(
                        f"{total_merged} specs merged total. Latest: {latest_id} ({latest_branch}). Recent: {others}",
                        "brain_index.decisions",
                        "now",
                        weight=8,
                        category="spec_queue",
                    ))

                # Truly pending: answered but not yet merged
                cur.execute(
                    """
                    SELECT id, question FROM brain_index.decisions
                    WHERE status = 'answered'
                      AND build_status NOT IN ('merged', 'none')
                      AND spec_written = true
                    ORDER BY id DESC
                    LIMIT 5
                    """
                )
                building = cur.fetchall()
                if building:
                    ids = ", ".join(r[0] for r in building)
                    rows.append(fact(
                        f"Specs in build pipeline (answered, not merged): {ids}",
                        "brain_index.decisions",
                        "now",
                        weight=7,
                        category="spec_queue",
                    ))

                # Unanswered questions (need James decision)
                cur.execute(
                    """
                    SELECT COUNT(*) FROM brain_index.decisions
                    WHERE status = 'awaiting'
                    """
                )
                awaiting = cur.fetchone()[0]
                if awaiting:
                    rows.append(fact(
                        f"{awaiting} decisions awaiting James answer",
                        "brain_index.decisions",
                        "now",
                        weight=6,
                        category="spec_queue",
                    ))

    except Exception:
        return _file_facts(repo_root)
    return rows


def _file_facts(repo_root: Path) -> list:
    """Fallback: file-system based scan when DB unavailable."""
    specs_dir = repo_root / "core" / "BUILD" / "specs"
    results_dir = repo_root / "core" / "BUILD" / "results"
    rows = []
    if specs_dir.exists():
        pending = [
            s.stem for s in sorted(specs_dir.glob("SPEC_*.md"))
            if not (results_dir / f"{s.stem}.result.md").exists()
        ]
        if pending:
            rows.append(fact(
                f"Top pending build specs (file-based): {', '.join(pending[:3])}",
                "core/BUILD/specs",
                file_date(max((specs_dir / f"{n}.md" for n in pending[:3]), key=lambda p: p.stat().st_mtime)),
                weight=6,
                category="spec_queue",
            ))
    merged = _last_merge(repo_root)
    if merged:
        rows.append(fact(f"Last git merge/build marker: {merged}", "git log", file_date(repo_root / ".git"), weight=5, category="spec_queue"))
    return rows


def _last_merge(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1", "--merges"],
            cwd=repo_root, text=True, capture_output=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    args = parser.parse_args(argv)
    payload = write_scan("spec", collect(args.repo_root, args.db_url), hot_dir=args.hot_dir)
    print(payload["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
