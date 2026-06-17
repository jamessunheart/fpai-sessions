"""Per-agent recursive benchmark helpers.

Scorers are intentionally fixture-friendly: tests can pass plain dictionaries,
while the daily runner can read repo-local ledgers and optional JSON fixtures
without requiring a live database.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from statistics import median
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCORE_LEDGER = REPO_ROOT / "core" / "benchmarks" / "per_agent_scores.jsonl"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_REVIEWS_DIR = REPO_ROOT / "core" / "BUILD" / "reviews"
KNOWN_EVENT_TYPES = {
    "benchmark_run",
    "ran",
    "skipped",
    "attempted",
    "succeeded",
    "failed",
    "proposed",
    "merged",
    "reversed",
    "correction",
    "spec_queued",
    "session_start",
    "cost",
}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def run_date(now: dt.datetime | None = None) -> str:
    return (now or utc_now()).date().isoformat()


def parse_time(value: Any) -> dt.datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = dt.datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def age_days(value: Any, *, now: dt.datetime | None = None) -> float | None:
    parsed = parse_time(value)
    if not parsed:
        return None
    return round(max(0.0, ((now or utc_now()) - parsed).total_seconds() / 86400.0), 4)


def clamp01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, number)), 4)


def rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return clamp01(float(numerator) / float(denominator))


def safe_median(values: Iterable[int | float]) -> float:
    vals = [float(value) for value in values]
    return round(float(median(vals)), 4) if vals else 0.0


def per_day(rows: Iterable[dict[str, Any]], field: str, *, days: int = 1, now: dt.datetime | None = None) -> float:
    current = now or utc_now()
    cutoff = current - dt.timedelta(days=days)
    count = 0
    for row in rows:
        ts = parse_time(row.get(field))
        if ts and cutoff <= ts <= current:
            count += 1
    return round(count / max(1, days), 4)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path, *, since: dt.datetime | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since:
            ts = parse_time(row.get("ts") or row.get("run_date") or row.get("created_at"))
            if ts and ts < since:
                continue
        rows.append(row)
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def score_result(
    agent: str,
    *,
    primary_metric: float | dict[str, float],
    metrics: dict[str, Any],
    trigger_fired: bool,
    trigger_metric: str | None = None,
    trigger_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "agent": agent,
        "primary_metric": primary_metric,
        "metrics": metrics,
        "trigger_fired": bool(trigger_fired),
        "trigger_metric": trigger_metric,
        "trigger_reason": trigger_reason,
    }


def rows_for(data: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not data:
        return []
    rows = data.get(key) or []
    return [row for row in rows if isinstance(row, dict)]


def grouped_rates(
    rows: Iterable[dict[str, Any]],
    *,
    group_key: str,
    numerator_predicate,
    denominator_predicate=lambda _row: True,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, int]] = {}
    for row in rows:
        if not denominator_predicate(row):
            continue
        group = str(row.get(group_key) or "unknown")
        bucket = groups.setdefault(group, {"numerator": 0, "denominator": 0})
        bucket["denominator"] += 1
        if numerator_predicate(row):
            bucket["numerator"] += 1
    return {
        group: {
            "numerator": values["numerator"],
            "denominator": values["denominator"],
            "rate": rate(values["numerator"], values["denominator"]),
        }
        for group, values in sorted(groups.items())
    }

