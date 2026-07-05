"""Regression guard (P8) for the is_canary-class drift, 2026-07-05.

The build_state reporting selector referenced `is_canary`, a column never migrated
into the live brain_index.decisions table → every honest-count caller crashed against
live and fell back to loose numbers (this session's "14 pending" was really 2). Fix:
958b6f17. This test makes the class recur LOUDLY: if any column the reporting selector
references stops existing in the live schema, the selector raises and this test fails —
instead of the failure being swallowed into a dishonest fallback count (P3 + P18).

Skips cleanly when the live DB is unreachable (laptop / CI without the brain), so it
never blocks non-server runs; it only asserts against the live schema when it can.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.build_loop.build_state import PENDING_DECISION_WHERE_SQL

DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:50dc339828327a7a042dca45957a5bab6dc6b4eda3857524ccd014d9acc23a52@127.0.0.1:25432/postgres",
)


def _live_conn():
    try:
        import psycopg
    except ImportError:
        return None
    try:
        return psycopg.connect(DB_URL, connect_timeout=3)
    except Exception:
        return None


def test_reporting_selector_runs_against_live_schema():
    """The reporting selector must reference only columns that exist in live.

    A missing column (the is_canary class) makes this raise → fail loud, not fall
    back to a looser count. Skips if the live brain is unreachable.
    """
    conn = _live_conn()
    if conn is None:
        import pytest  # type: ignore

        pytest.skip("live brain_index unreachable — schema check skipped (non-server run)")
    try:
        with conn.cursor() as cur:
            # If any referenced column is absent, psycopg raises UndefinedColumn here.
            cur.execute(
                "SELECT id FROM brain_index.decisions "
                + PENDING_DECISION_WHERE_SQL
                + " LIMIT 1"
            )
            cur.fetchall()
    finally:
        conn.close()


if __name__ == "__main__":
    # Runnable standalone as a smoke check too (no pytest required on the server).
    conn = _live_conn()
    if conn is None:
        print("SKIP — live brain_index unreachable")
        raise SystemExit(0)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM brain_index.decisions " + PENDING_DECISION_WHERE_SQL + " LIMIT 1"
            )
            cur.fetchall()
        print("OK — reporting selector runs against live schema (no missing-column drift)")
    finally:
        conn.close()
