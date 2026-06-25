# hermes Mastery Card

## What it does best
Hermes is best as the system notice layer: reviewable, auditable messages about user/account state changes, expiries, reminders, and warnings that must be timely without becoming uncontrolled outreach.

## Optimal use patterns (concrete, with examples)
- Treat every notice as a state-backed event. Example: "CORA decay notice scheduled because credit batch expires on 2026-07-01."
- Separate notice drafting from live sending. Drafts can be automated; sends need the approved channel, audience, and trigger rule.
- Include the minimum useful facts: what changed, why it matters, what action is available, and the deadline.
- Deduplicate notices by event key. Example: `cora_decay:{user_id}:{credit_batch_id}:{notice_window}`.
- Log notice attempts, outcomes, and suppression reasons to the ops/customer ledger.

## Anti-patterns (what silently degrades it)
- Treating notices as marketing copy or open-ended outreach.
- Sending from vague triggers that cannot be traced to a system state change.
- Re-notifying the same person repeatedly because there is no idempotency key.
- Omitting deadline, consequence, or available action.
- Letting failed notice delivery stay invisible.

## Effort/parameter settings for this system
Use deterministic templates for compliance-sensitive notices. Keep generative drafting review-only unless a future spec grants a narrow live-send rule. Prefer exact timestamps, entity IDs, and source policy references.

## Key constraints and hard limits
Live user-facing sends are James-gated unless an approved downstream spec explicitly grants a bounded automated notice path. Hermes must not bypass Brevo/email deliverability rules, Telegram consent boundaries, or public-send review.

## How to detect it's not performing well
Users miss expiry/decay events, duplicate notices appear, message content cannot be traced to a policy/event, sends lack ledger evidence, or James has to manually reconstruct who was notified.

## Last updated + source
Seeded 2026-06-16 from d046 tool list and repo-local CORA policy references to Hermes notices.

