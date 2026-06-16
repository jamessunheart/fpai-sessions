# Hermes Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16

## Identity

- **Function:** Hermes - channel gateway
- **Owner:** `tools/comms/` and future channel adapters
- **Status:** building
- **Decision:** d034 channel gateway lineage; seeded by d050

## What it does

Hermes is the channel gateway for FPOS. It normalizes messages from Telegram, email, web, SMS, WhatsApp, or future surfaces into one downstream shape so Spark, Ember, Ledger, and reserved-class gates do not have to know channel-specific details.

## How it works

- **Input:** Inbound messages or fixture-backed channel payloads.
- **Process:** Read channel-specific data, normalize sender/content/metadata, classify obvious send/reply/review boundaries, and pass reviewable work downstream.
- **Output:** Normalized message records, draft lanes, or human-edge send gates.
- **Side effects:** May write review artifacts or queue human approval gates; must never send public outreach automatically.

## Quality standard

Every live channel adapter must be fixture-first, read-only by default, covered by focused tests, and must create a human-edge gate before any send-capable path. Zero automatic sends without explicit James approval.

## Current behavior (verified)

- 2026-06-16: `tools/comms/` provides fixture-backed email triage and draft staging from the Comms Hub rung-4 build. Live provider adapters are not enabled in this seed.

## Known gaps

- 2026-06-16: d034 channel gateway behavior is not fully represented by a dedicated `curator/hermes/` module in this checkout.
- 2026-06-16: Live SMS/WhatsApp/web adapters are not verified here.
- 2026-06-16: Send safety is policy-level and queue-level; no live provider send path should exist without a separate approved spec.

## Integration map

- **Depends on:** Spark, Ember, Reserved Class classifier, queue gates, channel APIs when approved.
- **Used by:** Spark, Ember, Comms Hub, Ledger.
- **DB tables:** To be verified for live adapters; fixture path uses repo files.
- **Kill switch:** Adapter-specific; blueprint automation disabled with `BLUEPRINTS_DISABLE=1`.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d050 | Seeded Hermes blueprint | Future channel work has an explicit no-auto-send contract |

## Test coverage

- `tools/comms/test_hub.py` covers fixture email triage/draft behavior.
- NOT tested yet: live channel normalization across Telegram/SMS/WhatsApp/web.
