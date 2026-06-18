# AI Review — build/SPEC_d022_continuous-learning-controller

**Verdict:** APPROVE · **Risk:** med

**Summary:** Well-scoped d022 preference-seed exporter; new files only, fails closed on d021 gate, $0, reversible, cron not installed.

## Findings
- Branch correctly off feat/headless-build (not main); no push/merge; no secrets; no identity/memory writes; no self-grant. Within guardrails.
- SQL is safe: column names resolved from a hardcoded allowlist and quoted via q() (escapes double-quotes); values/IN-clause use %s parameter placeholders. No injection vector.
- Production DB write present: UPDATE brain_index.corrections SET preference_pair_exported=NOW() on server 162. It is watermark-only (no content mutation), gated on the d021 column existing (fails closed via detect_columns), and NOT auto-installed — cron/script are reviewed artifacts requiring manual Ember install. Acceptable but flag: this build's code does mutate prod data when run.
- Idempotency gap: export() writes JSONL (append) BEFORE mark_exported/commit. A crash after write_pairs but before commit leaves rows in the JSONL that are still unstamped in the DB → next run re-exports them = duplicate JSONL lines. Low harm (seed data, dedup downstream) but worth a stamp-then-write or dedup guard.
- count_unexported_older_than_24h returns 0 when no captured_at column exists, so the 24h proof condition is trivially satisfied in that schema — proof is weaker than the spec implies. Minor.
- Spec file was overwritten (original 3-file controller spec → narrower preference-seed spec) via auto-generation from the answered decision; build matches the new spec and is narrower, not scope creep.
- No live verification done in sandbox (no 162 SSH, no prod DB run, d021 liveness unconfirmed) — documented honestly in result/HANDOFF. Merge should be gated on James confirming d021's preference_pair_exported column is live before any install.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
