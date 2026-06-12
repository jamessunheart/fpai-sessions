"""knowledge-ingest worker — crawl tenant URLs, chunk, embed, store in pgvector.

Runs as a long-lived process (``python -m knowledge_ingest``).
Polls ``knowledge_sources`` with status='pending' and processes them.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from sqlalchemy import text

from shared.config import settings
from shared.db import SessionLocal
from shared.logging import configure_logging, get_logger

log = get_logger("knowledge-ingest")
EMBED_MODEL = "text-embedding-3-small"  # 1536-dim; matches vector(1536)
POLL_INTERVAL = 10.0
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150


async def _pending_sources():
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id::text, tenant_id::text, kind, uri
                      FROM knowledge_sources
                     WHERE status = 'pending'
                     ORDER BY created_at
                     LIMIT 10
                    """
                )
            )
        ).all()
    return rows


async def _mark(session, source_id: str, status: str) -> None:
    await session.execute(
        text(
            "UPDATE knowledge_sources SET status = :s, last_crawled_at = now() "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"s": status, "id": source_id},
    )


async def _fetch_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": "FPConciergeBot/1.0"})
        r.raise_for_status()
        return r.text


def _extract(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def _chunk(s: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> Iterable[str]:
    i = 0
    while i < len(s):
        yield s[i : i + size]
        i += max(1, size - overlap)


async def _embed(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


async def _process(src_id: str, tenant_id: str, kind: str, uri: str | None) -> None:
    if kind not in ("url", "doc"):
        log.warn("skipping_unsupported_kind", kind=kind)
        return
    if not uri:
        return
    if not settings.openai_api_key:
        log.error("no_openai_key_configured")
        return

    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        await _mark(session, src_id, "crawling")
        await session.commit()

    try:
        raw = await _fetch_url(uri)
        body = _extract(raw)
        chunks = list(_chunk(body))
        if not chunks:
            raise ValueError("no content")

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        # Batch embeddings to stay under API limits
        batch_size = 64
        all_embeddings: list[list[float]] = []
        for i in range(0, len(chunks), batch_size):
            all_embeddings.extend(await _embed(client, chunks[i : i + batch_size]))

        async with SessionLocal() as session:
            await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
            await session.execute(
                text(
                    "DELETE FROM knowledge_chunks WHERE source_id = CAST(:id AS uuid)"
                ),
                {"id": src_id},
            )
            for idx, (chunk, emb) in enumerate(zip(chunks, all_embeddings)):
                await session.execute(
                    text(
                        """
                        INSERT INTO knowledge_chunks
                          (tenant_id, source_id, chunk_idx, text, embedding, tokens, metadata)
                        VALUES
                          (CAST(:tid AS uuid), CAST(:sid AS uuid), :i, :t,
                           CAST(:e AS vector), :tok, CAST(:m AS jsonb))
                        """
                    ),
                    {
                        "tid": tenant_id,
                        "sid": src_id,
                        "i": idx,
                        "t": chunk,
                        "e": _to_pg_vector(emb),
                        "tok": len(chunk.split()),
                        "m": json.dumps({"uri": uri}),
                    },
                )
            await _mark(session, src_id, "indexed")
            await session.commit()
        log.info("indexed", source_id=src_id, chunks=len(chunks))
    except Exception as e:
        log.error("ingest_failed", source_id=src_id, err=str(e))
        async with SessionLocal() as session:
            await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
            await _mark(session, src_id, "failed")
            await session.commit()


def _to_pg_vector(emb: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in emb) + "]"


async def main() -> None:
    configure_logging()
    log.info("worker_started", model=EMBED_MODEL)
    while True:
        rows = await _pending_sources()
        if not rows:
            await asyncio.sleep(POLL_INTERVAL)
            continue
        await asyncio.gather(*[_process(r[0], r[1], r[2], r[3]) for r in rows])


if __name__ == "__main__":
    asyncio.run(main())
