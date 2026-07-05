# SPEC_d183_metric-replace-awareness-with-a result

## Files changed

- `tools/awareness/verify_awareness.py`
- `tools/awareness/reliability_probe.py`
- `tools/awareness/test_reliability_probe.py`
- `core/BUILD/specs/SPEC_d183_metric-replace-awareness-with-a.md`
- `core/BUILD/results/SPEC_d183_metric-replace-awareness-with-a.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Replaced the primary awareness metric with a behavioral bot-answer probe. `verify_awareness.py --probe-bot-response` now loads the latest active `brain_index.session_insights` row, derives a factual question from it, calls the bot `_synthesize_answer()` path with brain search disabled, bounds the answer wait to 10 seconds, and grades whether the answer matches the latest insight by normalized keyword overlap.

Kept the old render/title check as a separate secondary signal named `context_render_continuity`. `verify_awareness.py --probe-latest` remains available for that continuity check, but it is no longer the awareness score.

`reliability_probe.py` now computes the rolling awareness rate from `behavioral_pass` only, ignores legacy title-proxy rows that lack `behavioral_pass`, and writes both `behavioral_pass` and `context_render_continuity` into the ops row and `core/BUILD/signals/awareness_reliability.json`.

## Tests

- `python3 -B -m unittest tools.awareness.test_reliability_probe tools.continuity.test_write_session_insights` (10 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/awareness/verify_awareness.py tools/awareness/reliability_probe.py tools/awareness/test_reliability_probe.py tools/continuity/write_session_insights.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d183-registry.json`
- `git diff --check`

## Proof

Focused tests prove the behavioral probe asks the bot a factual question derived from the latest insight, passes when the answer includes the latest insight's key terms, fails when the answer is only generic status, records `behavioral_pass` in the metric JSON, preserves `context_render_continuity` separately, and excludes old title-proxy rows from the rolling awareness rate.

## Risks

The sandbox did not run the live DB plus live bot probe. First server run should execute `tools/awareness/verify_awareness.py --probe-bot-response --json` and confirm the bot answers through the real `/opt/sh-brain-src/curator/tgbot.py` path within 10 seconds.

Keyword grading is intentionally deterministic and reversible. It is stricter than a human semantic grader and may fail paraphrases that avoid the expected terms; the proof artifact exposes `expected_keywords` and `matched_keywords` so misses are auditable.

## Rollback

Revert this branch. The old context-render probe remains available as `--probe-latest`, and the runtime timer can be reverted to the prior `verify_latest()` behavior by reverting `tools/awareness/reliability_probe.py`.

## Intent solved

Awareness now measures whether the bot actually answers a latest-session-insight question correctly, not whether a title string appears verbatim in rendered context.

## Downstream intent unlocked

The reliability timer can report a meaningful bot-awareness rate while still surfacing context-render continuity as a separate diagnostic signal.
