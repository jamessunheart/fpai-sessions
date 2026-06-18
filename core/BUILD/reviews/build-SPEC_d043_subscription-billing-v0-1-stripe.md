# AI Review — build/SPEC_d043_subscription-billing-v0-1-stripe

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Solid, test-covered Stripe v0.1 on a build branch, but the owner-bot message gate and a schema-qualification mismatch are real footguns worth fixing before merge.

## Findings
- OWNER LOCKOUT RISK: _billing_message_gate runs on the plain-chat path of the single-owner @sunheartbrain_bot. With no user_agents row, get_user_tier returns FREE (10 msgs/day). Once deployed without STRIPE_DISABLE=1 or an explicit basic/pro row for James, the owner gets cut off at 10 messages/day — a live regression on James's own bot.
- SCHEMA MISMATCH: schema.sql creates tables UNQUALIFIED (CREATE TABLE user_agents / ops_ledger), but stripe_handler.py queries them QUALIFIED as brain_index.user_agents / brain_index.ops_ledger. Works only if migrations run with search_path=brain_index; otherwise webhook writes hit a missing relation. The qualification should be explicit and consistent.
- BLOCKING I/O IN ASYNC ROUTE: app.py /stripe/webhook (async) calls the synchronous handle_webhook directly — synchronous psycopg.connect + DB writes block the FastAPI event loop. Should be wrapped in asyncio.to_thread like the tgbot commands are.
- NOTIFY RECIPIENT ASSUMPTION: _notify_subscription/_notify_payment_failed send to chat_id=user_id, assuming brain user_id == Telegram chat_id. True for the owner today but unsafe once multi-user; a wrong/empty chat_id silently no-ops or misroutes.
- asyncio.run() inside the webhook will raise RuntimeError under the running FastAPI loop and fall into the except branch every time; the create_task fallback depends on tg being importable and is best-effort only — notifications are effectively unreliable from the webhook path.
- WEBHOOK IDEMPOTENCY: no Stripe event-id dedup table. Stripe retries deliver duplicates; CORA award has a heuristic guard (status+sub+tier) but it is weak — a re-delivered checkout.session.completed after any status drift could double-award CORA. Low blast radius (internal credit) but worth a hardened idempotency key.
- STRIPE_DISABLE=1 makes effective_tier return BASIC for ALL users (documented kill switch) — acceptable for testing, but confirm it is never set on a revenue-live host or it silently grants paid capabilities free.
- Endpoint is code-wired into the brain-index app (server 162) but per result is deploy-gated and on branch off feat/headless-build, not main — no main-branch or live-treasury exposure in the diff itself. Card data correctly kept at the Stripe PCI boundary; _log_event strips card-ish keys. Tests use fakes, so no live Stripe/Postgres path was exercised.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
