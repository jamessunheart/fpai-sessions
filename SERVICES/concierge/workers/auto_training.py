"""auto-training worker — every human-edited AI draft becomes a few-shot example.

Listens on ``concierge_events`` NOTIFY channel for ``agent.draft_edited``.
"""
from __future__ import annotations

import asyncio
import json

import asyncpg
from sqlalchemy import text

from shared.config import settings
from shared.db import SessionLocal
from shared.events import Topics
from shared.logging import configure_logging, get_logger

log = get_logger("auto-training")


async def _store_example(tenant_id: str, payload: dict) -> None:
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        await session.execute(
            text(
                """
                INSERT INTO few_shot_examples
                  (tenant_id, intent, input_text, ai_draft, human_revision)
                VALUES
                  (CAST(:tid AS uuid), :intent, :inp, :draft, :rev)
                """
            ),
            {
                "tid": tenant_id,
                "intent": payload.get("intent"),
                "inp": payload.get("input_text", ""),
                "draft": payload.get("ai_draft", ""),
                "rev": payload.get("human_revision", ""),
            },
        )
        await session.commit()


async def main() -> None:
    configure_logging()
    log.info("worker_started")
    conn = await asyncpg.connect(settings.database_url_sync.replace("postgresql://", "postgres://"))
    queue: asyncio.Queue[str] = asyncio.Queue()
    await conn.add_listener(
        "concierge_events", lambda *a: queue.put_nowait(a[-1])
    )
    try:
        while True:
            raw = await queue.get()
            try:
                evt = json.loads(raw)
                if evt.get("topic") == Topics.AGENT_DRAFT_EDITED:
                    await _store_example(evt["tenant_id"], evt.get("payload", {}))
            except Exception as e:
                log.error("process_error", err=str(e))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
