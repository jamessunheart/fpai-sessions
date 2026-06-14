"""app/sources/base.py — adapter base class + SourceConnection model.

Every Phase 2+ adapter inherits Adapter and gets free idempotency, error
recording, and last_sync timestamping.
"""
from __future__ import annotations

import abc
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..db import connect

log = logging.getLogger("streasury.sources")


@dataclass
class SourceConnection:
    id: int
    tenant_id: int
    kind: str
    label: str
    secret: str
    config: dict[str, Any]


@dataclass
class SyncResult:
    seen: int = 0
    inserted: int = 0
    skipped: int = 0
    error: str | None = None

    def merge(self, other: "SyncResult") -> "SyncResult":
        return SyncResult(
            seen=self.seen + other.seen,
            inserted=self.inserted + other.inserted,
            skipped=self.skipped + other.skipped,
            error=self.error or other.error,
        )


async def list_connections(*, kind: str | None = None, tenant_id: int | None = None) -> list[SourceConnection]:
    sql = (
        "SELECT id, tenant_id, kind, label, secret, config "
        "FROM streasury.source_connection WHERE enabled = TRUE"
    )
    args: list[Any] = []
    if kind:
        sql += " AND kind = %s"
        args.append(kind)
    if tenant_id is not None:
        sql += " AND tenant_id = %s"
        args.append(tenant_id)
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(args))
            rows = await cur.fetchall()
    return [
        SourceConnection(
            id=int(i), tenant_id=int(t), kind=k, label=lbl, secret=s,
            config=cfg if isinstance(cfg, dict) else json.loads(cfg or "{}"),
        )
        for (i, t, k, lbl, s, cfg) in rows
    ]


async def record_sync_outcome(connection_id: int, result: SyncResult) -> None:
    async with connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE streasury.source_connection "
                "SET last_sync_at = %s, last_sync_ok = %s, last_sync_error = %s "
                "WHERE id = %s",
                (datetime.now(timezone.utc), result.error is None, result.error, connection_id),
            )


class Adapter(abc.ABC):
    """Base class. Subclass once per source kind.

    Implementers fill in `sync(self, conn)`. The runner (a cron / on-demand
    /sync command) handles loading connections and recording results.
    """

    kind: str

    @abc.abstractmethod
    async def sync(self, conn: SourceConnection) -> SyncResult:
        ...


# Registry — adapters self-register here when imported.
ADAPTERS: dict[str, Adapter] = {}


def register(adapter: Adapter) -> Adapter:
    ADAPTERS[adapter.kind] = adapter
    return adapter


async def run_all(*, tenant_id: int | None = None) -> dict[str, SyncResult]:
    """Run every enabled connection. Returns {label: SyncResult}.
    Used by the daily cron and on-demand `/sync` command (Phase 2)."""
    out: dict[str, SyncResult] = {}
    for c in await list_connections(tenant_id=tenant_id):
        adapter = ADAPTERS.get(c.kind)
        if adapter is None:
            log.warning("no adapter registered for kind=%s (label=%s)", c.kind, c.label)
            out[c.label] = SyncResult(error=f"no adapter for {c.kind}")
            continue
        try:
            result = await adapter.sync(c)
        except Exception as e:
            log.exception("sync failed for %s/%s: %s", c.kind, c.label, e)
            result = SyncResult(error=str(e))
        await record_sync_outcome(c.id, result)
        out[c.label] = result
    return out
