# AI Review — build/SPEC_d034_hermes-channel-gateway-v0-1-plug

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Additive, kill-switched, owner-auth gateway is sound, but it writes caller-controlled identity into the memory/continuity substrate with a hardcoded role and no validation.

## Findings
- IDENTITY/MEMORY: PostgresMessageLogger.log_inbound hardcodes role='james' for every channel/user into brain_index.thread (the live cross-surface continuity substrate). This is the door explicitly being built for multi-user (web/SMS/WhatsApp), so any non-James inbound message will be written into the live thread as James — polluting continuity and the state loader. Role should derive from the resolved user, not be hardcoded.
- IDENTITY SPOOF: web_adapter takes channel_user_id/user_id straight from the request body and PostgresUserChannelStore uses message.user_id as the universal user_id. A caller can assert an arbitrary universal user_id and link/hijack identity rows. Mitigated today only because /hermes/web/message requires personal scope (owner-only), but the identity map accepts unvalidated input by design.
- PERMISSIONS OVERWRITE: ON CONFLICT DO UPDATE sets permissions = EXCLUDED.permissions, so each inbound message can silently flip stored {memory, marketing, human_followup} from the request payload (normalize_permissions only bounds keys, not authority). A channel message should not be able to rewrite a user's stored consent/permissions.
- DB DRIFT/REDUNDANCY: the table is defined twice (index/schema.sql UNIQUE(channel,channel_user_id) + migrate_add_user_channels.py which adds a second named unique index user_channels_channel_identity_uidx on the same columns) — redundant duplicate index and two SSOTs that can drift.
- COST/LLM PATH: default_pipeline routes every web message through tgbot._search_brain + _synthesize_answer (embedding + LLM). No rate limit on the endpoint beyond auth; under the $20/day cap this is a new metered/LLM surface that was not load- or cost-tested (result file confirms no live validation).
- VERIFICATION GAP: builder ran unit tests only; no live DB migration, no live endpoint request, no app import smoke (psycopg missing in sandbox), and the independent claude -p review hung and produced nothing — so no second-AI sign-off exists. Acceptable for a stub but combined with the above, validate on host before merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
