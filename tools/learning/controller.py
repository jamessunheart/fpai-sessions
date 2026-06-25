#!/usr/bin/env python3
"""Unified signal ingestion for the continuous learning controller.

Signal capture is safe by default: if a live ``brain_index`` connection is not
provided, rows are appended to a local JSONL proof file instead of disappearing.
Fine-tune readiness remains gated by ``LEARNING_ENABLED=1`` and signal volume.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIGNAL_LEDGER = Path(os.environ.get("LEARNING_SIGNAL_LEDGER", "/opt/fpai-build/learning_datasets/learning_signals.jsonl"))
VALID_SIGNAL_TYPES = {"correction", "approval", "reversal", "merge_outcome", "engagement", "council_verdict"}
MIN_SIGNALS = 100


class LearningSignalError(ValueError):
    """Raised when a learning signal is malformed."""


@dataclass(frozen=True)
class SignalWriteResult:
    status: str
    signal_type: str
    task_id: str
    value: float
    weight: float
    destination: str

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signal_type": self.signal_type,
            "task_id": self.task_id,
            "value": self.value,
            "weight": self.weight,
            "destination": self.destination,
        }


def learning_enabled() -> bool:
    return os.environ.get("LEARNING_ENABLED") == "1"


def ready_for_finetune(signal_count: int, *, min_signals: int = MIN_SIGNALS) -> bool:
    return learning_enabled() and signal_count >= min_signals


def collect_signal(
    task_id: str,
    prompt: str,
    response: str,
    signal_type: str,
    value: float,
    *,
    weight: float = 1.0,
    conn: Any | None = None,
    dsn: str | None = None,
    fallback_path: Path | str = DEFAULT_SIGNAL_LEDGER,
) -> SignalWriteResult:
    """Validate and persist one learning signal.

    ``conn`` is accepted for tests and live callers that already own a DB
    transaction. ``dsn`` is opt-in. Without either, the row lands in a local
    JSONL ledger so capture can be smoke-tested without live credentials.
    """
    signal_type = signal_type.strip().lower()
    if signal_type not in VALID_SIGNAL_TYPES:
        raise LearningSignalError(f"invalid signal_type {signal_type!r}; expected one of {sorted(VALID_SIGNAL_TYPES)}")
    numeric_value = float(value)
    numeric_weight = float(weight)
    if not -1.0 <= numeric_value <= 1.0:
        raise LearningSignalError("value must be between -1.0 and 1.0")
    if numeric_weight <= 0:
        raise LearningSignalError("weight must be positive")

    row = {
        "task_id": str(task_id),
        "signal_type": signal_type,
        "prompt": str(prompt),
        "response": str(response),
        "value": numeric_value,
        "weight": numeric_weight,
        "created_at": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if conn is not None:
        _insert_signal(conn, row)
        return SignalWriteResult("db_inserted", signal_type, str(task_id), numeric_value, numeric_weight, "brain_index.learning_signals")
    if dsn:
        live_conn = _connect(dsn)
        try:
            _insert_signal(live_conn, row)
            if hasattr(live_conn, "commit"):
                live_conn.commit()
        finally:
            if hasattr(live_conn, "close"):
                live_conn.close()
        return SignalWriteResult("db_inserted", signal_type, str(task_id), numeric_value, numeric_weight, "brain_index.learning_signals")

    path = Path(fallback_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return SignalWriteResult("fallback_jsonl", signal_type, str(task_id), numeric_value, numeric_weight, str(path))


def count_signals(*, conn: Any | None = None, path: Path | str = DEFAULT_SIGNAL_LEDGER) -> int:
    if conn is not None:
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM brain_index.learning_signals")
            return int(cur.fetchone()[0])
        finally:
            close = getattr(cur, "close", None)
            if callable(close):
                close()
    ledger = Path(path)
    if not ledger.exists():
        return 0
    return sum(1 for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip())


def _insert_signal(conn: Any, row: dict[str, Any]) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO brain_index.learning_signals
              (task_id, signal_type, prompt, response, value, weight)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (row["task_id"], row["signal_type"], row["prompt"], row["response"], row["value"], row["weight"]),
        )
    finally:
        close = getattr(cur, "close", None)
        if callable(close):
            close()


def _connect(dsn: str) -> Any:
    try:
        import psycopg  # type: ignore
    except ImportError:
        try:
            import psycopg2 as psycopg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("psycopg/psycopg2 is required for live brain_index writes") from exc
    return psycopg.connect(dsn)  # type: ignore[attr-defined]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture one continuous-learning signal.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--response", required=True)
    parser.add_argument("--signal-type", required=True, choices=sorted(VALID_SIGNAL_TYPES))
    parser.add_argument("--value", required=True, type=float)
    parser.add_argument("--weight", type=float, default=1.0)
    parser.add_argument("--dsn", default=os.environ.get("BRAIN_INDEX_DSN") or os.environ.get("DATABASE_URL"))
    parser.add_argument("--fallback-path", type=Path, default=DEFAULT_SIGNAL_LEDGER)
    args = parser.parse_args(argv)

    result = collect_signal(
        args.task_id,
        args.prompt,
        args.response,
        args.signal_type,
        args.value,
        weight=args.weight,
        dsn=args.dsn,
        fallback_path=args.fallback_path,
    )
    signal_count = count_signals(path=args.fallback_path)
    print(json.dumps({**result.to_json(), "signal_count": signal_count, "ready_for_finetune": ready_for_finetune(signal_count)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
