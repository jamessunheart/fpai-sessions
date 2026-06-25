# stripe Mastery Card

## What it does best
Stripe is best for payment intent, billing, subscription, checkout, invoice, and webhook-backed state changes where money events must be reliable, idempotent, and auditable.

## Optimal use patterns (concrete, with examples)
- Treat webhooks as the source of truth for completed payment state. Example: provision after `checkout.session.completed` or invoice payment success, not after client redirect alone.
- Verify webhook signatures against the raw request body before parsing or trusting event content.
- Use idempotency keys on create/update calls that may be retried. Example: `order:{order_id}:create_checkout_session`.
- Store Stripe event IDs and processed timestamps; ignore duplicate webhook deliveries.
- Make handlers fast and durable: validate, enqueue or persist the event, return 2xx only after the handoff is safe.
- Keep local domain state explicit: pending, paid, failed, refunded, disputed, canceled.

## Anti-patterns (what silently degrades it)
- Fulfilling from client-side success pages without webhook confirmation.
- Parsing JSON before signature verification or losing the raw request body.
- Assuming webhooks arrive once, in order, or immediately.
- Retrying create calls without idempotency keys and accidentally creating duplicate sessions/customers/subscriptions.
- Hiding failures in logs instead of exposing ledger rows and reconciliation alerts.

## Effort/parameter settings for this system
Use strict idempotency for all write calls. Keep webhook processing minimal and test duplicate/out-of-order events. Default to human review before changing live pricing, payout, tax, refund, or subscription policy.

## Key constraints and hard limits
Codex may build read-only or review-gated Stripe tooling only. Money movement, live pricing, refunds, payouts, production API keys, and account changes are James-gated.

## How to detect it's not performing well
Duplicate records appear, local paid state disagrees with Stripe, webhook retries continue, signature verification is bypassed, or failed payment/dispute states are invisible to ops.

## Last updated + source
Seeded 2026-06-16 from Stripe webhook/idempotency best-practice patterns and FPAI Reserved Class boundaries.

