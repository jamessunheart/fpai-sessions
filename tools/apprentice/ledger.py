"""JSONL ledger for apprentice dry-run reviews."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path(__file__).resolve().parent / "runs" / "apprentice_review_ledger.jsonl"


def ledger_row(payload: dict[str, Any]) -> dict[str, Any]:
    intent = payload["selected_intent"]
    pause = payload.get("would_pause_at") or {}
    gate = pause.get("gate") or {}
    return {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "intent_id": intent.get("id"),
        "intent_title": intent.get("title"),
        "stream": intent.get("stream"),
        "status": payload["apprentice_dry_run"].get("status"),
        "would_do": [
            {
                "step": step.get("step"),
                "action": step.get("action"),
            }
            for step in payload.get("would_do", [])
        ],
        "would_pause_at": pause.get("step"),
        "reserved_reason": pause.get("reason"),
        "gate_question": gate.get("question"),
        "artifact_path": payload.get("artifact_path"),
    }


def append_ledger(payload: dict[str, Any], path: Path | str = DEFAULT_LEDGER) -> Path:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    row = ledger_row(payload)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return ledger_path
