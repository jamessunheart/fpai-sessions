# AI Review — build/SPEC_d104_attention-engine-relevance-trigg

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds relevance-triggered attention surfacing over existing pgvector brain search plus an append-only audit table; in-scope, no scheduled checks/sends, defensive private exclusion, best-effort non-blocking logging — safe to merge.

## Findings
- Verified: brain_index.note_chunks already defines note_row_id and chunk_idx (schema.sql:10-11), so the modified _search_brain SELECT will not break the live Telegram query.
- Non-blocking: attention_surface_events logs the raw query[:1000] and surfaced content[:500] into a table with no sensitivity column; private rows are already excluded so risk is low, but consider a retention/scrubbing policy since this stores personal-tier conversational content.
- Non-blocking quality note: surfacing is purely cosine-threshold heuristic (0.72 default + 0.03 tag bonus). Given James's current complaint about the bot returning STALE state, injecting more advisory memory chunks could reinforce stale context unless chunks carry recency — monitor after merge.
- Good: kill switches (SH_ATTENTION_SURFACING_DISABLE / SH_ATTENTION_LOG_DISABLE), schema not applied live in sandbox, no push/merge/timer/sender added.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
