#!/usr/bin/env python3
"""Scan correction and feedback signal names into hot-memory facts."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from tools.hot_memory.common import DEFAULT_HOT_DIR, DEFAULT_OPS_LEDGER, REPO_ROOT, compact_facts, fact, file_date, read_jsonl_tail, write_scan

DEFAULT_DB_URL = os.environ.get("BRAIN_INDEX_DB_URL", os.environ.get("DATABASE_URL", ""))


def collect(repo_root: Path = REPO_ROOT, db_url: str = DEFAULT_DB_URL, ops_ledger: Path = DEFAULT_OPS_LEDGER):
    facts = []
    facts.extend(_feedback_files(repo_root))
    facts.extend(_liveness_failures(ops_ledger))
    if db_url:
        facts.extend(_db_correction_counts(db_url))
    return compact_facts(facts, limit=10)


def _feedback_files(repo_root: Path):
    candidates = []
    for base in (repo_root / "core" / "STATE", repo_root / "core" / "INTELLIGENCE", repo_root / "core" / "CONTENT"):
        if not base.exists():
            continue
        candidates.extend(path for path in base.rglob("*feedback*.md") if path.is_file())
    newest = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[:5]
    return [
        fact(f"Recent feedback signal file: {path.name}", str(path.relative_to(repo_root)), file_date(path), weight=6, category="signal")
        for path in newest
    ]


def _db_correction_counts(db_url: str):
    try:
        import psycopg
    except ImportError:
        return []
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*), max(created_at)::text FROM brain_index.corrections WHERE created_at > NOW() - INTERVAL '7 days'")
                count, last_ts = cur.fetchone()
    except Exception:
        return []
    if not count:
        return []
    return [fact(f"{count} bot correction signals recorded in the last 7 days", "brain_index.corrections", str(last_ts), weight=7, category="signal")]


def _liveness_failures(ops_ledger: Path):
    rows = read_jsonl_tail(ops_ledger, limit=200)
    failures = [row for row in rows if str(row.get("event") or "") in {"liveness:fail", "liveness:partial"}]
    facts = []
    for row in failures[-5:]:
        detail = str(row.get("detail") or "post-merge liveness failed")
        status = str(row.get("liveness_status") or row.get("event") or "not-live")
        spec_id = str(row.get("spec_id") or "")
        ts = str(row.get("ts") or file_date(ops_ledger))
        source = str(row.get("artifact") or ops_ledger)
        prefix = f"Merged-but-not-live ({status})"
        if spec_id:
            prefix += f": {spec_id}"
        facts.append(fact(f"{prefix}: {detail}", source, ts, weight=9, category="signal"))
    return facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    args = parser.parse_args(argv)
    payload = write_scan("signal", collect(args.repo_root, args.db_url, args.ops_ledger), hot_dir=args.hot_dir)
    print(payload["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
