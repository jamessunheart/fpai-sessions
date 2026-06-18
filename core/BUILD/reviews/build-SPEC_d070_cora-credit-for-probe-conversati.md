# AI Review — build/SPEC_d070_cora-credit-for-probe-conversati

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Adds an idempotent CORA-credit awarder for closed probe conversations (DB writes to brain_index on server 162); credits are correctly framed as closed-loop access, not money — but the writer never commits the transaction.

## Findings
- No transaction commit: award_cora()/ensure_schema() run DDL (ALTER/CREATE TABLE) and INSERTs but never call conn.commit() or set autocommit. Unless rate_governor.connect_from_env() returns an autocommit connection, the schema migration and all credit rows silently roll back on close — the tool would appear to succeed while persisting nothing. Verify the connection mode and add an explicit commit on the own_conn path.
- When run live this mutates the brain_index schema on 162: ALTER TABLE probe_sessions ADD COLUMN tester_identifier and CREATE TABLE cora_ledger. Additive and IF NOT EXISTS (low blast radius, spec-requested), but creating a brand-new persistent ledger table goes slightly beyond the d035 'add an event' framing — confirm cora_ledger is the intended runtime ledger before wiring into fpai-probe.timer.
- ensure_schema does CREATE SCHEMA but not CREATE TABLE probe_sessions; the ALTER will error if probe_sessions is absent (low risk since probe is live, but no guard).
- _specific_gap_reported uses loose substring markers ('gap:', 'correction:', 'should say') on free text — can false-trigger the +5 bonus. Low impact (bonus credit only), but worth tightening to the structured notes flags.
- Spec's gating field message_count does not exist in schema; the awarder falls back to drop_off_message as a proxy for message count. Tested and reasonable, but the open question in HANDOFF (triggered vs. James-validated correction) should be resolved before testers see the rewards as a real promise.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
