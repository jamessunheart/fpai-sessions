# AI Review — build/SPEC_d089_payment-triggered-agent-spawn-c

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Wires Stripe checkout.session.completed to mark user paid + init namespace + send 'Your agent is ready' Telegram; logic is parameterized and fail-closed, but couples payment settlement to Telegram delivery which can strand paid customers.

## Findings
- Money-correctness bug: activation runs BEFORE settlement and the webhook raises HTTPException(500) on skipped_reason in {missing_telegram_chat_id, telegram_send_failed}. By that point set_paid() already wrote users.paid=TRUE and init_namespace() created the row, but record.status stays PENDING. Stripe will retry forever and the payment intent never settles — internal ledger drifts permanently from Stripe (charged-but-PENDING) for any checkout lacking telegram metadata or during a transient Telegram outage. Settlement must not depend on notification delivery; settle the payment, then queue/retry the Telegram send out-of-band.
- Cross-store non-atomicity: set_paid (brain_index) and the zend-payments settlement are separate databases with no transaction. A failure between them leaves partial state; on Stripe retry the 'Your agent is ready.' message can be re-sent multiple times (no dedupe/idempotency key on the message).
- Dynamic importlib loading of curator/users.py and hermes/gateway.py by filesystem path (with sys.modules injection) is fragile across deploy layouts and depends on SUNHEART_BRAIN_CURATOR_ROOT / relative parents[3]; a path/layout drift silently degrades to RuntimeError and fails the webhook closed (compounds the settlement-stuck issue above).
- Process gate not satisfied: REGISTRY marks status=done/tests_passed=true but independent AI review never completed (claude -p hung) and the commit was blocked — merge gate normally requires a passing independent review before merge. This review is that gate; do not merge until the settlement/Telegram coupling is fixed.
- Live-schema inference for user_agents columns means a real-schema mismatch fails the webhook closed mid-payment rather than degrading gracefully — verify the live brain_index.users.paid and user_agents columns exist before any live checkout.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
