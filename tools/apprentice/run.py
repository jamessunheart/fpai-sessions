#!/usr/bin/env python3
"""Rung 1 apprentice runner.

An apprentice owns one buildstream item, does only AI-doable work, and pauses at
the first Reserved-Class bottleneck by writing a human-edge gate. It is not wired
into the live loop.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.reserved.classify import gate_or_proceed, is_reserved

DEFAULT_LOG = REPO_ROOT / "tools" / "apprentice" / "runs" / "apprentice_runs.jsonl"

GateWriter = Callable[..., dict[str, Any]]


@dataclasses.dataclass
class StepResult:
    step: str
    reserved: bool
    action: str
    reason: str
    gate: dict[str, Any] | None = None


@dataclasses.dataclass
class ApprenticeResult:
    intent_id: str
    status: str
    dry_run: bool
    steps: list[StepResult]
    log_path: Path | None

    @property
    def gated(self) -> bool:
        return self.status == "gated"


def run_intent(
    intent: dict[str, Any],
    *,
    dry_run: bool = False,
    gate_writer: GateWriter | None = None,
    queue_path: Path | str | None = None,
    log_path: Path | str | None = DEFAULT_LOG,
    handoff_path: Path | str | None = None,
) -> ApprenticeResult:
    """Run one intent until completion or the first Reserved-Class bottleneck."""
    intent_id = str(intent.get("id") or intent.get("ident") or "unknown-intent").strip()
    stream = str(intent.get("stream") or "Game").strip()
    steps = decompose_steps(intent)
    results: list[StepResult] = []

    for step in steps:
        verdict = is_reserved(step, {"stream": stream, "intent_id": intent_id})
        if verdict["reserved"]:
            gate = _gate_for_step(
                intent_id=intent_id,
                stream=stream,
                step=step,
                dry_run=dry_run,
                gate_writer=gate_writer,
                queue_path=queue_path,
            )
            results.append(
                StepResult(
                    step=step,
                    reserved=True,
                    action="gate",
                    reason=verdict["reason"],
                    gate=gate,
                )
            )
            apprentice = ApprenticeResult(intent_id, "gated", dry_run, results, Path(log_path) if log_path else None)
            _record_run(apprentice, intent, log_path, dry_run)
            _record_handoff(apprentice, handoff_path, dry_run)
            return apprentice

        results.append(
            StepResult(
                step=step,
                reserved=False,
                action=delegable_action(step),
                reason=verdict["reason"],
            )
        )

    apprentice = ApprenticeResult(intent_id, "completed", dry_run, results, Path(log_path) if log_path else None)
    _record_run(apprentice, intent, log_path, dry_run)
    _record_handoff(apprentice, handoff_path, dry_run)
    return apprentice


def decompose_steps(intent: dict[str, Any]) -> list[str]:
    """Build a minimal v1 plan from the intent's next move."""
    raw = str(intent.get("next") or intent.get("next_move") or intent.get("title") or "").strip()
    if not raw:
        raw = "summarize the intent and propose the next safe step"
    parts = re.split(r"\s*(?:;|\n+|,\s+then\s+|\s+then\s+)\s*", raw)
    steps = [p.strip(" -") for p in parts if p.strip(" -")]
    return steps or [raw]


def delegable_action(step: str) -> str:
    low = step.lower()
    if any(word in low for word in ("code", "implement", "fix", "build")):
        return "draft-codex-kickoff"
    if any(word in low for word in ("lead", "outreach", "message", "email")):
        return "draft-review-artifact"
    return "record-advisory-work"


def _gate_for_step(
    *,
    intent_id: str,
    stream: str,
    step: str,
    dry_run: bool,
    gate_writer: GateWriter | None,
    queue_path: Path | str | None,
) -> dict[str, Any]:
    context = {
        "stream": stream,
        "verbs": ["approve", "reject", "checkpoint"],
    }
    if dry_run:
        gate = gate_or_proceed(step, context, apply_gate=False)["gate"]
        return gate or {}
    writer = gate_writer or _queue_gate_writer(queue_path)
    gate = gate_or_proceed(step, context, apply_gate=True, gate_writer=writer)["gate"]
    if isinstance(gate, dict):
        gate.setdefault("intent_id", intent_id)
    return gate if isinstance(gate, dict) else {"gate": gate}


def _queue_gate_writer(queue_path: Path | str | None) -> GateWriter:
    def write_gate(**payload: Any) -> dict[str, Any]:
        from tools.queue.build import add_gate

        if queue_path:
            payload["path"] = queue_path
        return add_gate(**payload)

    return write_gate


def _record_run(
    result: ApprenticeResult,
    intent: dict[str, Any],
    log_path: Path | str | None,
    dry_run: bool,
) -> None:
    if dry_run or not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "intent_id": result.intent_id,
        "status": result.status,
        "intent": intent,
        "steps": [dataclasses.asdict(step) for step in result.steps],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _record_handoff(result: ApprenticeResult, handoff_path: Path | str | None, dry_run: bool) -> None:
    if dry_run or not handoff_path:
        return
    path = Path(handoff_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"### Apprentice run · intent `{result.intent_id}`",
        "",
        f"- Status: {result.status}",
        f"- Steps: {len(result.steps)}",
    ]
    for step in result.steps:
        if step.reserved:
            lines.append(f"- Gate: `{step.step}` — {step.reason}")
        else:
            lines.append(f"- Did: `{step.step}` — {step.action}")
    lines.append("")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(text.rstrip() + "\n\n" + "\n".join(lines), encoding="utf-8")


def result_payload(result: ApprenticeResult) -> dict[str, Any]:
    return {
        "intent_id": result.intent_id,
        "status": result.status,
        "dry_run": result.dry_run,
        "log_path": str(result.log_path) if result.log_path else None,
        "steps": [dataclasses.asdict(step) for step in result.steps],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one apprentice intent safely.")
    parser.add_argument("--intent-json", required=True, help="JSON object with id, stream, and next fields")
    parser.add_argument("--dry-run", action="store_true", help="plan/classify only; write no gate/log")
    parser.add_argument("--queue", type=Path, default=None, help="optional queue JSON path for gated runs")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="per-run JSONL log path")
    parser.add_argument("--handoff", type=Path, default=None, help="optional handoff path for run summary")
    args = parser.parse_args(argv)

    intent = json.loads(args.intent_json)
    result = run_intent(
        intent,
        dry_run=args.dry_run,
        queue_path=args.queue,
        log_path=args.log,
        handoff_path=args.handoff,
    )
    print(json.dumps(result_payload(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
