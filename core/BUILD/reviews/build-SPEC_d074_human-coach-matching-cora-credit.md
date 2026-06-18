# AI Review — build/SPEC_d074_human-coach-matching-cora-credit

**Verdict:** APPROVE · **Risk:** low

**Summary:** d074 adds an offline, fixture-only human-coach matching + CORA credit scaffold (no live DB/money/outreach/deploy); branched off feat/headless-build, registered, tests pass — safe.

## Findings
- No live mutations: credit_ledger only computes fiat-equivalent values, never moves money; fiat conversion explicitly gated behind 20 active coaches and documented as a James Reserved Class action. Compliant with treasury guardrails.
- Branch is build/SPEC_d074 off feat/headless-build (not main); REGISTRY.json status set to done by codex, merged left for Ember; no push/merge in diff. Correct.
- Minor (non-blocking): extract_specialty_tags() can invoke `claude -p` via subprocess as a fallback. In the identify_potential_coach flow it's unreachable (heuristic tags are required first), and args are passed as a list (no shell injection), but the public fn could fire the subprocess if called directly — confirm it stays subscription-CLI ($0) and is never wired to a live loop without a cost gate.
- Idempotency verified: award_session_credits short-circuits when coach_credits_awarded is already set; test covers double-award. Good.
- Scope matches spec exactly (identifier/matcher/session_tracker/credit_ledger/COACH_ECONOMY.md/tests); new files only, no edits to existing prod/identity/memory code.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
