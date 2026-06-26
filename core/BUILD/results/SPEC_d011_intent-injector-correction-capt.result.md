# SPEC_d011_intent-injector-correction-capt Result

## Status
done in working tree / awaiting merge review

## Summary
Verified d011 as an idempotent replay of the already-present intent injector and correction capture pipeline:

- `tools/learn/capture_corrections.py` appends explicit James corrections as d010-compatible preference pairs with `(rejected, preferred)` content.
- `SERVICES/sunheart-brain/curator/build_context.py` injects bounded advisory current build context into owner-chat system prompts, with `SH_BUILD_CONTEXT_DISABLE=1` rollback.
- `SERVICES/sunheart-brain/curator/corrections.py` detects James correction turns, writes the previous bot response plus James's correction, and renders recent failures back into chat context.
- `SERVICES/sunheart-brain/curator/tgbot.py` calls correction capture before answer generation and appends the build-context suffix defensively around synthesis.

No implementation files were edited because duplicating the existing reviewed logic would increase risk without changing behavior. This branch registers d011, preserves the generated spec state, adds this result artifact, and verifies the existing implementation.

## Files Changed
- `core/BUILD/specs/SPEC_d011_intent-injector-correction-capt.md`
- `core/BUILD/results/SPEC_d011_intent-injector-correction-capt.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Existing Implementation Verified
- `tools/learn/capture_corrections.py`
- `tools/learn/test_capture_corrections.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `SERVICES/sunheart-brain/curator/corrections.py`
- `SERVICES/sunheart-brain/curator/test_corrections.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`

## Tests
- `env HOT_MEMORY_STATE_PATH=/tmp/d011-no-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/d011-no-diagnostic.json python3 -B -m unittest tools.learn.test_capture_corrections SERVICES.sunheart-brain.curator.test_build_context SERVICES.sunheart-brain.curator.test_corrections` (22 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learn/capture_corrections.py tools/learn/test_capture_corrections.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/corrections.py SERVICES/sunheart-brain/curator/test_corrections.py`
- `python3 -B tools/learn/capture_corrections.py --dataset /tmp/d011-preference-pairs.jsonl --prompt "d011 context" --rejected "stale bot answer" --preferred "inject current build context and capture corrections"`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d011-registry.json`
- `git diff --check`

## Review
Existing independent review is present at `core/BUILD/reviews/build-SPEC_d011_intent-injector-correction-capt.md` with verdict `APPROVE` and risk `med`. This replay did not alter implementation files after that review.

## Risks
- No live Telegram chat, live Supabase/Postgres write, or production bot restart was run in this sandbox.
- The focused correction test emits a warning when the optional blueprint updater tries to write to the read-only parent checkout; that path is wrapped and correction capture continues, matching the intended non-blocking behavior.
- Build-context injection remains advisory and bounded. Runtime rollback is `SH_BUILD_CONTEXT_DISABLE=1`; correction context volume is controlled by `SH_CORRECTIONS_CONTEXT_LIMIT`.

## Rollback
Revert the listed files. Runtime mitigation without reverting remains `SH_BUILD_CONTEXT_DISABLE=1` to disable build-context injection.

## Intent solved
d011 no longer leaves the live-amnesia repair ambiguous: current build context is injected into owner chat, and explicit corrections can flow into the d010 preference-pair dataset.

## Downstream intent unlocked
d010/d022 preference learning can consume real James correction pairs while the bot sees current buildstream context on every owner-chat synthesis.
