# SPEC_d181_self-heal-awareness-render-late

- Status: done in working tree / awaiting review + merge
- Branch: `build/SPEC_d181_self-heal-awareness-render-late`
- Files changed:
  - `SERVICES/sunheart-brain/curator/test_build_context.py`
  - `tools/awareness/verify_awareness.py`
  - `tools/awareness/test_reliability_probe.py`
  - `core/BUILD/specs/SPEC_d181_self-heal-awareness-render-late.md`
  - `core/BUILD/results/SPEC_d181_self-heal-awareness-render-late.result.md`
  - `core/BUILD/REGISTRY.json`
  - `docs/codex/HANDOFF.md`

## Summary

`verify_awareness.py` now defines the probe target as the true newest active `brain_index.session_insights` row by timestamp (`ORDER BY ts DESC`), not the highest-weight row. This keeps the probe strict and aligned with the d181 contract: the latest insight title must reach bot context.

The existing `build_context.py` renderer already had the d180 fix on this branch: it loads the newest row first, then fills from weight-ranked older rows, and pins the first recent-insight lines during bounded rendering. This build adds focused proof for the reported failure shape: one low-weight newest insight plus a 443-row older high-weight backlog still renders the newest title inside `max_chars=1800`.

The awareness probe was not loosened.

## Tests

- `env HOT_MEMORY_STATE_PATH=/tmp/d181-no-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/d181-no-diagnostic.json python3 -B -m unittest SERVICES.sunheart-brain.curator.test_build_context` (18 OK)
- `python3 -B -m unittest tools.awareness.test_reliability_probe tools.continuity.test_write_session_insights` (8 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py tools/awareness/verify_awareness.py tools/awareness/test_reliability_probe.py tools/awareness/reliability_probe.py tools/continuity/write_session_insights.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d181-registry.json`
- `git diff --check`

## Proof

Focused regression coverage proves a low-weight newest insight is loaded first and survives a bounded 1800-character render even with 443 older high-weight insights behind it. Probe coverage proves `latest_session_insight()` now uses timestamp ordering, so `latest title in context` tests the actual newest row instead of a weight-ranked row.

## Risks

Live DB `verify_awareness --probe-latest` was not run in this sandbox. First production timer after merge should confirm the live `brain_index.session_insights` probe passes against `/opt/sh-brain-src/curator/build_context.py`.

## Rollback

Revert this branch. Runtime kill switches remain `SH_SESSION_INSIGHTS_DISABLE=1` for the session-insight block and `SH_BUILD_CONTEXT_DISABLE=1` for the whole advisory context suffix.

## Intent

- Intent solved: the actual newest session insight reaches owner-bot context under the strict awareness probe.
- Downstream intent unlocked: awareness reliability can recover without lowering the threshold or weakening the probe.
