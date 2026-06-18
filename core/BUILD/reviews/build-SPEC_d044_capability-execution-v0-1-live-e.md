# AI Review — build/SPEC_d044_capability-execution-v0-1-live-e

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Solid consent/confirmation/kill-switch gating, but the plain-text intent interceptor hijacks normal conversation and wires live outward email into the prod 162 bot — needs tightening before merge.

## Findings
- Conversation-hijack regression: `_handle_capability_turn` runs on EVERY plain-text message before the normal brain answer, and `_detect_capability_intent` matches extremely common phrases ('what is', 'find me', 'look up', 'schedule', 'reach out to'). Routine questions like 'what is X' will now return 'I can search for that. Want me to? yes/no' instead of a brain answer — a material UX regression on James's primary live interface (@sunheartbrain_bot on 162). Make detection far more conservative or opt-in.
- Outward-facing prod action: send_email goes through the live Brevo mail stack (mail.fullpotential.com reputation). Gating is good (non-default grant + consent_log + explicit confirm + CAPABILITIES_DISABLE), but this is a real escalation into production email from the bot — confirm James has explicitly blessed live send before merge, not just spec-implied.
- Default grant exposure: `_load_capability_grants` returns {'search_web'} for ALL users (from_user or chat_id), so any user conversing with the bot can trigger SerpAPI/DuckDuckGo searches. Bound search_web to owner/known users or add rate limiting to avoid cost/abuse.
- Migration not reviewable: tools/db/migrate_add_capability_log.py (creates brain_index.capability_log + consent/connected_services columns) is referenced but truncated from the diff — must be reviewed separately for idempotency, schema, and that it doesn't alter existing tables destructively.
- PII in audit log: `_redact_params` only strips 'confirmed'; full email to/subject/body are persisted to brain_index.capability_log in plaintext. Acceptable for a personal system but should be a conscious decision; consider redacting body.
- Sender spoofing surface: send_email honors a user-supplied params['from']/['from_name']. Not currently reachable from the tgbot extractor, but the executor would forward an arbitrary From to Brevo if ever passed — pin sender to env-config only.
- Cal.com booking passes attendees from params but the tgbot extractor never collects attendees; minor, but verify no unintended self-only events vs. silent attendee omission.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
