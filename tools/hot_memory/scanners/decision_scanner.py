#!/usr/bin/env python3
"""Scan recent decision/session-insight rows into hot-memory facts."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from tools.hot_memory.common import DEFAULT_HOT_DIR, REPO_ROOT, compact_facts, fact, utc_stamp, write_scan

DEFAULT_DB_URL = os.environ.get("BRAIN_INDEX_DB_URL", os.environ.get("DATABASE_URL", ""))


def collect(repo_root: Path = REPO_ROOT, db_url: str = DEFAULT_DB_URL):
    facts = []
    facts.extend(_repo_decisions(repo_root))
    if db_url:
        facts.extend(_db_facts(db_url))
    return compact_facts(facts, limit=12)


def _repo_decisions(repo_root: Path):
    rows = []
    handoff = repo_root / "docs" / "codex" / "HANDOFF.md"
    if handoff.exists():
        for line in handoff.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if "Intent solved:" in stripped or "Downstream intent unlocked:" in stripped:
                rows.append(fact(stripped.lstrip("- "), "docs/codex/HANDOFF.md", utc_stamp(), weight=6, category="decision"))
            if len(rows) >= 4:
                break
    return rows


def _db_facts(db_url: str):
    try:
        import psycopg
    except ImportError:
        return []
    rows = []
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT title, body, surface, insight_type, weight, ts::text
                      FROM brain_index.session_insights
                     WHERE expires_at IS NULL OR expires_at > NOW()
                     ORDER BY weight DESC, ts DESC
                     LIMIT 6
                    """
                )
                for title, body, surface, insight_type, weight, ts in cur.fetchall():
                    text = f"{surface}/{insight_type}: {title}"
                    if body:
                        text += f" - {body}"
                    rows.append(fact(text, "brain_index.session_insights", str(ts), weight=int(weight or 6), category="decision"))
                cur.execute(
                    """
                    SELECT question, answer, ts::text
                      FROM brain_index.decisions
                     ORDER BY ts DESC
                     LIMIT 4
                    """
                )
                for question, answer, ts in cur.fetchall():
                    rows.append(fact(f"Decision answered: {question} -> {answer}", "brain_index.decisions", str(ts), weight=7, category="decision"))
    except Exception:
        return rows
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    args = parser.parse_args(argv)
    payload = write_scan("decision", collect(args.repo_root, args.db_url), hot_dir=args.hot_dir)
    print(payload["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

