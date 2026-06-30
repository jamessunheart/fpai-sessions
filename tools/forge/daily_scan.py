#!/usr/bin/env python3
"""Run the opt-in daily Forge frontier scan."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from tools.forge.frontier_scan import append_daily_log, notify_if_needed, run_scan, scan_enabled, send_alarm


def run_daily_scan(
    *,
    root: Path,
    force: bool = False,
    current: dt.datetime | None = None,
    json_output: bool = False,
) -> dict[str, object]:
    if not scan_enabled(force):
        return {"status": "skipped", "reason": "FORGE_SCAN_ENABLED is not 1"}
    now = current or dt.datetime.now(dt.timezone.utc)
    try:
        findings = run_scan("daily", current=now)
    except Exception as exc:  # any scan failure must alarm, not crash silently
        alarm = send_alarm(f"\u26a0 Forge DAILY frontier scan: no parseable findings after retries ({exc}). Scan ran but produced nothing \u2014 check claude -p / parser.")
        return {"status": "empty", "findings": 0, "alarm": alarm, "json_output": json_output}
    log_result = append_daily_log(findings, root / "core" / "STATE" / "FRONTIER_LOG.md", current=now)
    notify_result = notify_if_needed(findings, "daily")
    return {
        "status": "ok",
        "findings": len(findings),
        "log": log_result,
        "notify": notify_result,
        "json_output": json_output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the daily Forge frontier scan.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--force", action="store_true", help="Run even when FORGE_SCAN_ENABLED is not 1.")
    parser.add_argument("--json", action="store_true", help="Print JSON result.")
    args = parser.parse_args(argv)

    result = run_daily_scan(root=args.root, force=args.force, json_output=args.json)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"daily frontier scan: {result['status']}")
    return 0 if result["status"] in {"ok", "skipped", "empty"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
