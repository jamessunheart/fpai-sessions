# AI Review — build/SPEC_d036_user-onboarding-flow-v0-1-beacon

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Well-guarded new-files build, but the migration redefines existing load-bearing brain_index.thread/user_channels tables with an assumed schema that was never verified against live.

## Findings
- Migration tools/db/migrate_add_agent_passports.py CREATEs brain_index.thread and user_channels — these are already live, load-bearing tables (thread is the d016 continuity substrate). CREATE IF NOT EXISTS silently no-ops if the live schema differs, so the code's assumed columns (user_id, surface, role, text) may not match production, causing INSERT failures at runtime. Verify against live schema and ideally don't redefine tables owned by another spec.
- The live Postgres path (PsycopgOnboardingStore) was admitted as never exercised against real credentials — load_beacon/save_passport SQL is untested; ON CONFLICT...excluded clauses and psycopg3 cursor.execute().fetchone() usage need a real-DB smoke test before merge.
- Good: production writes gated behind HERMES_DISABLE!='0' (default DisabledStore no-op), CORA award gated behind CORA_POLICY_LIVE=='1' (default skip, no promise) — money path correctly off by default.
- Good: new files only, branched off feat/headless-build not main, registered in REGISTRY.json, 6 unit tests pass, no secrets, no self-escalation. Scope matches spec.
- Minor: ONBOARDING_CORA_AWARD=25 is hard-coded in flow.py rather than read from the d035 CORA policy — risks drift from the canonical earn-rate; reconcile with CORA_POLICY before live.
- Minor: full onboarding round-trip (start_onboarding -> complete) is only covered via metadata.onboarding_answers injection; the real multi-turn Hermes handoff shape is unspecified (flagged as open question) — deterministic v0.1 heuristics need review against real transcripts.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
