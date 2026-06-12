"""ai-qa worker — post-call rubric scoring with LLM → ratings + earnings.

Listens for ``conversation.closed`` events and scores on:
- Disclosure compliance (was AI disclosure made?)
- Intent resolution (did we achieve the caller's goal?)
- Warmth / professionalism
- Handoff cleanliness (if human-handled)
"""
from __future__ import annotations

import asyncio
import json

import asyncpg
import httpx
from openai import AsyncOpenAI
from sqlalchemy import text

from shared.config import settings
from shared.db import SessionLocal
from shared.events import Topics
from shared.logging import configure_logging, get_logger

log = get_logger("ai-qa")

RUBRIC_PROMPT = """You are a QA analyst scoring a customer-service call.
Return STRICT JSON:
{
  "disclosure_ok": bool,
  "intent_resolution": 0.0-1.0,
  "warmth": 0.0-1.0,
  "handoff_clean": 0.0-1.0,
  "overall": 0.0-1.0,
  "notes": "short reasoning"
}
Transcript:
---
{transcript}
---
"""


async def _score(transcript: str) -> dict | None:
    if not settings.openai_api_key or not transcript.strip():
        return None
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    r = await client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[{"role": "user", "content": RUBRIC_PROMPT.replace("{transcript}", transcript)}],
        response_format={"type": "json_object"},
    )
    return json.loads(r.choices[0].message.content)


async def _process(conversation_id: str) -> None:
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text(
                    """
                    SELECT c.tenant_id::text, c.agent_id::text, t.text
                      FROM conversations c
                      LEFT JOIN transcripts t ON t.conversation_id = c.id
                     WHERE c.id = CAST(:id AS uuid) LIMIT 1
                    """
                ),
                {"id": conversation_id},
            )
        ).first()
        if not row:
            return
        tenant_id, agent_id, transcript = row[0], row[1], row[2] or ""

    scores = await _score(transcript)
    if not scores:
        return

    async with httpx.AsyncClient(timeout=5.0) as client:
        if agent_id:
            await client.post(
                f"{settings.skills_mesh_url}/ratings",
                headers={
                    "X-Internal-Token": settings.internal_service_token,
                    "X-Tenant-Id": tenant_id,
                },
                json={
                    "agent_id": agent_id,
                    "conversation_id": conversation_id,
                    "source": "ai_qa",
                    "score": scores.get("overall", 0.0),
                    "rubric": scores,
                },
            )


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
                if evt.get("topic") == Topics.CONVERSATION_CLOSED:
                    cid = evt.get("payload", {}).get("conversation_id")
                    if cid:
                        await _process(cid)
            except Exception as e:
                log.error("process_error", err=str(e))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
