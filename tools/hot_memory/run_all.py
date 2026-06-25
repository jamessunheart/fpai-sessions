#!/usr/bin/env python3
"""Run all hot-memory domain scanners."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

from tools.hot_memory.common import DEFAULT_HOT_DIR, DEFAULT_OPS_LEDGER, REPO_ROOT
from tools.hot_memory.scanners import decision_scanner, identity_scanner, ops_scanner, signal_scanner, spec_scanner


def run_all(
    *,
    repo_root: Path = REPO_ROOT,
    hot_dir: Path = DEFAULT_HOT_DIR,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    db_url: str = "",
) -> dict[str, object]:
    results: dict[str, object] = {"ok": True, "scanners": {}}
    runners: list[tuple[str, Callable[[], list[object]]]] = [
        ("spec", lambda: spec_scanner.collect(repo_root)),
        ("identity", lambda: identity_scanner.collect(repo_root)),
        ("ops", lambda: ops_scanner.collect(repo_root, ops_ledger)),
        ("decision", lambda: decision_scanner.collect(repo_root, db_url)),
        ("signal", lambda: signal_scanner.collect(repo_root, db_url)),
    ]
    for name, runner in runners:
        try:
            facts = runner()
            module = {
                "spec": spec_scanner,
                "identity": identity_scanner,
                "ops": ops_scanner,
                "decision": decision_scanner,
                "signal": signal_scanner,
            }[name]
            payload = module.write_scan(name, facts, hot_dir=hot_dir)
            results["scanners"][name] = {"ok": True, "changed": payload.get("changed"), "facts": len(facts)}
        except Exception as exc:
            results["ok"] = False
            results["scanners"][name] = {"ok": False, "error": str(exc)[:240]}
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--db-url", default=os.environ.get("BRAIN_INDEX_DB_URL", os.environ.get("DATABASE_URL", "")))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_all(repo_root=args.repo_root, hot_dir=args.hot_dir, ops_ledger=args.ops_ledger, db_url=args.db_url)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"hot-memory scan ok={result['ok']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

