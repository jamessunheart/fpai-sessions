"""Conversation memory for durable Telegram chat facts.

This compresses a bounded chat transcript into terse facts, embeds the memory,
and stores it in ``brain_index.note_chunks`` as high-trust retrievable context.
It is intentionally inert unless callers invoke ``compress_and_store``.
"""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence

log = logging.getLogger("curator.conversation_memory")

MEMORY_SOURCE = "tg-memory"

COMPRESS_SYSTEM = (
    "You distill a conversation between James and his Sunheart Brain into durable long-term memory. "
    "Output 3-8 terse factual lines worth remembering for weeks: decisions made, James's stated "
    "goals / preferences / state, commitments, and concrete context. Only durable facts -- skip "
    "pleasantries and any meta-talk about the AI's memory working or not. One fact per line, plain text."
)


async def compress_and_store(chat_id: int | str, turns: Sequence[tuple[str, str]]) -> str | None:
    """Compress chat turns into a stored memory note and return its text."""
    if not turns:
        return None

    from .llm import complete
    from .tgbot import _embed_query

    convo = "\n".join(f"{'James' if role == 'user' else 'Brain'}: {text}" for role, text in turns)
    try:
        result = await complete(
            COMPRESS_SYSTEM,
            "Conversation:\n" + convo + "\n\nDurable memory facts:",
            max_tokens=400,
            temperature=0.2,
            force_json=False,
        )
        memory = (result.text or "").strip()
    except Exception as e:
        log.warning("compress failed: %s", e)
        return None
    if not memory:
        return None

    embedding = await _embed_query(memory)
    if not embedding:
        log.warning("memory embed failed (no embedding)")
        return None

    sha = hashlib.sha1(memory.encode("utf-8")).hexdigest()
    from .db import connect

    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.note_chunks
                        (note_row_id, chunk_idx, content, content_sha1, embedding, embedding_model,
                         source, sensitivity, tags, created_at)
                    VALUES (%s, 0, %s, %s, %s::vector, %s, %s, 'personal', ARRAY['tg-memory'], now())
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        f"tgmem-{chat_id}-{sha[:12]}",
                        memory,
                        sha,
                        embedding,
                        "nomic-embed-text",
                        MEMORY_SOURCE,
                    ),
                )
        log.info("stored conversation memory (%d chars) for chat %s", len(memory), chat_id)
        return memory
    except Exception as e:
        log.warning("store memory failed: %s", e)
        return None
