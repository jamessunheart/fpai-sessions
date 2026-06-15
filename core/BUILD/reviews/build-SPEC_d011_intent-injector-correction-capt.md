# AI Review — build/SPEC_d011_intent-injector-correction-capt

**Verdict:** APPROVE · **Risk:** med

**Summary:** Bounded, reversible, well-tested advisory build-context injector + capture-only correction logger; touches prod bot defensively, no money/secrets/merge violations.

## Findings
- Correct branch: built off feat/headless-build, REGISTRY marks status=done with explicit 'do NOT push or merge' note — respects no-merge contract.
- No secrets hardcoded: Supabase URL/key are env-driven; read-only GET only; absent env → repo-mirror fallback. OK.
- No treasury/money/identity surfaces touched; render text explicitly forbids treating context as approval to write/spend/deploy — reinforces guardrails rather than bypassing.
- Scope matches spec d011 exactly (part A capture_corrections.py, part B build-context injection); no scope creep observed.
- PROD TOUCH: tgbot.py runs on the brain bot — injection is wrapped in try/except, fails back to CHAT_SYSTEM_PROMPT, and is killable via SH_BUILD_CONTEXT_DISABLE=1. Defensive, but it does modify a live-bot code path; confirm deploy is gated on Ember/James.
- LATENCY: _load_supabase_context is awaited before every synthesis with a 2s timeout; if Supabase is slow/unreachable, each chat can stall up to ~2s before fail-back. Minor UX risk — consider caching or shorter timeout.
- PROMPT-INJECTION SURFACE: Supabase row fields (title/next/focus) are embedded verbatim into the system prompt; bounded by char/item limits and owner-controlled data, low risk but worth noting if that table is ever writable by non-owners.
- correction pairs default never_train=False (trainable) — intended to feed d010, but capture-only here; no training/scoring/routing performed. Acceptable.
- render_build_context char-bound logic relies on a newline existing in the truncated head; header always supplies newlines so the <=max_chars guarantee holds (test confirms).

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
