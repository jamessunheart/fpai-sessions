# Learning Loop Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16

## Identity

- **Function:** Loop - correction capture and preference pairs
- **Owner:** `SERVICES/sunheart-brain/curator/corrections.py` and `tools/learn/`
- **Status:** building
- **Decision:** d010-d023

## What it does

The Learning Loop turns James's corrections, build outcomes, review outcomes, and explicit feedback into durable preference evidence. It keeps the system from repeating the same mistake and creates structured seed data for future learning without training or live policy changes by default.

## How it works

- **Input:** Telegram corrections, build registry outcomes, review approvals/vetoes, and feedback JSONL rows.
- **Process:** Detect corrections, store correction pairs, inject recent failures into context, export preference pairs after watermark gates, and seed session-feedback examples.
- **Output:** `brain_index.corrections`, preference-pair JSONL rows, session feedback seed rows, and context blocks.
- **Side effects:** Future bot prompts include recent correction memory; exporters may append local JSONL artifacts.

## Quality standard

Corrections should be captured within one turn, preference-pair exports must be idempotent through watermarks, and learning evidence must remain advisory until a separate reviewed build explicitly changes routing or model behavior.

## Current behavior (verified)

- 2026-06-16: d014 correction capture exists in `SERVICES/sunheart-brain/curator/corrections.py`.
- 2026-06-16: d022 preference-pair exporter and d023 session-feedback seed exist under `tools/learn/`.

## Known gaps

- 2026-06-16: Live Supabase/production correction audit was not run in this sandbox.
- 2026-06-16: Conversation ratings need a future surface to append explicit feedback rows.
- 2026-06-16: Correction-to-blueprint updates are added by d050 and need live proof after merge.
- 2026-06-16: Actually, d010 was the preference dataset.
- 2026-06-16: Actually, d010 was the preference dataset.
- 2026-06-16: Actually, d010 was the preference dataset.
- 2026-06-16: Actually, d010 was the preference dataset.
- 2026-06-16: Actually, d010 was the preference dataset.

## Integration map

- **Depends on:** Ember, Ledger, brain_index, build registry, review artifacts.
- **Used by:** Ember context, Council diagnostics, future preference learning, blueprints.
- **DB tables:** `brain_index.corrections`, `brain_index.tg_messages`.
- **Kill switch:** `BLUEPRINTS_DISABLE=1` skips blueprint updates; learning exporters have their own disables.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d050 | Seeded Learning Loop blueprint | Future correction and feedback work has an advisory-learning contract |
| 2026-06-16 | d023 | Added session feedback preference seed | Build/review outcomes became structured advisory evidence |
| 2026-06-16 | d022 | Added correction-to-preference exporter | Corrections can seed preference pairs after watermark gates |
| 2026-06-15 | d014 | Added correction capture | James corrections became durable context |

## Test coverage

- `SERVICES/sunheart-brain/curator/test_corrections.py` covers correction detection, capture, and bounded rendering.
- `tools/learn/test_seed_preference_pairs.py` and `tools/learn/test_session_feedback_seed.py` cover exporters.
- NOT tested yet: live correction-to-blueprint update after a production Telegram correction.
