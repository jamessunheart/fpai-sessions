"""Token-accurate metering → budget_ledger (sync-safe for worker threads).

Every Anthropic Messages API response carries ``usage.input_tokens`` and
``usage.output_tokens``. We persist those + USD from ``budget.estimate_cost``
(same price table as pre-flight gates) so internal totals can be reconciled
against Anthropic Console exports (same list prices; org credits/promos may
still cause small drift — see ``reconciliation`` in cost intelligence).
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.engine.url import make_url

from .budget import COST_ORIGIN, estimate_cost

logger = logging.getLogger("fp_index.metering")

METERING_VERSION = "1.0.0"


def resolve_sqlite_path() -> str:
    raw = __import__("os").getenv("FP_INDEX_DB", "sqlite+aiosqlite:///./fp_index.db")
    url = make_url(raw)
    if not url.drivername.startswith("sqlite"):
        raise ValueError(f"METERING: unsupported DB driver {url.drivername}")
    db = url.database
    if not db:
        raise ValueError("METERING: sqlite URL has no database path")
    return db


def _usage_tokens(resp: Any) -> tuple[int, int]:
    u = getattr(resp, "usage", None)
    if u is None:
        return 0, 0
    tin = int(getattr(u, "input_tokens", None) or 0)
    tout = int(getattr(u, "output_tokens", None) or 0)
    return tin, tout


def _model_from_response(resp: Any, fallback: str) -> str:
    return (getattr(resp, "model", None) or fallback or "").strip()


def append_ledger_row_sync(
    action_type: str,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    description: str,
    reversible: bool = True,
    content_id: Optional[str] = None,
) -> float:
    """Insert one ledger row using sync sqlite (safe from asyncio.to_thread workers)."""
    cost = estimate_cost(provider, model, tokens_in, tokens_out)
    ts = datetime.now(timezone.utc)
    path = resolve_sqlite_path()
    desc = (description or "")[:500]
    cid = content_id[:64] if content_id else None
    rev = 1 if reversible else 0
    try:
        origin = (COST_ORIGIN or "primary")[:64]
        with sqlite3.connect(path, timeout=10) as conn:
            conn.execute(
                """INSERT INTO budget_ledger
                (action_type, provider, model, tokens_in, tokens_out,
                 estimated_cost_usd, description, reversible, content_id, timestamp, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    action_type[:50],
                    provider[:30],
                    (model or "")[:80],
                    int(tokens_in),
                    int(tokens_out),
                    float(cost),
                    desc,
                    rev,
                    cid,
                    ts.isoformat(),
                    origin,
                ),
            )
    except Exception as e:
        logger.warning(f"[METERING] ledger insert failed: {e}")
        return 0.0
    logger.info(
        f"[METERING] {action_type} {provider}/{model} in={tokens_in} out={tokens_out} ~${cost:.5f}"
    )
    return cost


def meter_anthropic_message_response(
    resp: Any,
    action_type: str,
    description: str,
    model_fallback: str = "",
) -> float:
    """Record one Anthropic ``messages.create`` response to ``budget_ledger``."""
    model = _model_from_response(resp, model_fallback)
    tin, tout = _usage_tokens(resp)
    return append_ledger_row_sync(
        action_type=action_type,
        provider="anthropic",
        model=model,
        tokens_in=tin,
        tokens_out=tout,
        description=description,
        reversible=True,
        content_id=None,
    )
