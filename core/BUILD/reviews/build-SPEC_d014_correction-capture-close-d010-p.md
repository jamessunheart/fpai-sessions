# AI Review — build/SPEC_d014_correction-capture-close-d010-p

**Verdict:** APPROVE · **Risk:** low

**Summary:** Advisory correction-capture loop is well-bounded, parameterized, fail-safe, and matches spec scope; no money/identity/secret/main-branch concerns.

## Findings
- No SQL injection: all DB queries use parameterized %s placeholders; dynamic WHERE built only from fixed clause strings + bound params. Supabase table name comes from env, not user input.
- Fail-safe design is correct: capture/write/read are all wrapped in try/except and best-effort, so the bot's normal answer path is never blocked if DB or Supabase is unavailable.
- Ordering is correct: capture_if_correction runs BEFORE _log_tg_message, so the 'previous bot turn' is the prior bot reply rather than James's just-sent message (verified by wiring test).
- No treasury/money, identity/memory, or secrets touched. REGISTRY status set to 'done' (not 'merged') per contract — Ember-only merge gate respected. schema.sql change is additive (CREATE TABLE IF NOT EXISTS).
- LOW: recent_corrections fallback with conversation_id=None returns corrections across all conversations; harmless on an owner-only bot but would leak cross-chat if reused multi-tenant. build_context path always passes conversation_id, so not triggered in practice.
- LOW: _NEGATION_RESTATEMENT regex is broad and may false-positive; advisory-only impact (injects an extra context line), no correctness/security risk.
- NOTE (acknowledged in handoff): spec step 1 'audit Supabase logs to confirm injection fires' was not executed (no prod creds in sandbox); pass gate is code/test-level only — needs live verification post-merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
