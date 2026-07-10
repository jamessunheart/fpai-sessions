# The Event-Sourced Process Principle

_Canonical design principle · James + Ember, 2026-07-10 · surfaced while designing the email architecture, generalized to the whole Conversation OS._

## The principle

> **Every operational process should be designed as an event-sourced system that naturally evolves into a product.**

Not "build a product." Design the *process itself* so that doing it produces an immutable Event stream, and running it by hand writes the specification for its own automation. The process and the product are the same thing at different rungs of maturity.

## Two halves

**1. Event-sourced from day one.** Every process emits provider-agnostic, immutable, versioned, replayable Events. All derived state (dashboards, rooms, digests, CRM records, Brain entries) is a *projection* rebuilt from the stream — never the source of truth. The channel (email, WhatsApp, a meeting) is just a producer; the Event store is canonical. (Full properties: `core/INTENT/EMAIL_ARCHITECTURE_2026-07.md` §5a.)

**2. Naturally evolves into a product.** Every manual step is future product functionality. Running the manual process is requirements-gathering for its automated replacement. The playbook IS the roadmap.

## The evolution loop

```
Manual → Playbook → Specification → Automation → Platform → Intelligence
   ▲                                                              │
   └──────────────── each capability enables new manual frontiers ┘
```

- **Manual** — do it by hand once.
- **Playbook** — write the repeatable steps.
- **Specification** — a step that repeats becomes a `SPEC_*`.
- **Automation** — the spec is built; the step runs itself.
- **Platform** — the automation generalizes across domains / tenants / orgs.
- **Intelligence** — accumulated runs teach the system to do it better than any manual operator.

**The discipline:** never let a manual process stay merely *done*. Ask which rung it's on and push it up one.

## Where it applies (the Conversation OS surface)

Every one of these is a process that should be event-sourced and product-bound from the start:

| Domain | The Events | The product it becomes |
|--------|-----------|------------------------|
| **Email** | `email.received` / `.sent` | Router · deliverability dashboard · onboarding wizard |
| **WhatsApp / Telegram** | `message.received` | unified inbox · intent routing |
| **Meetings** | `meeting.held` / `.decided` | decision log · action-item automation |
| **Recruiting** | `candidate.applied` / `.advanced` | pipeline · scoring · offer automation |
| **Treasury** | `position.opened` / `transfer.made` | live treasury dashboard · rebalance autopilot |
| **CRM** | `contact.touched` / `deal.moved` | relationship graph · next-best-action |
| **Customer Support** | `ticket.opened` / `.resolved` | triage · auto-response · knowledge base |
| **Camp Zen** | `villager.arrived` / `session.held` | village OS · soul-time ledger |
| **Growth** | `lead.captured` / `.converted` | funnel · kill/breed allocator |

Same shape everywhere: a channel produces Events → the Router classifies and routes → projections serve humans → manual steps graduate into automated capabilities.

## Why this is foundational

This is **Recursion** (the third R of `FOUNDATION.md`) expressed as a repeatable method — the system improving how it does its own work. It's the **Sunheart Rule** applied to process (route every step to the lowest tier: human → AI). And it's how the Conversation OS actually grows: not by a separate "build the product" phase, but by every operation performed today becoming tomorrow's product feature.

Design any new process this way from the first manual run, and it is already on the ladder to becoming platform intelligence.

## Related

- `core/INTENT/EMAIL_ARCHITECTURE_2026-07.md` — the first process to walk the full ladder (reference implementation)
- `core/STATE/FOUNDATION.md` — the Three Rs (this is Recursion)
- `docs/codex/LANTERN_MIRROR_LEDGER_PRINCIPLE.md` — sibling design principle
- memory: `feedback_sunheart_rule.md`, `feedback_standing_capability_proof_back.md`, `reference_email_router_architecture.md`
