# AI Review — build/SPEC_d083_reply-loop-closer-telegram-cta-f

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds repo-only, fail-closed Telegram CTA follow-up runner + guarded inbound email reply webhook for probe sessions; no live deploy/send/server-209 write, spec-compliant with tests.

## Findings
- Non-blocking: pipe token check uses plain `!=` comparison (not constant-time) — negligible timing-attack surface on this localhost-behind-nginx route, but `hmac.compare_digest` would be cleaner.
- Non-blocking: inbound webhook runs `CREATE TABLE IF NOT EXISTS probe_reply_queue` DDL inside the request path (also in schema.sql) — idempotent and harmless but DDL-on-request is mild smell.
- Non-blocking: REGISTRY.json `updated_at` regressed from 2026-06-17T21:20:00Z to 12:36:01Z (backwards), cosmetic only.
- Confirmed safe: all live paths fail closed — follow-up sends gated by is_live_enabled/Brevo key + PROBE_DISABLE/OUTREACH_EMAIL_DISABLE; inbound webhook requires PROBE_PIPE_ENABLED=1 AND matching PROBE_PIPE_TOKEN; server-209 pipe script is repo artifact only, gated on explicit James authorization; branch correctly off feat/headless-build, no push/merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
