#!/usr/bin/env python3
"""Run all discovery crawlers with source-level error isolation."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.discovery import common

CRAWLERS = (
    ("reddit", "tools.discovery.reddit_crawler"),
    ("twitter", "tools.discovery.twitter_crawler"),
    ("instagram", "tools.discovery.instagram_crawler"),
    ("telegram", "tools.discovery.telegram_scanner"),
    ("hn", "tools.discovery.hn_crawler"),
    ("github", "tools.discovery.github_crawler"),
)


def run_all(*, crawlers: tuple[tuple[str, str], ...] = CRAWLERS, connector: Any | None = None) -> dict[str, Any]:
    if os.environ.get("DISCOVERY_DISABLE") == "1":
        return {"schema": "fpai.discovery.run.v1", "disabled": True, "found": 0, "inserted": 0, "sources": []}
    inserted_total = 0
    found_total = 0
    source_results: list[dict[str, Any]] = []
    conn = connector() if connector else None
    try:
        for name, module_name in crawlers:
            if common.disabled(name):
                source_results.append({"source": name, "disabled": True, "found": 0, "inserted": 0})
                continue
            try:
                module = importlib.import_module(module_name)
                rows = module.discover()
                found = len(rows)
                inserted = common.insert_contacts(conn, rows) if conn is not None and common.live_enabled() else 0
                found_total += found
                inserted_total += inserted
                source_results.append({"source": name, "found": found, "inserted": inserted, "error": None})
            except Exception as exc:
                source_results.append({"source": name, "found": 0, "inserted": 0, "error": f"{exc.__class__.__name__}: {exc}"})
    finally:
        if conn is not None and hasattr(conn, "close"):
            conn.close()
    return {
        "schema": "fpai.discovery.run.v1",
        "disabled": False,
        "dry_run": not common.live_enabled(),
        "found": found_total,
        "inserted": inserted_total,
        "sources": source_results,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all public discovery crawlers.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = run_all(connector=common.connect_from_env if common.live_enabled() else None)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        status = "disabled" if result.get("disabled") else f"found={result['found']} inserted={result['inserted']} dry_run={result.get('dry_run')}"
        print(f"discovery: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
