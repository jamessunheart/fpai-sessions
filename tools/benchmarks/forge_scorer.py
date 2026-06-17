from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from tools.benchmarks import DEFAULT_REGISTRY, DEFAULT_REVIEWS_DIR, parse_time, rate, rows_for, safe_median, score_result

AGENT = "forge"


def _registry_builds(registry_path: Path) -> list[dict[str, Any]]:
    if not registry_path.exists():
        return []
    try:
        return [row for row in json.loads(registry_path.read_text(encoding="utf-8")).get("active_builds", []) if isinstance(row, dict)]
    except (json.JSONDecodeError, OSError):
        return []


def _review_statuses(reviews_dir: Path) -> dict[str, list[str]]:
    statuses: dict[str, list[str]] = {}
    if not reviews_dir.exists():
        return statuses
    for path in sorted(reviews_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        build_id = path.stem.replace(".review", "")
        if "REQUEST_CHANGES" in text or re.search(r"\brequest changes\b", text, re.I):
            statuses.setdefault(build_id, []).append("REQUEST_CHANGES")
        if "APPROVE" in text or re.search(r"\bapproved?\b|\bno blockers?\b", text, re.I):
            statuses.setdefault(build_id, []).append("APPROVE")
    return statuses


def score(
    data: dict[str, Any] | None = None,
    *,
    now: dt.datetime | None = None,
    registry_path: Path = DEFAULT_REGISTRY,
    reviews_dir: Path = DEFAULT_REVIEWS_DIR,
) -> dict[str, Any]:
    builds = rows_for(data, "registry_builds") or _registry_builds(registry_path)
    reviews = (data or {}).get("review_statuses") or _review_statuses(reviews_dir)
    done = [row for row in builds if str(row.get("status") or "").lower() in {"done", "merged"}]
    first_pass = 0
    reviewed = 0
    for row in done:
        build_id = str(row.get("id") or row.get("slug") or "")
        statuses = reviews.get(build_id) or reviews.get(str(row.get("branch") or "")) or []
        if statuses:
            reviewed += 1
            if statuses[0] == "APPROVE" and "REQUEST_CHANGES" not in statuses[:1]:
                first_pass += 1
        elif row.get("tests_passed") is True:
            reviewed += 1
            first_pass += 1
    ops_rows = rows_for(data, "ops_ledger")
    merges = [row for row in ops_rows if row.get("event") == "merged"]
    reverts = [row for row in ops_rows if row.get("event") in {"reversed", "auto_reverted"}]
    cycle_hours = []
    for row in builds:
        start = parse_time(row.get("spec_written_at") or row.get("created_at") or row.get("started_at"))
        end = parse_time(row.get("merged_at") or row.get("done_at"))
        if start and end and end >= start:
            cycle_hours.append((end - start).total_seconds() / 3600.0)
    metrics = {
        "first_pass_approve_rate": rate(first_pass, reviewed),
        "revert_rate": rate(len(reverts), len(merges)),
        "cycle_time_hours": safe_median(cycle_hours),
    }
    return score_result(
        AGENT,
        primary_metric=metrics["first_pass_approve_rate"],
        metrics=metrics,
        trigger_fired=bool(reviewed) and metrics["first_pass_approve_rate"] < 0.6,
        trigger_metric="first_pass_approve_rate" if reviewed and metrics["first_pass_approve_rate"] < 0.6 else None,
        trigger_reason=f"first_pass_approve_rate {metrics['first_pass_approve_rate']} below 0.6" if reviewed and metrics["first_pass_approve_rate"] < 0.6 else None,
    )

