#!/usr/bin/env python3
"""Dry-run selector for the next apprentice candidate.

This reads the repo buildstream, chooses one ready intent, and runs the
apprentice in dry-run mode only. It writes no queue gates, logs, or handoff rows.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.apprentice.artifact import write_review_artifact
from tools.apprentice.ledger import append_ledger
from tools.apprentice.run import ApprenticeResult, result_payload, run_intent

DEFAULT_BUILDSTREAM = REPO_ROOT / "docs" / "codex" / "INTENT_BUILDSTREAM.md"


def load_intents(path: Path | str = DEFAULT_BUILDSTREAM) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    intents: list[dict[str, Any]] = []
    for line in text.splitlines():
        parsed = parse_intent_line(line)
        if parsed:
            intents.append(parsed)
    return intents


def parse_intent_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line.startswith("- ") or "|" not in line:
        return None
    segments = [part.strip() for part in line[2:].split("|")]
    title = segments[0]
    intent: dict[str, Any] = {"title": title}
    for segment in segments[1:]:
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        key = key.strip().lower().replace("-", "_")
        intent[key] = value.strip()
    if "id" not in intent:
        return None
    intent["weight"] = _int_value(intent.get("weight") or intent.get("value") or "0")
    intent["status"] = str(intent.get("status", "")).lower()
    if "stream" not in intent:
        intent["stream"] = "Game"
    if "next" not in intent:
        intent["next"] = title
    return intent


def select_intent(intents: list[dict[str, Any]], intent_id: str | None = None) -> dict[str, Any]:
    if intent_id:
        for intent in intents:
            if intent.get("id") == intent_id:
                return intent
        raise KeyError(f"intent not found: {intent_id}")
    ready = [intent for intent in intents if intent.get("status") == "ready"]
    if not ready:
        raise ValueError("no ready apprentice intents found")
    return sorted(ready, key=lambda item: (int(item.get("weight", 0)), str(item.get("id", ""))), reverse=True)[0]


def dry_run_intent(intent: dict[str, Any]) -> ApprenticeResult:
    return run_intent(normalize_for_apprentice(intent), dry_run=True, log_path=None)


def normalize_for_apprentice(intent: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(intent)
    next_move = str(normalized.get("next", "")).strip()
    verbs = str(normalized.get("verbs", "")).lower()
    tier = str(normalized.get("tier", "")).lower()
    if tier == "human" and "lead" in next_move.lower():
        normalized["next"] = "draft candidate leads; approve and send these 5"
        normalized["source_next"] = next_move
    elif "draft" in verbs and "checkpoint" in verbs and "pick" in next_move.lower():
        normalized["next"] = f"draft options for: {next_move}; approve final choice"
        normalized["source_next"] = next_move
    return normalized


def selector_payload(intent: dict[str, Any], result: ApprenticeResult) -> dict[str, Any]:
    steps = result_payload(result)["steps"]
    first_gate = next((step for step in steps if step["reserved"]), None)
    return {
        "selected_intent": {
            "id": intent.get("id"),
            "title": intent.get("title"),
            "stream": intent.get("stream"),
            "status": intent.get("status"),
            "weight": intent.get("weight"),
            "source_next": intent.get("source_next") or intent.get("next"),
        },
        "apprentice_dry_run": result_payload(result),
        "would_do": [step for step in steps if not step["reserved"]],
        "would_pause_at": first_gate,
        "why": bottleneck_reason(intent, first_gate),
    }


def bottleneck_reason(intent: dict[str, Any], gate_step: dict[str, Any] | None) -> str:
    if not gate_step:
        return "No Reserved-Class bottleneck found; the apprentice would complete the dry-run plan."
    return (
        f"Intent `{intent.get('id')}` can advance through delegable prep, then pauses only at "
        f"`{gate_step['step']}` because Rung 0 classified that step as Reserved-Class."
    )


def _int_value(value: Any) -> int:
    match = re.search(r"-?\d+", str(value))
    return int(match.group(0)) if match else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select one buildstream intent for apprentice dry-run.")
    parser.add_argument("--buildstream", type=Path, default=DEFAULT_BUILDSTREAM)
    parser.add_argument("--id", dest="intent_id", default=None, help="select a specific intent id")
    parser.add_argument("--artifact", type=Path, default=None, help="optional Markdown review artifact path")
    parser.add_argument("--ledger", type=Path, default=None, help="optional JSONL review ledger path")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args(argv)

    intents = load_intents(args.buildstream)
    selected = select_intent(intents, args.intent_id)
    apprentice_intent = normalize_for_apprentice(selected)
    result = dry_run_intent(selected)
    payload = selector_payload(apprentice_intent, result)
    if args.artifact:
        path = write_review_artifact(payload, args.artifact)
        payload["artifact_path"] = str(path)
    if args.ledger:
        path = append_ledger(payload, args.ledger)
        payload["ledger_path"] = str(path)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"selected: {payload['selected_intent']['id']}")
        print(f"status: {payload['apprentice_dry_run']['status']}")
        for step in payload["would_do"]:
            print(f"would do: {step['step']} ({step['action']})")
        if payload["would_pause_at"]:
            print(f"would pause: {payload['would_pause_at']['step']}")
        print(f"why: {payload['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
