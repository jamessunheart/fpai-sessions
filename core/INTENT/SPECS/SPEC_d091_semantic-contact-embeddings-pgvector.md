# SPEC d091 — Semantic Contact Embeddings (pgvector + nomic)

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What
Embed every contact in probe_pool using nomic-embed-text (Ollama, $0) and store in brain_index via pgvector (already installed). Enables semantic search: "find contacts most similar to Cheyenne" or "who in our network cares about regenerative cities."

## Why
pgvector is installed in brain_index. nomic-embed-text produces 768-dim embeddings at $0. note_chunks table already exists with vector column. The infrastructure is complete — just needs the wire.

## Deliverables

### `brain_index.probe_pool` — add vector column
```sql
ALTER TABLE brain_index.probe_pool ADD COLUMN IF NOT EXISTS embedding vector(768);
CREATE INDEX IF NOT EXISTS probe_pool_embedding_idx ON brain_index.probe_pool USING ivfflat (embedding vector_cosine_ops);
```

### `tools/probe/embedder.py`
- `embed_contact(probe_id)` — fetch contact profile, embed via nomic, store in probe_pool.embedding
- `find_similar(probe_id, n=10)` → list of similar contacts by cosine similarity
- `find_by_interest(query, n=10)` → semantic search across all contacts
- Runs on: new contact added, profile updated, nightly refresh

### `tools/probe/embed_all.py`
- One-time backfill: embed all existing probe_pool entries
- Incremental: embed new entries as they're added (hook into agent.py)

## Gates
- Additive only — no existing columns touched
- `EMBEDDING_ENABLED=1` env flag
- Embedding model: nomic-embed-text (already pulled)

## Proof
- All probe_pool rows have non-null embedding
- `find_by_interest("regenerative cities")` returns Josh Pasmore in top 3
- Query time < 50ms for 1000 contacts
