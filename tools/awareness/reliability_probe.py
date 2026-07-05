#!/usr/bin/env python3
"""Continuously measure behavioral bot awareness reliability.

The primary metric is whether the live bot answer path can answer a factual
question derived from the latest session insight. The older context-render
check is retained only as a secondary continuity signal.
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime as dt
import html
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Awaitable, Callable

from verify_awareness import AwarenessProbe, DEFAULT_DB_URL, verify_bot_response, verify_context_render_continuity

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "awareness_reliability.json"
DEFAULT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "awareness_reliability.md"
DEFAULT_COOLDOWN_FILE = Path(
    os.environ.get("AWARENESS_RELIABILITY_COOLDOWN_FILE", "/opt/fpai-build/.awareness_reliability_last_alert")
)
SCHEMA = "awareness-reliability.v1"


@dataclasses.dataclass(frozen=True)
class ReliabilityMetric:
    ok: bool
    reliability: float
    successes: int
    total: int
    threshold: float
    current_ok: bool
    reason: str
    latest_title: str = ""
    behavioral_pass: bool = False
    context_render_continuity: bool | None = None
    question: str = ""
    answer: str = ""
    matched_keywords: tuple[str, ...] = ()
    alert_sent: bool = False

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(value: dt.datetime | None = None) -> str:
    return (value or utc_now()).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def recent_probe_rows(path: Path, *, now: dt.datetime, window_hours: float, limit: int) -> list[dict[str, Any]]:
    cutoff = now - dt.timedelta(hours=window_hours)
    rows = []
    for row in read_jsonl(path):
        if row.get("event") != "awareness_reliability_probe":
            continue
        ts = parse_time(row.get("ts"))
        if ts is None or ts >= cutoff:
            rows.append(row)
    return rows[-limit:]


def append_ops(path: Path, row: dict[str, Any], *, now: dt.datetime) -> bool:
    payload = {"ts": utc_stamp(now), **row}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return True
    except Exception:
        return False


def compute_metric(
    *,
    current: AwarenessProbe,
    history: list[dict[str, Any]],
    threshold: float,
) -> ReliabilityMetric:
    outcomes = [bool(row.get("behavioral_pass")) for row in history if "behavioral_pass" in row]
    outcomes.append(bool(current.ok))
    total = len(outcomes)
    successes = sum(1 for ok in outcomes if ok)
    reliability = successes / total if total else 0.0
    reason = current.reason or ("ok" if current.ok else "behavioral awareness probe failed")
    return ReliabilityMetric(
        ok=reliability >= threshold and current.ok,
        reliability=reliability,
        successes=successes,
        total=total,
        threshold=threshold,
        current_ok=current.ok,
        reason=reason,
        latest_title=current.latest_title,
        behavioral_pass=bool(current.behavioral_pass if current.behavioral_pass is not None else current.ok),
        context_render_continuity=current.context_render_continuity,
        question=current.question,
        answer=current.answer,
        matched_keywords=current.matched_keywords,
    )


def write_reports(metric: ReliabilityMetric, *, json_path: Path, markdown_path: Path, now: dt.datetime) -> None:
    payload = {
        "schema": SCHEMA,
        "generated_at": utc_stamp(now),
        "primary_metric": "behavioral_bot_answer",
        "secondary_signal": "context_render_continuity",
        "metric": metric.to_json(),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = "PASS" if metric.ok else "FAIL"
    markdown_path.write_text(
        "\n".join(
            [
                "# Awareness Reliability",
                "",
                "Primary metric: behavioral bot-answer correctness. Secondary signal: context-render continuity.",
                "",
                f"- Status: {status}",
                f"- Reliability: {metric.reliability:.1%} ({metric.successes}/{metric.total})",
                f"- Threshold: {metric.threshold:.1%}",
                f"- Behavioral pass: {metric.behavioral_pass}",
                f"- Context-render continuity: {metric.context_render_continuity}",
                f"- Latest title: {metric.latest_title or '-'}",
                f"- Question: {metric.question or '-'}",
                f"- Matched keywords: {', '.join(metric.matched_keywords) if metric.matched_keywords else '-'}",
                f"- Reason: {metric.reason or '-'}",
                f"- Generated: {utc_stamp(now)}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def should_alert(metric: ReliabilityMetric, cooldown_file: Path, now: dt.datetime, *, cooldown_minutes: float) -> bool:
    if metric.reliability >= metric.threshold:
        return False
    last = parse_time(cooldown_file.read_text(encoding="utf-8").strip()) if cooldown_file.exists() else None
    if last and (now - last).total_seconds() < cooldown_minutes * 60:
        return False
    return True


def alert_message(metric: ReliabilityMetric, markdown_path: Path) -> str:
    return (
        "<b>Behavioral awareness reliability below threshold</b>\n"
        f"Reliability: {metric.reliability:.1%} ({metric.successes}/{metric.total})\n"
        f"Threshold: {metric.threshold:.1%}\n"
        f"Behavioral pass: {'PASS' if metric.behavioral_pass else 'FAIL'}\n"
        f"Context-render continuity: {metric.context_render_continuity}\n"
        f"Reason: {html.escape(metric.reason or '-')}\n"
        f"Report: {html.escape(str(markdown_path))}"
    )


def send_alert(repo_root: Path, message: str) -> bool:
    # 2026-07-05 (James): this is INTERNAL system monitoring — raw "reliability 0%/FAIL"
    # diagnostics do not belong in James's chat (P17). The signal file is still written for
    # self-heal + the council. Never push to James from here.
    return False
    notifier = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not notifier.exists():
        return False
    try:
        result = subprocess.run(
            [str(notifier), message],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    output = f"{result.stdout}\n{result.stderr}"
    return result.returncode == 0 and "notify: sent" in output


def run(
    *,
    repo_root: Path = REPO_ROOT,
    db_url: str = DEFAULT_DB_URL,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
    cooldown_file: Path = DEFAULT_COOLDOWN_FILE,
    threshold: float = 0.95,
    window_hours: float = 24.0,
    sample_limit: int = 100,
    cooldown_minutes: float = 30.0,
    source: str = "timer",
    send_alert_flag: bool = False,
    now: dt.datetime | None = None,
    verifier: Callable[[], Awaitable[AwarenessProbe]] | None = None,
    notifier: Callable[[Path, str], bool] = send_alert,
) -> ReliabilityMetric:
    current_time = now or utc_now()
    history = recent_probe_rows(ops_ledger, now=current_time, window_hours=window_hours, limit=max(0, sample_limit - 1))
    probe = asyncio.run(
        verifier()
        if verifier
        else verify_bot_response(
            db_url=db_url,
            context_probe=lambda: verify_context_render_continuity(db_url=db_url),
        )
    )
    metric = compute_metric(current=probe, history=history, threshold=threshold)
    append_ops(
        ops_ledger,
        {
            "event": "awareness_reliability_probe",
            "source": source,
            "ok": probe.ok,
            "behavioral_pass": metric.behavioral_pass,
            "context_render_continuity": metric.context_render_continuity,
            "reliability": round(metric.reliability, 6),
            "successes": metric.successes,
            "total": metric.total,
            "threshold": metric.threshold,
            "reason": probe.reason,
            "latest_title": probe.latest_title,
            "question": probe.question,
            "answer": probe.answer[:1000],
            "matched_keywords": list(probe.matched_keywords),
        },
        now=current_time,
    )
    if send_alert_flag and should_alert(metric, cooldown_file, current_time, cooldown_minutes=cooldown_minutes):
        sent = notifier(repo_root, alert_message(metric, markdown_path))
        metric = dataclasses.replace(metric, alert_sent=sent)
        if sent:
            cooldown_file.parent.mkdir(parents=True, exist_ok=True)
            cooldown_file.write_text(utc_stamp(current_time), encoding="utf-8")
    write_reports(metric, json_path=json_path, markdown_path=markdown_path, now=current_time)
    return metric


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-path", type=Path, default=DEFAULT_MD)
    parser.add_argument("--cooldown-file", type=Path, default=DEFAULT_COOLDOWN_FILE)
    parser.add_argument("--threshold", type=float, default=0.95)
    parser.add_argument("--window-hours", type=float, default=24.0)
    parser.add_argument("--sample-limit", type=int, default=100)
    parser.add_argument("--cooldown-minutes", type=float, default=30.0)
    parser.add_argument("--source", default="timer")
    parser.add_argument("--send-alert", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    metric = run(
        db_url=args.db_url,
        ops_ledger=args.ops_ledger,
        json_path=args.json_path,
        markdown_path=args.markdown_path,
        cooldown_file=args.cooldown_file,
        threshold=args.threshold,
        window_hours=args.window_hours,
        sample_limit=args.sample_limit,
        cooldown_minutes=args.cooldown_minutes,
        source=args.source,
        send_alert_flag=args.send_alert,
    )
    if args.json:
        print(json.dumps(metric.to_json(), sort_keys=True))
    else:
        print(f"behavioral awareness reliability: {metric.reliability:.1%} ({metric.successes}/{metric.total})")
    # Two axes, not one (P6): a low-but-MEASURED value is a successful probe run — the alert +
    # ledger convey "below threshold"; the service must NOT report exit-failure for it (that spammed
    # a fake 'service failed' + hid real breakage). Exit nonzero ONLY on a genuine probe/infra failure
    # (couldn't connect/measure), so systemd 'failed' means the probe is broken, not that awareness is low.
    reason = (metric.reason or "").lower()
    infra_failure = any(s in reason for s in (
        "connection", "auth", "could not", "lookup failed", "unavailable", "timeout", "traceback"))
    return 1 if infra_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
