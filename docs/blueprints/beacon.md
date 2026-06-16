# Beacon Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16

## Identity

- **Function:** Beacon - growth engine
- **Owner:** `tools/beacon/` and `docs/content_bank/`
- **Status:** building
- **Decision:** d037-d038

## What it does

Beacon is the growth engine for FPOS. It turns reviewed truth assets into organic-first campaign variants, tracks proof-bearing acquisition signals, and protects the system from reward farming or growth loops that outrun actual human proof.

## How it works

- **Input:** Reviewed content-bank assets, campaign definitions, links, proof counts, and CORA reward signals.
- **Process:** Seed missing source assets, load campaign material, generate variants, and throttle reward farming when earns outrun proof.
- **Output:** Draft truth assets, seed campaign docs, generated variants, and throttle decisions.
- **Side effects:** May write content-bank files or ops-ledger rows; public publishing remains James-approved.

## Quality standard

Beacon must use reviewed source assets rather than blank-page generation, keep public copy draft-tagged until approved, and throttle CORA farming when rewards exceed proof by more than 10:1. Campaign tests must cover seed safety and variant source loading.

## Current behavior (verified)

- 2026-06-16: d038 added seven draft-tagged truth assets, seed campaigns, missing-file-only content seeding, variant source loading, and a CORA farming guard in `tools/beacon/`.

## Known gaps

- 2026-06-16: Content assets remain draft-only until James edits/approves them.
- 2026-06-16: Campaign links and live conversion tracking are not populated in this seed.
- 2026-06-16: d037 live growth campaigns are not verified here.

## Integration map

- **Depends on:** CORA, Ledger, Hermes, Spark, content bank.
- **Used by:** Growth surfaces, campaign testing, onboarding entry paths.
- **DB tables:** Future attribution/campaign tables to be verified.
- **Kill switch:** `CONTENT_BANK_DISABLE=1` for seed script; future Beacon runtimes must define their own.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d050 | Seeded Beacon blueprint | Growth work now has a reviewed-source and proof-before-reward contract |
| 2026-06-16 | d038 | Added content bank and farming guard | Beacon can remix source truth assets and detect reward farming pressure |

## Test coverage

- `tools/beacon/test_content_bank.py` covers content-bank seeding, variant source loading, and CORA farming guard.
- NOT tested yet: live attribution and conversion tracking.
