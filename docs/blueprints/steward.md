# Steward Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16

## Identity

- **Function:** Steward - per-user agent
- **Owner:** future `curator/agent/` namespace and user tables
- **Status:** building
- **Decision:** d039-d043 lineage; seeded by d050

## What it does

Steward is the per-user agent layer. It isolates each user's memory, profile, permissions, CORA balance, and capability grants so FPOS can serve more than James without blending identities or leaking context between users.

## How it works

- **Input:** Spark intake, authenticated channel identity, user corrections, proof events, and capability grants.
- **Process:** Create or load a user namespace, maintain an Agent Passport, enforce per-user boundaries, and expose only the capabilities granted to that user.
- **Output:** User-specific context, Agent Passport state, and bounded capability access.
- **Side effects:** Future writes may create user records, reward balances, and preference memory.

## Quality standard

Every user-facing path must resolve to exactly one user namespace before writing memory or rewards. Cross-user memory leakage target is zero; tests must cover namespace isolation before any second-user live rollout.

## Current behavior (verified)

- 2026-06-16: Existing blueprints and handoff describe d039-d043 as building. This seed does not verify a complete per-user namespace implementation in the checkout.

## Known gaps

- 2026-06-16: Agent Passport schema and storage are not verified here.
- 2026-06-16: Per-user CORA balances and grants are not verified here.
- 2026-06-16: Namespace isolation needs dedicated tests before live multi-user use.

## Integration map

- **Depends on:** Spark, Ember, CORA, Hermes, Ledger.
- **Used by:** User onboarding, One Chat, rewards, future capability marketplace.
- **DB tables:** `brain_index.user_agents` and future passport/balance tables to be verified.
- **Kill switch:** Future steward runtime must define one before live multi-user rollout.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d050 | Seeded Steward blueprint | Multi-user work now has an explicit isolation standard |

## Test coverage

- NOT tested yet: namespace isolation, passport persistence, grant enforcement, reward balance writes.
