"""app/sources/actual.py — Actual Budget pull adapter.

PHASE 2 STUB. The real implementation lives in PHASE2_ACTUAL.md and lands
once Actual is running on the Brain server.

Plan:
    1. Connect to Actual server (port 5006) using the API token stored as
       conn.secret.
    2. Call /sync to pull latest from upstream (SimpleFIN/GoCardless).
    3. List all transactions added since conn.config["since"] (default: last
       sync timestamp - 7 days for safety).
    4. For each, call ledger.insert_txn with:
           source = "actual"
           source_ref = transaction.id (Actual's UUID, stable across syncs)
           account_slug = the Actual account's name, slugified
           category = mapped from Actual category → our category dictionary
    5. Update conn.config["since"] = now.

The unique index on (tenant_id, source, source_ref) makes this idempotent.

External dep: a small Node helper (`actual-cli.js`) that wraps the
@actual-app/api npm library and exposes simple JSON commands. Node is the
sanctioned client; there's no Python SDK as of 2026-04.
"""
from __future__ import annotations

from .base import Adapter, SourceConnection, SyncResult, register


class ActualAdapter(Adapter):
    kind = "actual"

    async def sync(self, conn: SourceConnection) -> SyncResult:  # pragma: no cover (stub)
        return SyncResult(
            seen=0, inserted=0, skipped=0,
            error="actual adapter not yet implemented (Phase 2)",
        )


register(ActualAdapter())
