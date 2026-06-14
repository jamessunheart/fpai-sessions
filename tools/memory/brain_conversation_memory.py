"""Conversation memory — compress chat into durable, retrievable memories.

Tier 2: distill a conversation into terse durable facts (decisions, James's
preferences/goals/state), embed them, and store as high-trust note_chunks
(source='tg-memory') so every future reply can retrieve them via the existing
vector search. This is what makes the brain remember across days, not just the
last 14 turns.
"""
import hashlib, logging
log = logging.getLogger("curator.conversation_memory")
MEMORY_SOURCE = "tg-memory"

COMPRESS_SYSTEM = (
    "You distill a conversation between James and his Sunheart Brain into durable long-term memory. "
    "Output 3-8 terse factual lines worth remembering for weeks: decisions made, James's stated "
    "goals / preferences / state, commitments, and concrete context. Only durable facts — skip "
    "pleasantries and any meta-talk about the AI's memory working or not. One fact per line, plain text."
)

async def compress_and_store(chat_id, turns):
    """turns = [(role, text), ...] oldest-first. Returns the memory text or None."""
    if not turns:
        return None
    from .llm import complete
    from .tgbot import _embed_query
    convo = "\n".join(f"{'James' if r == 'user' else 'Brain'}: {t}" for r, t in turns)
    try:
        res = await complete(COMPRESS_SYSTEM,
                             "Conversation:\n" + convo + "\n\nDurable memory facts:",
                             max_tokens=400, temperature=0.2, force_json=False)
        memory = (res.text or "").strip()
    except Exception as e:
        log.warning("compress failed: %s", e)
        return None
    if not memory:
        return None
    emb = await _embed_query(memory)
    if not emb:
        log.warning("memory embed failed (no embedding)")
        return None
    sha = hashlib.sha1(memory.encode("utf-8")).hexdigest()
    from .db import connect
    try:
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO brain_index.note_chunks "
                    "(note_row_id, chunk_idx, content, content_sha1, embedding, embedding_model, "
                    " source, sensitivity, tags, created_at) "
                    "VALUES (%s, 0, %s, %s, %s::vector, %s, %s, 'personal', ARRAY['tg-memory'], now()) "
                    "ON CONFLICT DO NOTHING",
                    (f"tgmem-{chat_id}-{sha[:12]}", memory, sha, emb, "nomic-embed-text", MEMORY_SOURCE),
                )
        log.info("stored conversation memory (%d chars) for chat %s", len(memory), chat_id)
        return memory
    except Exception as e:
        log.warning("store memory failed: %s", e)
        return None
