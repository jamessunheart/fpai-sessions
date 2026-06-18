#!/usr/bin/env python3
"""Generate the weekly bandwidth report from routing ledger evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from tools.bandwidth.routing_log import DEFAULT_LEDGER, REPO_ROOT

DEFAULT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "bandwidth_ledger.json"
DEFAULT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "bandwidth_ledger.md"
DEFAULT_STATE = REPO_ROOT / "core" / "STATE" / "BANDWIDTH_LEDGER.md"
SCHEMA = "bandwidth-ledger.v1"
T3_EQUIVALENT_MINUTES = 20


@dataclass(frozen=True)
class WeekMetric:
    week: str
    task_type: str
    total: int
    t1_handled: int
    t3_escalated: int
    t1_rate_pct: float
    recovered_t3_equivalent_decisions: int
    recovered_minutes: int

    def to_json(self) -> dict[str, Any]:
        return {
            "week": self.week,
            "task_type": self.task_type,
            "total": self.total,
            "t1_handled": self.t1_handled,
            "t3_escalated": self.t3_escalated,
            "t1_rate_pct": self.t1_rate_pct,
            "recovered_t3_equivalent_decisions": self.recovered_t3_equivalent_decisions,
            "recovered_minutes": self.recovered_minutes,
        }


@dataclass(frozen=True)
class BandwidthReport:
    generated_at: str
    status: str
    current_week: str
    previous_week: str | None
    weekly: tuple[WeekMetric, ...]
    current_t1_rate_pct: float
    previous_t1_rate_pct: float | None
    t1_rate_delta_pct: float | None
    recovered_decisions: int
    recovered_minutes: int
    leak_task_types: tuple[str, ...]
    recommendations: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "generated_at": self.generated_at,
            "status": self.status,
            "current_week": self.current_week,
            "previous_week": self.previous_week,
            "weekly": [item.to_json() for item in self.weekly],
            "current_t1_rate_pct": self.current_t1_rate_pct,
            "previous_t1_rate_pct": self.previous_t1_rate_pct,
            "t1_rate_delta_pct": self.t1_rate_delta_pct,
            "recovered_decisions": self.recovered_decisions,
            "recovered_minutes": self.recovered_minutes,
            "leak_task_types": list(self.leak_task_types),
            "recommendations": list(self.recommendations),
        }


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(value: dt.datetime | None = None) -> str:
    return (value or utc_now()).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def week_id(value: dt.datetime) -> str:
    year, week, _ = value.isocalendar()
    return f"{year}-W{week:02d}"


def parse_ts(raw: str) -> dt.datetime | None:
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def read_jsonl(path: Path | str = DEFAULT_LEDGER) -> list[dict[str, Any]]:
    ledger = Path(path)
    if not ledger.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def normalize_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        parsed = parse_ts(str(row.get("ts") or ""))
        task_type = str(row.get("task_type") or "").strip()
        tier_used = str(row.get("tier_used") or "").upper()
        outcome = str(row.get("outcome") or "").lower()
        if not parsed or not task_type or tier_used not in {"T0", "T1", "T2", "T3", "T4", "T5"}:
            continue
        normalized.append(
            {
                "ts": parsed,
                "week": week_id(parsed),
                "task_type": task_type,
                "tier_used": tier_used,
                "outcome": outcome,
            }
        )
    return normalized


def aggregate_weekly(rows: Iterable[dict[str, Any]]) -> tuple[WeekMetric, ...]:
    buckets: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"total": 0, "t1": 0, "t3": 0})
    for row in rows:
        key = (row["week"], row["task_type"])
        buckets[key]["total"] += 1
        if row["tier_used"] == "T1" and row["outcome"] == "completed":
            buckets[key]["t1"] += 1
        if row["tier_used"] in {"T3", "T4", "T5"} or row["outcome"] == "escalated":
            buckets[key]["t3"] += 1
    metrics: list[WeekMetric] = []
    for (week, task_type), counts in sorted(buckets.items(), reverse=True):
        total = counts["total"]
        t1 = counts["t1"]
        rate = round((100.0 * t1 / total), 1) if total else 0.0
        metrics.append(
            WeekMetric(
                week=week,
                task_type=task_type,
                total=total,
                t1_handled=t1,
                t3_escalated=counts["t3"],
                t1_rate_pct=rate,
                recovered_t3_equivalent_decisions=t1,
                recovered_minutes=t1 * T3_EQUIVALENT_MINUTES,
            )
        )
    return tuple(metrics)


def _week_totals(metrics: Iterable[WeekMetric]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "t1": 0, "recovered": 0, "minutes": 0})
    for metric in metrics:
        totals[metric.week]["total"] += metric.total
        totals[metric.week]["t1"] += metric.t1_handled
        totals[metric.week]["recovered"] += metric.recovered_t3_equivalent_decisions
        totals[metric.week]["minutes"] += metric.recovered_minutes
    return totals


def _rate(total: int, handled: int) -> float:
    return round(100.0 * handled / total, 1) if total else 0.0


def build_report(rows: Iterable[dict[str, Any]], *, now: dt.datetime | None = None) -> BandwidthReport:
    current = now or utc_now()
    normalized = normalize_rows(rows)
    metrics = aggregate_weekly(normalized)
    current_week = week_id(current)
    weeks = sorted({metric.week for metric in metrics}, reverse=True)
    previous_week = next((week for week in weeks if week < current_week), None)
    totals = _week_totals(metrics)
    current_totals = totals.get(current_week, {"total": 0, "t1": 0, "recovered": 0, "minutes": 0})
    current_rate = _rate(current_totals["total"], current_totals["t1"])
    previous_rate = None
    delta = None
    if previous_week:
        previous_totals = totals[previous_week]
        previous_rate = _rate(previous_totals["total"], previous_totals["t1"])
        delta = round(current_rate - previous_rate, 1)
    current_leaks = sorted(
        metric.task_type for metric in metrics if metric.week == current_week and metric.t3_escalated > 0
    )
    recommendations: list[str] = []
    if not normalized:
        status = "NO_DATA"
        recommendations.append("Start logging routing decisions through tools.bandwidth.routing_log before judging the trend.")
    elif current_rate < 50:
        status = "LEAK"
        recommendations.append("Review current-week T3 escalations and graduate safe repeated task types to T1 rules.")
    elif delta is not None and delta < 0:
        status = "WATCH"
        recommendations.append("T1 completion rate fell week-over-week; inspect leak task types before adding more automation.")
    else:
        status = "RECOVERING"
        recommendations.append("Keep the ledger running weekly and compare the 8-week T1 completion curve.")
    if current_leaks:
        recommendations.append("Task types still escalating this week: " + ", ".join(current_leaks[:6]))
    return BandwidthReport(
        generated_at=utc_stamp(current),
        status=status,
        current_week=current_week,
        previous_week=previous_week,
        weekly=metrics,
        current_t1_rate_pct=current_rate,
        previous_t1_rate_pct=previous_rate,
        t1_rate_delta_pct=delta,
        recovered_decisions=current_totals["recovered"],
        recovered_minutes=current_totals["minutes"],
        leak_task_types=tuple(current_leaks),
        recommendations=tuple(recommendations),
    )


def render_markdown(report: BandwidthReport) -> str:
    delta = "n/a" if report.t1_rate_delta_pct is None else f"{report.t1_rate_delta_pct:+.1f}%"
    previous = "n/a" if report.previous_t1_rate_pct is None else f"{report.previous_t1_rate_pct:.1f}%"
    hours = round(report.recovered_minutes / 60, 1)
    lines = [
        "# Bandwidth Ledger",
        "",
        "classification: PRIVATE",
        "privacy: internal routing metrics only; no message content, secrets, money movement, outreach, or live sends",
        "generated_by: d105 bandwidth ledger",
        f"generated_at: {report.generated_at}",
        f"status: {report.status}",
        f"current_week: {report.current_week}",
        "",
        "## Recovered This Week",
        "",
        f"- T1 handled {report.current_t1_rate_pct:.1f}% of logged routing tasks ({delta} WoW; previous {previous}).",
        f"- Recovered {report.recovered_decisions} estimated T3-equivalent decisions ({report.recovered_minutes} minutes / {hours} hours).",
        "",
        "## Bandwidth Leaks",
        "",
    ]
    if report.leak_task_types:
        lines.extend(f"- {item}" for item in report.leak_task_types)
    else:
        lines.append("- none logged this week")
    lines.extend(["", "## Weekly Task Metrics", ""])
    if report.weekly:
        lines.append("| Week | Task type | Total | T1 handled | T3+ escalated | T1 rate | Recovered minutes |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for metric in report.weekly[:40]:
            lines.append(
                f"| {metric.week} | {metric.task_type} | {metric.total} | {metric.t1_handled} | "
                f"{metric.t3_escalated} | {metric.t1_rate_pct:.1f}% | {metric.recovered_minutes} |"
            )
    else:
        lines.append("_No routing ledger rows found yet._")
    lines.extend(["", "## One Sentence", ""])
    lines.append(
        f"The system recovered {report.recovered_decisions} estimated T3-equivalent decisions this week by graduating them to T1."
    )
    lines.extend(["", "## Recommended Repairs", ""])
    lines.extend(f"- {item}" for item in report.recommendations)
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: BandwidthReport,
    *,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
    state_path: Path = DEFAULT_STATE,
) -> None:
    payload = json.dumps(report.to_json(), indent=2, sort_keys=True) + "\n"
    rendered = render_markdown(report)
    for path, content in ((json_path, payload), (markdown_path, rendered), (state_path, rendered)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-path", type=Path, default=DEFAULT_MD)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument("--no-write", action="store_true", help="Do not write report artifacts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(read_jsonl(args.ledger))
    if not args.no_write:
        write_report(report, json_path=args.json_path, markdown_path=args.markdown_path, state_path=args.state_path)
    if args.json:
        print(json.dumps(report.to_json(), sort_keys=True))
    else:
        print(f"bandwidth ledger: {report.status} · T1 {report.current_t1_rate_pct:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

