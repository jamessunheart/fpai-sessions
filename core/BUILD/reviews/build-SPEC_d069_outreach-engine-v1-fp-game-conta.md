# AI Review — build/SPEC_d069_outreach-engine-v1-fp-game-conta

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds FP Champions puller + Brevo email adapter + IMAP reply parser into the d054 probe loop; dry-run-first, multi-gated, branched off feat/headless-build (not main), no live sends/secrets/prod deploy by default — safe to merge with minor follow-ups.

## Findings
- Hard boundaries intact: live email requires OUTREACH_LIVE=1 AND DRY_RUN!=1 AND BREVO_API_KEY, plus PROBE_DISABLE/OUTREACH_EMAIL_DISABLE kill switches; default path is double-guarded dry-run. No main, no secrets committed, no self-escalation.
- Minor bug — repeated expiry re-marking: outreach_sessions selects engaged=false rows within a 7-day window, so an already-expired (>72h, no-reply) session is re-processed every run, re-marking engaged=false and appending another 'no_reply_72h' line to notes (notes/metric pollution, up to ~7 duplicates). Harmless functionally (no sends triggered) but should de-dupe via a status guard.
- Mild scope addition: spec asked only for 'source TEXT' column, build also adds a 'metadata' column (name/field_score/last_active/affiliate_count). Justified to preserve [first_name], handled old-schema-safe, but slightly beyond the written spec.
- PII/operational note (not a code defect): with --pull-fp-champions added to fpai-probe.service, the daily timer auto-pulls real champion emails from fullpotential.com into brain_index.probe_pool. No outreach occurs without explicit OUTREACH_LIVE=1, but real contacts accumulate in the DB on a timer if the service is installed. Sends originate as james@fullpotential.com per spec.
- Human gating preserved correctly: result notes require Ember/James to apply tools/probe/schema.sql to the live DB, set Brevo/IMAP env, run disabled/dry-run proofs, then bless a tiny OUTREACH_LIVE=1 batch — the live activation step is not automated by this build.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
