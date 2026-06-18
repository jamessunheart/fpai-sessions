#!/usr/bin/env python3
"""Best-effort routing decision logging for the bandwidth ledger.

The live target is ``brain_index.routing_log`` when explicitly enabled. The
default path is an append-only repo JSONL mirror so local tests and dry runs can
measure the same shape without credentials or production writes.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2]))
DEFAULT_LEDGER = REPO_ROOT / "core" / "BUILD" / "signals" / "routing_log.jsonl"
VALID_TIERS = {"T0", "T1", "T2", "T3", "T4", "T5"}
VALID_OUTCOMES = {"completed", "escalated", "failed", "no_op"}


@dataclass(frozen=True)
class RoutingDecision:
    ts: str
    task_type: str
    tier_used: str
    outcome: str
    tier_intended: str = "T1"
    tokens_loaded: int = 0
    tokens_used: int = 0
    session_id: str = ""
    source: str = "repo"
    metadata: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "task_type": self.task_type,
            "tier_used": self.tier_used,
            "tier_intended": self.tier_intended,
            "outcome": self.outcome,
            "tokens_loaded": self.tokens_loaded,
            "tokens_used": self.tokens_used,
            "session_id": self.session_id,
            "source": self.source,
            "metadata": self.metadata or {},
        }


def utc_stamp(value: dt.datetime | None = None) -> str:
    return (value or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_tier(value: str) -> str:
    tier = str(value or "").upper()
    if tier not in VALID_TIERS:
        raise ValueError(f"invalid tier {value!r}; expected one of {sorted(VALID_TIERS)}")
    return tier


def normalize_outcome(value: str) -> str:
    outcome = str(value or "").lower()
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"invalid outcome {value!r}; expected one of {sorted(VALID_OUTCOMES)}")
    return outcome


def build_decision(
    *,
    task_type: str,
    tier_used: str,
    outcome: str,
    tier_intended: str = "T1",
    tokens_loaded: int | None = None,
    tokens_used: int | None = None,
    session_id: str = "",
    source: str = "repo",
    metadata: dict[str, Any] | None = None,
    now: dt.datetime | None = None,
) -> RoutingDecision:
    if not task_type or not str(task_type).strip():
        raise ValueError("task_type is required")
    return RoutingDecision(
        ts=utc_stamp(now),
        task_type=str(task_type).strip(),
        tier_used=normalize_tier(tier_used),
        tier_intended=normalize_tier(tier_intended),
        outcome=normalize_outcome(outcome),
        tokens_loaded=max(0, int(tokens_loaded or 0)),
        tokens_used=max(0, int(tokens_used or 0)),
        session_id=str(session_id or ""),
        source=str(source or "repo"),
        metadata=metadata or {},
    )


def ledger_disabled() -> bool:
    return os.environ.get("BANDWIDTH_LEDGER_DISABLE", "").strip().lower() in {"1", "true", "yes", "on"}


def append_jsonl(decision: RoutingDecision, path: Path | str = DEFAULT_LEDGER) -> Path:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision.to_json(), sort_keys=True) + "\n")
    return ledger_path


def _db_write_enabled() -> bool:
    return os.environ.get("BANDWIDTH_LEDGER_DB_WRITE", "").strip().lower() in {"1", "true", "yes", "on"}


def _dsn() -> str:
    return os.environ.get("BANDWIDTH_LEDGER_DSN") or os.environ.get("DATABASE_URL") or ""


def write_brain_index(decision: RoutingDecision) -> bool:
    """Write to ``brain_index.routing_log`` only when explicitly enabled.

    Exceptions are swallowed by ``log_routing_decision`` so routing paths do not
    fail because measurement failed.
    """

    if not _db_write_enabled():
        return False
    dsn = _dsn()
    if not dsn:
        return False
    import psycopg2  # type: ignore[import-not-found]

    row = decision.to_json()
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO brain_index.routing_log
                    (ts, task_type, tier_used, tier_intended, outcome,
                     tokens_loaded, tokens_used, session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row["ts"],
                    row["task_type"],
                    row["tier_used"],
                    row["tier_intended"],
                    row["outcome"],
                    row["tokens_loaded"],
                    row["tokens_used"],
                    row["session_id"],
                ),
            )
    return True


def log_routing_decision(
    *,
    task_type: str,
    tier_used: str,
    outcome: str,
    tier_intended: str = "T1",
    tokens_loaded: int | None = None,
    tokens_used: int | None = None,
    session_id: str = "",
    source: str = "repo",
    metadata: dict[str, Any] | None = None,
    ledger_path: Path | str = DEFAULT_LEDGER,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Log one routing decision without blocking the caller."""

    if ledger_disabled():
        return {"logged": False, "reason": "disabled"}
    try:
        decision = build_decision(
            task_type=task_type,
            tier_used=tier_used,
            tier_intended=tier_intended,
            outcome=outcome,
            tokens_loaded=tokens_loaded,
            tokens_used=tokens_used,
            session_id=session_id,
            source=source,
            metadata=metadata,
            now=now,
        )
        path = append_jsonl(decision, ledger_path)
        db_written = write_brain_index(decision)
        return {"logged": True, "path": str(path), "db_written": db_written}
    except Exception as exc:
        return {"logged": False, "reason": f"{type(exc).__name__}: {exc}"}

