"""nerve-center-forwarder — drain ``event_outbox`` and POST to the Nerve Center.

Runs as a long-lived worker. At-least-once delivery; idempotency is the
responsibility of Nerve Center (we include ``event_id`` + ``topic`` so it can
dedupe).
"""
from __future__ import annotations

import asyncio
import json

import httpx
from sqlalchemy import text

from shared.config import settings
from shared.db import SessionLocal
from shared.logging import configure_logging, get_logger

log = get_logger("nerve-center-forwarder")

BATCH_SIZE = 100
POLL_INTERVAL = 3.0


async def _fetch_batch() -> list[tuple]:
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id, tenant_id::text, topic, payload
                      FROM event_outbox
                     WHERE NOT published
                     ORDER BY id
                     LIMIT :n
                    FOR UPDATE SKIP LOCKED
                    """
                ),
                {"n": BATCH_SIZE},
            )
        ).all()
    return list(rows)


async def _mark_published(ids: list[int]) -> None:
    if not ids:
        return
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        await session.execute(
            text("UPDATE event_outbox SET published = true WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
        await session.commit()


async def _forward(client: httpx.AsyncClient, row: tuple) -> bool:
    event_id_db, tenant_id, topic, payload = row
    body = {
        "source": "concierge",
        "topic": topic,
        "tenant_id": tenant_id,
        "payload": payload,
        "outbox_id": event_id_db,
    }
    try:
        r = await client.post(
            f"{settings.nerve_center_url}/events",
            json=body,
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=5.0,
        )
        return 200 <= r.status_code < 300
    except Exception as e:
        log.warn("nerve_center_unreachable", err=str(e))
        return False


async def main() -> None:
    configure_logging()
    log.info("worker_started", nerve_center=settings.nerve_center_url)
    async with httpx.AsyncClient() as client:
        while True:
            batch = await _fetch_batch()
            if not batch:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            published: list[int] = []
            for row in batch:
                if await _forward(client, row):
                    published.append(row[0])
            if published:
                await _mark_published(published)
                log.info("forwarded", count=len(published))
            if len(published) < len(batch):
                await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
