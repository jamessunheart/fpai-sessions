# AI Review — build/SPEC_d112_hot-memory-architecture-5-domain

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** d112 adds hot-memory scanners + HOT_STATE synthesis and makes the live bot read HOT_STATE first; sound and reversible, but the bot context short-circuit silently drops per-person becoming context, a scope/regression issue.

## Findings
- build_context_system_suffix: when HOT_STATE is fresh it returns only diagnostic+hot_state and short-circuits BEFORE _render_becoming_context, so the per-person becoming-engine context (d081, keyed by conversation_id) is silently dropped from the live One Chat. Spec scope is replacing the 6 stale SYSTEM sources, not conversation-specific becoming context — these serve different purposes. This is an untested live-bot regression (no test asserts becoming is preserved). Fix: append becoming to the HOT_STATE branch instead of returning early.
- Cadence/freshness mismatch: HOT_STATE_MAX_AGE_SECONDS=30min but the synthesize timer runs OnUnitActiveSec=35min, so for ~5min each cycle the file reads as stale and the bot flips back to patchwork context — intermittent context churn. Align the freshness window to the synthesis cadence (or set max-age > timer interval).
- Mitigations present and good: HOT_MEMORY_DISABLE=1 kill switch, freshness gate, secret/private regex filtering (is_public_safe), char bounds, read-only DB SELECTs with fail-soft, branch off feat/headless-build (not main), timers are artifacts only (not installed). No money/treasury/secrets exposure found.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
