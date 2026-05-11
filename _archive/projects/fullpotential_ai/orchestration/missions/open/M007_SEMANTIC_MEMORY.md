# M007 – Upgrade to Semantic Vector Memory

- **Mission ID:** M007_SEMANTIC_MEMORY  
- **Title:** Upgrade to Semantic Vector Memory  
- **Priority:** P1 (Intelligence)  
- **Owner:** I PROACTIVE / Consciousness Core  
- **Status:** OPEN  

---

## Objective

Bring the proto-conscious memory stack to full **semantic recall** so that queries search by meaning instead of brittle keywords (e.g., a request for “Money” also surfaces “Treasury” or “Yield” work).

### Action Plan

1. **Integrate a lightweight Vector Store**
   - Stand up a local-friendly option such as ChromaDB, FAISS, or SQLite + pgvector.
   - Ship a `vector_store` helper inside `i-proactive` that exposes:
     - `store_embedding(id, text, metadata)`
     - `search(query_text, top_k, filters=None)`

2. **Embed every episode on write**
   - When `ContextEngine.log_activity` (Companion Claude) or `IRemember.remember_episode` persists an episode:
     - Build a canonical text block: `title + summary + tags + open-loop context`.
     - Generate an embedding via the configured provider (OpenAI, Cohere, or local model).
     - Store the vector + metadata keyed by the `episode_id`.

3. **Upgrade `/memory/recall` to semantic search**
   - Extend I PROACTIVE so `/memory/recall` accepts `query_text`, optional `project`, and `limit`, then searches the vector store for meaning-based matches.
   - Fall back to the current keyword recall path when embeddings or the vector store are offline so existing automations never regress.
   - Update internal consumers (dashboards, future agents, tools) to prefer the semantic endpoint for “what should I remember right now?”.

---

## Implementation Notes

- **Providers:** Start with whichever embedding provider is already wired into the system (OpenAI/Cohere/local Ollama embeddings). Keep a clean abstraction so the provider can be swapped.
- **Privacy / Sovereignty:** Prefer local embeddings (e.g., via Ollama) when possible to preserve sovereignty; cloud providers are acceptable as an initial bridge.
- **Backfill:** Provide an optional backfill script to:
  - Iterate existing episodes from I REMEMBER.  
  - Generate embeddings and populate the vector store so historical episodes become searchable.

---

## Definition of Done

1. Vector store module is implemented and can:
   - Persist embeddings locally.
   - Return top-k most similar items for a query.
2. New `/memory/recall` endpoint returns **semantically** relevant episodes/insights for high-level queries (e.g., “money”, “first revenue”, “treasury yield”).
3. New episodes written by `IRemember.remember_episode` are automatically embedded and indexed.
4. Fallback to keyword-based recall works gracefully if the vector store or embedding provider is offline.



