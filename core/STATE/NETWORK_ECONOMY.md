# Network Economy

Status: repo-side architecture scaffold. No live treasury mutations, wallet
transactions, fiat conversion, outreach sends, DB writes, deploys, or reserve
changes are performed by this build.

## Principle

The economy optimizes for value retention over extraction. Every exchange should
prefer the least-extractive viable path:

1. CORA credits first when both sides can settle internally.
2. On-chain USDC when CORA is unavailable and both sides have wallets.
3. Fiat only when an exchange truly requires an external rail such as payroll,
   legal, tax, rent, regulated payment, or an external vendor.

Fiat off-ramp exists as a relief valve, not the default recommendation.

## Network Roles

| Role | Brings | Primary recruiting signal |
|---|---|---|
| Seeker | energy, feedback, growth story | stuck, purpose, full potential, clarity |
| Coach | skill, time, lived knowledge | mentor, coach, facilitated terrain |
| Builder | capability expansion | code, design, curriculum, integrations |
| Validator | trust signal, proof | review, audit, quality, outcome verification |
| Connector | reach, warm introductions | community, audience, newsletter, podcast |
| Patron | capital, resources, runway | grants, philanthropy, aligned funding |
| Anchor | credibility, embodied story | public mission, founder, speaker, story |

Role scores are private routing signals, not public rankings.

## Value Ledger

Target table shape:

```sql
CREATE TABLE brain_index.value_ledger (
  id SERIAL PRIMARY KEY,
  at TIMESTAMPTZ DEFAULT now(),
  from_identifier TEXT,
  to_identifier TEXT,
  value_type TEXT,
  amount FLOAT,
  currency TEXT,
  exchange_rate_to_cora FLOAT,
  description TEXT,
  external_extraction FLOAT DEFAULT 0.0,
  internal_flag BOOLEAN DEFAULT true
);
```

Tracked exchange types include attention, time, knowledge, build, outcome, fiat,
CORA, crypto, referrals, validation proof, coaching sessions, and treasury yield
income. This build only returns DB-shaped rows; applying the migration and
writing live rows is a later approved live-host task.

## Currencies

| Currency | Role |
|---|---|
| CORA | internal credit, default path, zero extraction |
| hours | time accounting for coaching, building, review |
| attention_points | comments, corrections, shares, useful feedback |
| outcome_credits | validated outcome value |
| USDC | low-friction external reserve path when both sides have wallets |
| USD/fiat | external rail for legally or operationally required payments |
| crypto | external reserve/yield accounting only; no autonomous movement |

All currencies report a CORA equivalent through `exchange_rate_to_cora` so the
system can compare circulation and extraction.

## Network Value Score

Private member score:

```text
NVS = value_given_in_cora_equivalent / (value_received_in_cora_equivalent + 1)
```

- `> 1.0`: net contributor, route higher-trust opportunities when relevant.
- `0.5-1.0`: balanced, continue reciprocal exchange routing.
- `< 0.5`: net extractor, gently surface one low-friction contribution path.

NVS must not become a public leaderboard.

## Off-Ramp Rule

When a person requests fiat off-ramp, check whether the stated need can be met
inside the network first. Example: if someone has 200 CORA credits and wants a
coach session costing 75 credits, offer the internal session before conversion.

Weekly proof should report:

- total CORA-equivalent value exchanged,
- internal retention rate,
- external extraction rate,
- week-over-week retention direction.

## Treasury Boundary

The crypto treasury is the external reserve. CORA is the internal economy. A
future guarded live spec may mint community-pool credits when new external
capital or yield enters, but this scaffold cannot move funds, convert assets,
sign transactions, or recommend live treasury action.

## Credit Unlock Ladder

| Tier | Unlock |
|---|---|
| 1 | AI access, early features, community recognition |
| 2 | coaching sessions, peer review, mentorship |
| 3 | custom builds, integrations, content creation |
| 4 | Zen Village stays, retreat access, village resources |
| 5 | anything the network can provide, credits first |

