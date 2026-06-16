# Cora Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16

## Identity

- **Function:** CORA - reward policy and closed-loop attention credit
- **Owner:** `docs/policy/CORA_POLICY_v0.2.md`
- **Status:** building
- **Decision:** d035

## What it does

CORA defines the review-only reward policy for non-cash, non-investment, non-transferable attention credits. It gives FPOS a constrained way to recognize useful proof, participation, and learning without creating unsafe monetary, securities, or public-market behavior.

## How it works

- **Input:** Approved policy text, future proof events, and future reward triggers.
- **Process:** Apply earn, burn, cap, decay, and containment rules once product wiring exists.
- **Output:** Reviewable policy and future credit ledger entries.
- **Side effects:** Future live rewards may affect user motivation and compliance exposure, so policy changes require review.

## Quality standard

No product path may reference live CORA rewards until the policy has reviewed earn/burn amounts, caps, legal containment, and tests for no cash-out/no transfer/no investment language. Any future live reward write must have a kill switch and ledger proof.

## Current behavior (verified)

- 2026-06-16: d035 added `docs/policy/CORA_POLICY_v0.2.md` as a review-only policy draft with earn rules, backing, spends/burns, issuance caps, legal containment, decay/renewal, and gap log.

## Known gaps

- 2026-06-16: Amounts, caps, and prices remain provisional.
- 2026-06-16: No live reward ledger or user balance wiring is verified in this seed.
- 2026-06-16: Compliance/legal review remains required before launch.

## Integration map

- **Depends on:** Ledger, Spark, Steward, Beacon proof events.
- **Used by:** Onboarding, user agent, rewards surfaces, future marketplace loops.
- **DB tables:** Future CORA balance/ledger tables to be verified.
- **Kill switch:** No live runtime yet; future reward wiring must define one.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d050 | Seeded CORA blueprint | Reward work now has a clear policy-first contract |
| 2026-06-16 | d035 | Drafted CORA v0.2 policy | Defined reviewable earn, burn, cap, decay, and containment rules before launch |

## Test coverage

- `docs/policy/test_cora_policy.py` verifies required policy sections and containment language.
- NOT tested yet: live reward award/burn ledger behavior.
