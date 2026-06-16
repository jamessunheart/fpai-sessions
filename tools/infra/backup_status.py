#!/usr/bin/env python3
"""Summarize brain backup events from the ops ledger for the morning digest."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path("/opt/fpai-build/ops_ledger.jsonl")
BACKUP_EVENTS = {"backup_complete", "backup_failed", "backup_warning", "backup_verified"}


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_rows(path: Path, *, now: datetime | None = None, hours: float = 24) -> list[dict[str, Any]]:
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(hours=hours)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        event = str(row.get("event") or row.get("type") or "")
        if event not in BACKUP_EVENTS:
            continue
        ts = parse_ts(row.get("ts") or row.get("timestamp"))
        if ts and ts < cutoff:
            continue
        rows.append(row)
    return rows


def backup_status(path: Path = DEFAULT_LEDGER, *, now: datetime | None = None, hours: float = 24) -> dict[str, Any]:
    rows = read_rows(path, now=now, hours=hours)
    failures = [r for r in rows if r.get("event") == "backup_failed"]
    completes = [r for r in rows if r.get("event") == "backup_complete"]
    latest_complete = completes[-1] if completes else None
    if failures:
        icon = "red"
        label = "backup failed"
        detail = str(failures[-1].get("detail") or failures[-1].get("path") or "failure logged")
    elif latest_complete and latest_complete.get("offsite") is True:
        icon = "green"
        label = "backup complete + offsite"
        detail = str(latest_complete.get("path") or "")
    elif latest_complete:
        icon = "yellow"
        label = "backup complete local only"
        detail = str(latest_complete.get("path") or "")
    else:
        icon = "yellow"
        label = "no backup event in window"
        detail = "morning digest did not find backup_complete or backup_failed in the last 24h"
    return {
        "icon": icon,
        "label": label,
        "detail": detail,
        "events": rows,
        "latest_complete": latest_complete,
        "failure_count": len(failures),
    }


def format_text(status: dict[str, Any]) -> str:
    emoji = {"red": "🔴", "green": "🟢", "yellow": "🟡"}.get(status["icon"], "🟡")
    return f"{emoji} brain backup: {status['label']} · {status['detail']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print brain backup status from ops_ledger.")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    status = backup_status(args.ops_ledger, hours=args.hours)
    print(json.dumps(status, sort_keys=True, default=str) if args.json else format_text(status))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
