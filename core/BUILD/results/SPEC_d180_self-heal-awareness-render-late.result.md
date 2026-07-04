# SPEC_d180_self-heal-awareness-render-late

- Status: done in working tree / awaiting review + merge
- Branch: `build/SPEC_d180_self-heal-awareness-render-late`
- Files changed:
  - `SERVICES/sunheart-brain/curator/build_context.py`
  - `SERVICES/sunheart-brain/curator/test_build_context.py`
  - `core/BUILD/specs/SPEC_d180_self-heal-awareness-render-late.md`
  - `core/BUILD/results/SPEC_d180_self-heal-awareness-render-late.result.md`
  - `core/BUILD/REGISTRY.json`
  - `docs/codex/HANDOFF.md`

## Summary

`build_context.py` now explicitly loads the newest active `brain_index.session_insights` row by timestamp and prepends it before the existing weight-ranked insight set. The bounded renderer also pins the first recent-insight lines before filling the remaining budget, so both the newest insight title and the existing top-ranked awareness probe row survive the normal `max_chars=1800` truncation instead of being pushed out by older or larger context blocks.

The awareness probe was not loosened.

## Tests

- `env HOT_MEMORY_STATE_PATH=/tmp/d180-no-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/d180-no-diagnostic.json python3 -B -m unittest SERVICES.sunheart-brain.curator.test_build_context` (17 OK)
- `python3 -B -m unittest tools.awareness.test_reliability_probe tools.continuity.test_write_session_insights` (7 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py tools/awareness/verify_awareness.py tools/awareness/reliability_probe.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d180-registry.json`
- `git diff --check`

## Proof

Focused regressions prove a lower-weight newest insight is loaded before older high-weight rows, and that both the newest insight title and older high-weight probe row remain present in a bounded 1800-character render even when earlier context would otherwise consume the character budget. This targets the root failure behind `latest title missing from bot context`.

## Risks

Live DB proof was not run in this sandbox, so the first post-merge awareness timer should confirm the production `verify_awareness --probe-latest` path passes against live `brain_index.session_insights`. If `SH_SESSION_INSIGHTS_DISABLE=1` is set in runtime env, this context path remains intentionally disabled.

## Rollback

Revert this branch. The runtime kill switch remains `SH_SESSION_INSIGHTS_DISABLE=1` for only the session-insight block, or `SH_BUILD_CONTEXT_DISABLE=1` for the entire advisory build-context suffix.

## Intent

- Intent solved: the latest session insight reaches owner-bot context under the existing awareness probe and bounded render contract.
- Downstream intent unlocked: awareness reliability can recover without lowering the probe threshold or metric strictness.
