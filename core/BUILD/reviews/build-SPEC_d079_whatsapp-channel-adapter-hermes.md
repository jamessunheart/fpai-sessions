# AI Review — build/SPEC_d079_whatsapp-channel-adapter-hermes

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Guarded WhatsApp Cloud API adapter, correctly branched off feat/headless-build, sends gated behind WHATSAPP_LIVE+DRY_RUN with fail-closed signature checks — but a column/value misalignment in the probe_sessions INSERT writes a stray integer into a text column and would likely break inbound routing on the live DB.

## Findings
- BUG (probe_sessions INSERT, whatsapp_adapter.py record_probe_session_from_inbound): value/column misalignment. Columns are (...engaged, drop_off_message, completed_spark, completed_onboarding, quality_score, corrections_triggered, last_message, notes) with `engaged`=true literal, yet the values tuple passes (probe_id, 'warm', current, current, 1, message.text[:1000], notes). The stray `1` lands in `drop_off_message`, not `engaged`. On the real DB this likely errors (integer into a text column) or silently corrupts drop_off_message. Tests pass only because the FakeCursor indexes params positionally and never validates schema. Fix the value alignment before this runs against the live probe_sessions table.
- RISK (migrations/add_contact_pool_table.sql): the probe_pool CHECK is dropped and re-added with an explicit platform allow-list. Postgres validates a re-added CHECK against existing rows by default; if any current probe_pool row has a platform not in the new list, the ALTER fails. Verify the new list is a superset of all platforms already present (or add NOT VALID). Not applied live yet, so blast radius is deferred.
- UNTESTED LIVE PATH: all DB inserts (contact_pool, probe_pool, probe_sessions) are only exercised against an in-memory FakeCursor; real schema column names/types are unverified. The migration was not applied and the FastAPI receiver was not mounted, so the DB round-trip has no real proof — fine for a dry-run merge but the probe_sessions bug above must be fixed before any live receive proof.
- NOTE (not blocking, no diff change needed): a live Brevo API key was pasted in the conversation thread (xkeysib-...); it is not in this diff, but it is now exposed in chat history and should be rotated independently of this build.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
