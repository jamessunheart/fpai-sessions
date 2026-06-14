#!/usr/bin/env python3
"""Reflect on apprentice review ledger rows.

This is read-only by default: it summarizes where dry-run apprentices keep
pausing, so future specs can improve the bottleneck instead of guessing.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.apprentice.ledger import DEFAULT_LEDGER


def load_rows(path: Path | str = DEFAULT_LEDGER) -> list[dict[str, Any]]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid ledger JSON at {ledger_path}:{line_no}") from exc
    return rows


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pauses = collections.Counter(row.get("would_pause_at") or "none" for row in rows)
    reasons = collections.Counter(row.get("reserved_reason") or "none" for row in rows)
    streams = collections.Counter(row.get("stream") or "unknown" for row in rows)
    intents = collections.Counter(row.get("intent_id") or "unknown" for row in rows)
    gated = sum(1 for row in rows if row.get("status") == "gated")
    return {
        "total_runs": len(rows),
        "gated_runs": gated,
        "completed_runs": len(rows) - gated,
        "top_pauses": _top(pauses),
        "top_reserved_reasons": _top(reasons),
        "top_streams": _top(streams),
        "top_intents": _top(intents),
        "next_improvement": next_improvement(pauses, reasons, len(rows)),
    }


def next_improvement(
    pauses: collections.Counter[str],
    reasons: collections.Counter[str],
    total: int,
) -> str:
    if total == 0:
        return "Run apprentice dry-runs with --ledger first; no reflection data exists yet."
    pause, pause_count = pauses.most_common(1)[0]
    reason, reason_count = reasons.most_common(1)[0]
    if pause != "none":
        return (
            f"Most repeated pause is `{pause}` ({pause_count}x), with top reason `{reason}` "
            f"({reason_count}x). Improve the apprentice around that bottleneck next."
        )
    return "Most dry-runs complete without a Reserved-Class pause; next improvement can focus on richer delegated artifacts."


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Apprentice Reflection",
        "",
        f"- total runs: `{summary['total_runs']}`",
        f"- gated runs: `{summary['gated_runs']}`",
        f"- completed runs: `{summary['completed_runs']}`",
        "",
        "## Top Pauses",
        "",
    ]
    lines.extend(_counter_lines(summary["top_pauses"]))
    lines.extend(["", "## Top Reserved Reasons", ""])
    lines.extend(_counter_lines(summary["top_reserved_reasons"]))
    lines.extend(["", "## Top Streams", ""])
    lines.extend(_counter_lines(summary["top_streams"]))
    lines.extend(["", "## Top Intents", ""])
    lines.extend(_counter_lines(summary["top_intents"]))
    lines.extend(["", "## Next Improvement", "", summary["next_improvement"], ""])
    return "\n".join(lines)


def write_report(summary: dict[str, Any], path: Path | str) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(summary), encoding="utf-8")
    return report_path


def _top(counter: collections.Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def _counter_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["_No data._"]
    return [f"- `{row['value']}`: {row['count']}" for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize apprentice dry-run ledger rows.")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--report", type=Path, default=None, help="optional Markdown report path")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    summary = summarize_rows(load_rows(args.ledger))
    if args.report:
        path = write_report(summary, args.report)
        summary["report_path"] = str(path)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
