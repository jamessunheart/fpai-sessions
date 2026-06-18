# AI Review — build/SPEC_d110_session-write-through-every-clau

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds an additive brain_index.session_insights table, a fail-soft writer, an uninstalled hook wrapper, an awareness verifier, and bot context injection so non-Telegram surfaces can surface recent decisions; no push/merge/deploy/live-write performed — matches spec scope and is reversible.

## Findings
- Schema DDL is duplicated in two places — index/schema.sql (CREATE TABLE session_insights) and write_session_insights.ensure_schema (brain_index.session_insights). They agree today but can drift; ensure_schema also auto-creates the table on the brain DB (server 162) at first real write. Keep the live migration + hook install as the documented manual James-hand step (the build correctly deferred both); do not let an automated settle path silently mutate the brain schema unreviewed.
- In build_context._with_recent_session_insights the dynamic-import block (spec.loader.exec_module) is only guarded against ImportError; a runtime error during module load would propagate past the function. Low risk (db.py is known-good) but the DB-query block's broad try/except already sets the fail-soft pattern — the import should match it.
- invalidate_system_prompt_cache writes a timestamp to /var/lib/sh-brain/system_prompt.invalidate; confirm a live reader actually consumes this file, otherwise weight>=8 insights set a cache-invalidation flag nothing acts on (no harm, but dead signal).
- DEFAULT_DB_URL embeds a 'changeme' placeholder credential as fallback; harmless as a local default but ensure prod always supplies BRAIN_INDEX_DB_URL/DATABASE_URL so the writer never silently targets the wrong DB.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
