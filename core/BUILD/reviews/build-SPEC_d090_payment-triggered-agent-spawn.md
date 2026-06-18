# AI Review — build/SPEC_d090_payment-triggered-agent-spawn

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Gated, off-by-default payment→namespace spawn scaffold (no money movement, branched off feat/headless-build, not pushed/merged/deployed) — safe in shape, but has a latent DB-correctness bug and an unverified live-DB path that must be fixed before activation.

## Findings
- write_spawn/ensure_tables never call conn.commit(): if connect_from_env() does not return an autocommit connection, the CREATE TABLE and both INSERTs are rolled back on conn.close() — the feature would silently persist nothing on live activation. Verify autocommit or add an explicit commit before declaring 'done'.
- HMAC verification (signature_valid) takes the timestamp from the signature itself and never checks freshness — no replay-window enforcement. Replay risk is bounded by event_id uniqueness/idempotency, but a stale captured request stays valid forever; add a max-age check before activation.
- On activation this connects to and writes new tables into the brain_index DB on the live 162 brain (memory SSOT). Additive and gated, but per-user runtime isolation/grants are not actually enforced here (only deterministic IDs + UNIQUE constraints) — must be validated in the activation spec before multi-user autonomy depends on it, as the result doc itself notes.
- Spec requires an independent-AI-reviewed branch but the in-sandbox claude -p review failed (ConnectionRefused) — that gate is unmet by the build itself; this review now satisfies it, but record it explicitly rather than treating the build's self-reported review as done.
- Paid-detection has permissive escape hatches: top-level payload.get('paid') overrides payment_status for checkout/invoice/payment_intent, and 'payment.succeeded' defaults paid=True. Acceptable only because the HMAC-signed webhook is the sole trusted source — confirm the live webhook never forwards attacker-controllable bodies before mounting /payments/agent-spawn.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
