# Health Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16

## Identity

- **Function:** Health - health checks and smoke tests
- **Owner:** `tools/selftest/` and `tools/build_loop/health_check.sh`
- **Status:** building
- **Decision:** d049

## What it does

Health verifies that the autonomous FPOS loop is still alive, bounded, and coherent after builds. It checks imports, ledger behavior, build-loop liveness, smoke evidence, and self-standing readiness signals so failures surface before James has to discover them.

## How it works

- **Input:** Repo state, ops ledger rows, build-loop files, imports, and smoke-test commands.
- **Process:** Run focused checks, summarize pass/warn/fail evidence, and report status to the loop or digest.
- **Output:** Selftest reports, health-check status, and ops-ledger evidence.
- **Side effects:** May write canary ledger rows or status artifacts.

## Quality standard

Every merge should be followed by a health signal within 6 hours. Critical import or smoke failures must block or surface the next merge cycle, while warnings remain explicit and dated.

## Current behavior (verified)

- 2026-06-16: Handoff references d049 health check and smoke tests as the current health layer. Existing selftest modules provide repo-side status checks.

## Known gaps

- 2026-06-16: This seed does not verify the full d049 smoke suite live on server 162.
- 2026-06-16: Blueprint update health proof is not yet part of smoke checks.

## Integration map

- **Depends on:** Forge, Ledger, repo imports, ops-ledger files.
- **Used by:** Forge, morning digest, self-standing checks, James/Ember status surfaces.
- **DB tables:** None required for repo smoke tests; live checks may read brain_index indirectly.
- **Kill switch:** Health scripts should remain explicit; blueprint automation disabled with `BLUEPRINTS_DISABLE=1`.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d050 | Seeded Health blueprint | Smoke-test work now has an explicit post-merge standard |

## Test coverage

- `tools/selftest/test_check.py` and `tools/selftest/test_report.py` cover selftest behavior.
- `tools/build_loop/test_queue_status.sh` covers queue status behavior.
- NOT tested yet: full server-162 post-merge smoke cycle from this sandbox.
