#!/usr/bin/env python3
"""Rung 2 self-directing loop foreman.

The foreman reads ready buildstream intents, assigns each to the Rung 1
apprentice runner, and stops at Reserved-Class gates. It is runnable on demand
only; nothing here wires into the live autoloop.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.apprentice.run import ApprenticeResult, result_payload, run_intent
from tools.apprentice.select import DEFAULT_BUILDSTREAM, load_intents, normalize_for_apprentice

DEFAULT_QUEUE = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
DEFAULT_LOG = REPO_ROOT / "tools" / "loop" / "runs" / "direct_runs.jsonl"
DEFAULT_MEMORY = REPO_ROOT / "tools" / "loop" / "runs" / "foreman_memory.json"
DEFAULT_HANDOFF = REPO_ROOT / "docs" / "codex" / "HANDOFF.md"


@dataclasses.dataclass(frozen=True)
class IntentOutcome:
    intent_id: str
    status: str
    steps_executed: int
    gates_raised: int
    first_gate: str | None
    apprentice: ApprenticeResult


@dataclasses.dataclass(frozen=True)
class TickSummary:
    dry_run: bool
    max_intents: int
    outcomes: list[IntentOutcome]
    skipped_intents: list[str]
    log_path: Path | None
    memory_path: Path | None
    handoff_path: Path | None

    @property
    def intents_touched(self) -> int:
        return len(self.outcomes)

    @property
    def steps_executed(self) -> int:
        return sum(outcome.steps_executed for outcome in self.outcomes)

    @property
    def gates_raised(self) -> int:
        return sum(outcome.gates_raised for outcome in self.outcomes)


def ready_intents(buildstream_path: Path | str = DEFAULT_BUILDSTREAM) -> list[dict[str, Any]]:
    """Load READY intents with a next move, ordered by weight then id."""
    intents = [
        intent
        for intent in load_intents(buildstream_path)
        if str(intent.get("status", "")).lower() == "ready" and str(intent.get("next", "")).strip()
    ]
    return sorted(intents, key=lambda item: (-int(item.get("weight", 0)), str(item.get("id", ""))))


def tick(
    *,
    dry_run: bool = False,
    max_intents: int = 1,
    buildstream_path: Path | str = DEFAULT_BUILDSTREAM,
    queue_path: Path | str = DEFAULT_QUEUE,
    log_path: Path | str | None = DEFAULT_LOG,
    memory_path: Path | str | None = DEFAULT_MEMORY,
    apprentice_log_path: Path | str | None = None,
    handoff_path: Path | str | None = DEFAULT_HANDOFF,
) -> TickSummary:
    """Run a bounded foreman tick across ready intents."""
    if max_intents < 1:
        raise ValueError("max_intents must be at least 1")

    memory = load_memory(memory_path)
    open_gate_ids = _open_gate_ids(queue_path)
    outcomes: list[IntentOutcome] = []
    skipped: list[str] = []
    for intent in ready_intents(buildstream_path):
        intent_id = str(intent.get("id", "")).strip()
        if is_blocked_by_memory(intent_id, memory, open_gate_ids):
            skipped.append(intent_id)
            continue
        if len(outcomes) >= max_intents:
            break
        apprentice_intent = normalize_for_apprentice(intent)
        apprentice = run_intent(
            apprentice_intent,
            dry_run=dry_run,
            queue_path=queue_path,
            log_path=apprentice_log_path,
            handoff_path=None,
        )
        outcome = _outcome(intent, apprentice)
        outcomes.append(outcome)
        update_memory(memory, intent, outcome)

    summary = TickSummary(
        dry_run=dry_run,
        max_intents=max_intents,
        outcomes=outcomes,
        skipped_intents=skipped,
        log_path=Path(log_path) if log_path else None,
        memory_path=Path(memory_path) if memory_path else None,
        handoff_path=Path(handoff_path) if handoff_path else None,
    )
    _record_memory(summary, memory, memory_path)
    _record_tick(summary, log_path)
    _record_handoff(summary, handoff_path)
    return summary


def _outcome(intent: dict[str, Any], apprentice: ApprenticeResult) -> IntentOutcome:
    executed = [step for step in apprentice.steps if not step.reserved]
    gates = [step for step in apprentice.steps if step.reserved]
    return IntentOutcome(
        intent_id=str(intent.get("id") or apprentice.intent_id),
        status=apprentice.status,
        steps_executed=len(executed),
        gates_raised=len(gates),
        first_gate=gates[0].step if gates else None,
        apprentice=apprentice,
    )


def _record_tick(summary: TickSummary, log_path: Path | str | None) -> None:
    if summary.dry_run or not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(tick_payload(summary), ensure_ascii=False, sort_keys=True) + "\n")


def _record_memory(summary: TickSummary, memory: dict[str, Any], memory_path: Path | str | None) -> None:
    if summary.dry_run or not memory_path:
        return
    save_memory(memory, memory_path)


def _record_handoff(summary: TickSummary, handoff_path: Path | str | None) -> None:
    if summary.dry_run or not handoff_path:
        return
    path = Path(handoff_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing.rstrip() + "\n\n" + render_handoff(summary), encoding="utf-8")


def render_handoff(summary: TickSummary) -> str:
    lines = [
        f"### {dt.date.today().isoformat()} · Self-directing loop tick",
        "",
        "- Status: done",
        f"- Intents touched: {summary.intents_touched}",
        f"- Steps executed: {summary.steps_executed}",
        f"- Gates raised: {summary.gates_raised}",
        f"- Skipped blocked intents: {len(summary.skipped_intents)}",
        "- Outcomes:",
    ]
    if not summary.outcomes:
        lines.append("  - no READY intents found")
    for outcome in summary.outcomes:
        detail = f"  - `{outcome.intent_id}` -> `{outcome.status}`"
        if outcome.first_gate:
            detail += f" (gate: `{outcome.first_gate}`)"
        lines.append(detail)
    if summary.skipped_intents:
        lines.append("- Memory skipped: " + ", ".join(f"`{intent_id}`" for intent_id in summary.skipped_intents))
    lines.extend(
        [
            "- Safety: no Reserved-Class step was executed; gates were surfaced through the apprentice boundary.",
            "- Live autoloop wiring: not touched.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def tick_payload(summary: TickSummary) -> dict[str, Any]:
    return {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "dry_run": summary.dry_run,
        "max_intents": summary.max_intents,
        "intents_touched": summary.intents_touched,
        "steps_executed": summary.steps_executed,
        "gates_raised": summary.gates_raised,
        "skipped_intents": summary.skipped_intents,
        "outcomes": [
            {
                "intent_id": outcome.intent_id,
                "status": outcome.status,
                "steps_executed": outcome.steps_executed,
                "gates_raised": outcome.gates_raised,
                "first_gate": outcome.first_gate,
                "apprentice": result_payload(outcome.apprentice),
            }
            for outcome in summary.outcomes
        ],
        "log_path": str(summary.log_path) if summary.log_path else None,
        "memory_path": str(summary.memory_path) if summary.memory_path else None,
        "handoff_path": str(summary.handoff_path) if summary.handoff_path else None,
    }


def load_memory(path: Path | str | None = DEFAULT_MEMORY) -> dict[str, Any]:
    if not path:
        return {"version": 1, "intents": {}}
    memory_path = Path(path)
    if not memory_path.exists():
        return {"version": 1, "intents": {}}
    try:
        data = json.loads(memory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid foreman memory JSON: {memory_path}") from exc
    intents = data.get("intents", {})
    if not isinstance(intents, dict):
        raise ValueError("foreman memory must contain an intents object")
    return {"version": int(data.get("version", 1)), "intents": intents}


def save_memory(memory: dict[str, Any], path: Path | str = DEFAULT_MEMORY) -> None:
    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_blocked_by_memory(intent_id: str, memory: dict[str, Any], open_gate_ids: set[str]) -> bool:
    if not intent_id:
        return False
    record = memory.get("intents", {}).get(intent_id)
    if not isinstance(record, dict) or record.get("status") != "gated":
        return False
    gate_id = str(record.get("gate_id") or "").strip()
    if not gate_id:
        return True
    return gate_id in open_gate_ids


def update_memory(memory: dict[str, Any], intent: dict[str, Any], outcome: IntentOutcome) -> None:
    intent_id = outcome.intent_id
    gate = _first_gate(outcome.apprentice)
    gate_id = _gate_id(gate)
    if outcome.status == "gated":
        next_action = f"wait for human-edge gate {gate_id}" if gate_id else "wait for human-edge gate"
    elif outcome.status == "completed":
        next_action = "select next READY intent"
    else:
        next_action = "review foreman outcome"
    memory.setdefault("intents", {})[intent_id] = {
        "intent_id": intent_id,
        "title": intent.get("title"),
        "last_attempted": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "status": outcome.status,
        "safe_steps_done": [
            step.step for step in outcome.apprentice.steps if not step.reserved
        ],
        "gate_id": gate_id,
        "gate_step": outcome.first_gate,
        "next_allowed_action": next_action,
    }


def _first_gate(apprentice: ApprenticeResult) -> dict[str, Any]:
    for step in apprentice.steps:
        if step.reserved and isinstance(step.gate, dict):
            return step.gate
    return {}


def _gate_id(gate: dict[str, Any]) -> str | None:
    value = gate.get("id") or gate.get("gate_id")
    return str(value).strip() if value else None


def _open_gate_ids(queue_path: Path | str) -> set[str]:
    path = Path(queue_path)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    gates = data.get("gates", [])
    if not isinstance(gates, list):
        return set()
    return {
        str(gate.get("id", "")).strip()
        for gate in gates
        if isinstance(gate, dict) and gate.get("state") == "open" and str(gate.get("id", "")).strip()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a bounded self-directing loop tick.")
    parser.add_argument("--buildstream", type=Path, default=DEFAULT_BUILDSTREAM)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--memory", type=Path, default=DEFAULT_MEMORY)
    parser.add_argument("--apprentice-log", type=Path, default=None)
    parser.add_argument("--handoff", type=Path, default=DEFAULT_HANDOFF)
    parser.add_argument("--max-intents", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    summary = tick(
        dry_run=args.dry_run,
        max_intents=args.max_intents,
        buildstream_path=args.buildstream,
        queue_path=args.queue,
        log_path=args.log,
        memory_path=args.memory,
        apprentice_log_path=args.apprentice_log,
        handoff_path=args.handoff,
    )
    payload = tick_payload(summary)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"intents={summary.intents_touched} "
            f"steps={summary.steps_executed} "
            f"gates={summary.gates_raised} "
            f"skipped={len(summary.skipped_intents)}"
        )
        for outcome in summary.outcomes:
            gate = f" gate={outcome.first_gate}" if outcome.first_gate else ""
            print(f"{outcome.intent_id}: {outcome.status}{gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
