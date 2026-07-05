#!/usr/bin/env python3
"""Capability-created ledger.

This extends the allocation ledger convention with realized capability gain.
Missing or unmeasured axis values are zero by design.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Iterable


DEFAULT_LEDGER = Path(os.environ.get("FPAI_CAPABILITY_LEDGER", Path.home() / ".config/fpai/allocation/ledger.jsonl"))
DEFAULT_AXES = ("time_saved", "knowledge_gained", "cash_flow", "trust", "automation")
AXIS_LABELS = {
    "time_saved": "time",
    "knowledge_gained": "knowledge",
    "cash_flow": "cash",
    "trust": "trust",
    "automation": "auto",
}
RUBRIC = (
    "1 point = one defensible James-hour-equivalent, $100/month recurring cash-flow equivalent, "
    "or one similarly bounded unit of reusable trust/knowledge/automation. Unmeasured gain is 0."
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_ts(value: Any) -> dt.datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def score_value(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(number, 4)


def normalize_scores(scores: dict[str, Any] | None) -> dict[str, float]:
    raw = scores or {}
    normalized = {axis: score_value(raw.get(axis, 0)) for axis in DEFAULT_AXES}
    for axis, value in raw.items():
        if axis not in normalized:
            normalized[str(axis)] = score_value(value)
    return normalized


def total_score(scores: dict[str, float]) -> float:
    return round(sum(scores.values()), 4)


def capability_row(
    *,
    source_type: str,
    source_id: str,
    title: str,
    scores: dict[str, Any] | None = None,
    reusable_intelligence: str = "",
    expected_capability_gain: dict[str, Any] | None = None,
    basis: str = "",
    reviewed_by: str = "",
    ts: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_scores(scores)
    total = total_score(normalized)
    if total > 0 and not reusable_intelligence:
        raise ValueError("positive capability rows require reusable_intelligence")
    row = {
        "ts": ts or utc_now(),
        "event": "capability_created",
        "kind": "allocation_ledger_capability_score",
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "capability_gain": normalized,
        "total_capability_gain": total,
        "expected_capability_gain": normalize_scores(expected_capability_gain),
        "reusable_intelligence": reusable_intelligence,
        "rubric": RUBRIC,
        "basis": basis,
        "reviewed_by": reviewed_by,
        "honesty": "unmeasured gain is 0; do not infer unsupported scores",
    }
    expected_total = total_score(row["expected_capability_gain"])
    row["expected_total_capability_gain"] = expected_total
    row["capability_estimate_delta"] = round(total - expected_total, 4)
    return row


def append_row(path: Path | str, row: dict[str, Any]) -> dict[str, Any]:
    ledger = Path(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def read_rows(path: Path | str) -> list[dict[str, Any]]:
    ledger = Path(path)
    if not ledger.exists():
        return []
    rows: list[dict[str, Any]] = []
    with ledger.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("event") == "capability_created":
                rows.append(item)
    return rows


def rows_since(rows: Iterable[dict[str, Any]], *, start: dt.datetime, end: dt.datetime) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        stamp = parse_ts(row.get("ts"))
        if stamp and start <= stamp < end:
            selected.append(row)
    return selected


def summarize_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    axis_totals: dict[str, float] = {axis: 0.0 for axis in DEFAULT_AXES}
    selected = list(rows)
    for row in selected:
        scores = normalize_scores(row.get("capability_gain"))
        for axis, value in scores.items():
            axis_totals[axis] = round(axis_totals.get(axis, 0.0) + value, 4)
    total = round(sum(axis_totals.values()), 4)
    return {
        "total_capability_gain": total,
        "axis_totals": axis_totals,
        "row_count": len(selected),
        "reusable_intelligence": [
            row.get("reusable_intelligence")
            for row in selected
            if row.get("total_capability_gain", 0) and row.get("reusable_intelligence")
        ],
    }


def period_summary(path: Path | str = DEFAULT_LEDGER, *, days: int = 1, now: dt.datetime | None = None) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    end = current.astimezone(dt.timezone.utc)
    if days == 1:
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = end - dt.timedelta(days=days)
    rows = rows_since(read_rows(path), start=start, end=end + dt.timedelta(microseconds=1))
    summary = summarize_rows(rows)
    summary.update({
        "start": start.isoformat().replace("+00:00", "Z"),
        "end": end.isoformat().replace("+00:00", "Z"),
        "days": days,
        "ledger": str(path),
    })
    return summary


def trend(path: Path | str = DEFAULT_LEDGER, *, days: int = 30, now: dt.datetime | None = None) -> list[dict[str, Any]]:
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    today = current.astimezone(dt.timezone.utc).date()
    rows = read_rows(path)
    out = []
    for offset in range(days - 1, -1, -1):
        day = today - dt.timedelta(days=offset)
        start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
        end = start + dt.timedelta(days=1)
        summary = summarize_rows(rows_since(rows, start=start, end=end))
        out.append({"date": day.isoformat(), **summary})
    return out


def capability_view(path: Path | str = DEFAULT_LEDGER, *, now: dt.datetime | None = None) -> dict[str, Any]:
    today = period_summary(path, days=1, now=now)
    week = period_summary(path, days=7, now=now)
    thirty = period_summary(path, days=30, now=now)
    return {
        "rubric": RUBRIC,
        "today": today,
        "week": week,
        "thirty_day": thirty,
        "trend_30d": trend(path, days=30, now=now),
    }


def format_summary(summary: dict[str, Any]) -> str:
    total = summary.get("total_capability_gain", 0)
    axes = summary.get("axis_totals", {})
    parts = []
    for axis in DEFAULT_AXES:
        value = axes.get(axis, 0)
        parts.append(f"{AXIS_LABELS.get(axis, axis)}+{format_points(value)}")
    return f"capability created today: +{format_points(total)} ({' '.join(parts)})."


def format_points(value: Any) -> str:
    number = score_value(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read or append capability-created ledger rows.")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--json", action="store_true", help="Print the full /capability payload as JSON.")
    parser.add_argument("--append", action="store_true", help="Append one capability row.")
    parser.add_argument("--source-type", default="build")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--score", action="append", default=[], help="Axis score as axis=value. Missing axes stay zero.")
    parser.add_argument("--reusable-intelligence", default="")
    parser.add_argument("--basis", default="")
    args = parser.parse_args(argv)

    if args.append:
        scores = dict(item.split("=", 1) for item in args.score if "=" in item)
        row = capability_row(
            source_type=args.source_type,
            source_id=args.source_id,
            title=args.title or args.source_id,
            scores=scores,
            reusable_intelligence=args.reusable_intelligence,
            basis=args.basis,
        )
        append_row(args.ledger, row)
        print(json.dumps(row, sort_keys=True))
        return 0

    view = capability_view(args.ledger)
    if args.json:
        print(json.dumps(view, indent=2, sort_keys=True))
    else:
        print(format_summary(view["today"]))
        print(f"7d: +{format_points(view['week']['total_capability_gain'])}")
        print(f"30d: +{format_points(view['thirty_day']['total_capability_gain'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
