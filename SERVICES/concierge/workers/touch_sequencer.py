"""touch-sequencer — poll ``campaign_contacts`` for due steps and POST /touch.

Runs centrally (as a superuser context) to find due work across all tenants,
then issues the actual dispatch via the outbound-engine so compliance-gate +
rate-limit logic live in one place.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import text

from shared.config import settings
from shared.db import SessionLocal
from shared.logging import configure_logging, get_logger

log = get_logger("touch-sequencer")

POLL_INTERVAL_SEC = 10
BATCH_SIZE = 50


async def _due_contacts() -> list[tuple[str, str]]:
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id::text, tenant_id::text
                      FROM campaign_contacts
                     WHERE status = 'pending'
                       AND (next_run_at IS NULL OR next_run_at <= now())
                     ORDER BY next_run_at NULLS FIRST
                     LIMIT :n
                    """
                ),
                {"n": BATCH_SIZE},
            )
        ).all()
    return [(r[0], r[1]) for r in rows]


async def _send(client: httpx.AsyncClient, cc_id: str, tenant_id: str) -> None:
    try:
        r = await client.post(
            f"{settings.outbound_engine_url}/touch",
            headers={
                "X-Internal-Token": settings.internal_service_token,
                "X-Tenant-Id": tenant_id,
            },
            json={"campaign_contact_id": cc_id},
            timeout=10.0,
        )
        r.raise_for_status()
    except Exception as e:
        log.warn("touch_failed", cc_id=cc_id, err=str(e))
        # Back off on failure: move next_run_at ahead 10 minutes.
        async with SessionLocal() as session:
            await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
            await session.execute(
                text(
                    """
                    UPDATE campaign_contacts
                       SET next_run_at = now() + interval '10 minutes'
                     WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": cc_id},
            )
            await session.commit()


async def main() -> None:
    configure_logging()
    log.info("worker_started", outbound=settings.outbound_engine_url)
    async with httpx.AsyncClient() as client:
        while True:
            due = await _due_contacts()
            if not due:
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue
            await asyncio.gather(*[_send(client, cc_id, tid) for cc_id, tid in due])
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
