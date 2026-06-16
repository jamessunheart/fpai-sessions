# SPEC_d043_subscription-billing-v0-1-stripe Result

- Status: done / awaiting James review + merge review
- Branch: `build/SPEC_d043_subscription-billing-v0-1-stripe`
- Cost: ~$0 marginal · GPT Pro flat-rate · source: Codex desktop

## Summary

Added Subscription Billing v0.1 for the Sunheart Brain path:

- `curator.billing.stripe_handler` creates Stripe Checkout sessions, verifies
  webhook signatures before DB writes, syncs subscription tier/status to
  `brain_index.user_agents`, appends Stripe event rows to
  `brain_index.ops_ledger`, creates Customer Portal URLs, and exposes tier gate
  helpers with `STRIPE_DISABLE=1` treating users as Basic.
- `POST /stripe/webhook` is wired into the brain-index FastAPI app.
- Telegram bot commands `/upgrade`, `/billing`, and `/tier` are wired into the
  existing owner bot router, and the plain chat path enforces the daily
  message cap before search/answer work.
- `docs/billing/PRICING.md` records draft Free/Basic/Pro pricing and review
  gates before live Stripe Products/Prices are created.
- Independent review found duplicate-subscription, cancellation-grace,
  notification-recipient, runtime-gate, and weak-test issues. The duplicate
  subscription path now routes existing subscribers to the Stripe Portal,
  cancellation grace preserves the current paid tier while grace is active,
  Telegram billing notifications can target the paying chat id, the daily
  message cap is wired into chat, and the upgrade reply is directly tested.
  A final re-review caught grace expiry still keeping paid access; that blocker
  was fixed and the reviewer confirmed it resolved.

## Tests

- `python3 -B -m unittest SERVICES/sunheart-brain/curator/billing/test_stripe_handler.py` (11 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/billing/stripe_handler.py SERVICES/sunheart-brain/curator/billing/test_stripe_handler.py SERVICES/sunheart-brain/index/app.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/telegram.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check -- SERVICES/sunheart-brain/curator/billing SERVICES/sunheart-brain/index/app.py SERVICES/sunheart-brain/index/schema.sql SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/telegram.py SERVICES/sunheart-brain/index/requirements.txt SERVICES/sunheart-brain/curator/requirements.txt docs/billing/PRICING.md core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d043_subscription-billing-v0-1-stripe.md core/BUILD/results/SPEC_d043_subscription-billing-v0-1-stripe.result.md docs/codex/HANDOFF.md`
- `python3 -B -m unittest SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `python3 -B SERVICES/sunheart-brain/curator/test_build_context.py`
- `python3 -B SERVICES/sunheart-brain/curator/test_corrections.py`

## Risks

- Live Stripe calls were not exercised in this sandbox; tests use fake Stripe and
  fake Postgres.
- Stripe Products/Prices must be created manually after James approves
  `docs/billing/PRICING.md`.
- Runtime env must provide `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRICE_BASIC_ID`, and `STRIPE_PRICE_PRO_ID` before live checkout.
- The webhook endpoint is code-wired only; server deployment/restart and Stripe
  dashboard webhook registration remain Ember/ops steps.
- Capability gates are available as helper functions, but only the Telegram
  daily message limit is wired in this branch because no email/calendar
  execution path was present in the touched bot flow.

## Rollback

Revert the changed files; remove the d043 row from `core/BUILD/REGISTRY.json`.
If a live DB has already migrated, leave `brain_index.user_agents` and
`brain_index.ops_ledger` in place unless James explicitly approves table
deletion.

## Intent

- Intent solved: the product now has a reviewable, test-covered Stripe
  subscription layer that can turn proven value into Free/Basic/Pro access
  without touching card data.
- Downstream intent unlocked: James can review pricing, seed Stripe Products,
  and run a live checkout/webhook proof before turning revenue gates on.
- Next move: Ember/ops reviews diff, installs dependencies/env on the brain host,
  registers the Stripe webhook URL, and runs one live test purchase in Stripe
  test mode after James approves pricing.
