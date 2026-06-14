#!/usr/bin/env python
"""Manual / cron entrypoint for source-adapter sync.

Usage (as the streasury user, with /etc/streasury-bot/streasury.env loaded):

    cd /opt/streasury-bot
    .venv/bin/python -m scripts.sync_sources              # all enabled sources
    .venv/bin/python -m scripts.sync_sources outbounders  # just one kind

The Phase 2+ runner. Mirrors the contract of `app.sources.base.run_all` —
imports the adapter package so adapters self-register, then calls run_all
filtered to the requested kinds.
"""
from __future__ import annotations

import asyncio
import logging
import sys

# Importing the package triggers adapter self-registration via __init__.py.
import app.sources  # noqa: F401
from app.db import close_pool
from app.sources.base import ADAPTERS, list_connections, record_sync_outcome


async def main(only_kinds: set[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    log = logging.getLogger("sync_sources")

    log.info("registered adapters: %s", sorted(ADAPTERS.keys()))

    rc = 0
    try:
        connections = await list_connections()
        if only_kinds is not None:
            connections = [c for c in connections if c.kind in only_kinds]
        if not connections:
            log.warning("no enabled connections matched (kinds=%s)", only_kinds)
            return 0

        for c in connections:
            adapter = ADAPTERS.get(c.kind)
            if adapter is None:
                log.warning("no adapter registered for kind=%s (label=%s)", c.kind, c.label)
                continue
            log.info("syncing %s/%s …", c.kind, c.label)
            try:
                result = await adapter.sync(c)
            except Exception as e:
                log.exception("sync failed for %s/%s", c.kind, c.label)
                from app.sources.base import SyncResult
                result = SyncResult(error=str(e))
                rc = 1
            await record_sync_outcome(c.id, result)
            log.info(
                "  %s/%s → seen=%d inserted=%d skipped=%d error=%s",
                c.kind, c.label, result.seen, result.inserted, result.skipped, result.error,
            )
    finally:
        await close_pool()

    return rc


if __name__ == "__main__":
    kinds: set[str] | None = set(sys.argv[1:]) or None
    raise SystemExit(asyncio.run(main(kinds)))
