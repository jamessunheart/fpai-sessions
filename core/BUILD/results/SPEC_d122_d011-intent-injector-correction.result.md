# SPEC_d122_d011-intent-injector-correction Result

## Status
done in working tree / awaiting merge review

## Summary
Verified d122 as an idempotent retry/fix of d011. The requested intent injector and correction capture pipeline already exists in tracked implementation files from the original d011/d014 path:

- `tools/learn/capture_corrections.py` appends James correction pairs in the d010 preference-pair JSONL shape.
- `SERVICES/sunheart-brain/curator/build_context.py` injects bounded advisory build context into owner chat prompts, with `SH_BUILD_CONTEXT_DISABLE=1` rollback.
- `SERVICES/sunheart-brain/curator/corrections.py` captures conversational corrections and surfaces recent failures back into future context.
- `SERVICES/sunheart-brain/curator/tgbot.py` calls correction capture before answer generation and appends build-context suffixes defensively.

No implementation files were edited, because duplicating the existing live-bot logic would increase risk without changing behavior. This branch registers the d122 retry, preserves the generated d122 spec, adds this result artifact, and verifies the existing behavior with focused tests.

## Files Changed
- `core/BUILD/specs/SPEC_d122_d011-intent-injector-correction.md`
- `core/BUILD/results/SPEC_d122_d011-intent-injector-correction.result.md`
- `core/BUILD/REGISTRY.json`

## Existing Implementation Verified
- `tools/learn/capture_corrections.py`
- `tools/learn/test_capture_corrections.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `SERVICES/sunheart-brain/curator/corrections.py`
- `SERVICES/sunheart-brain/curator/test_corrections.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`

## Tests
- `env HOT_MEMORY_STATE_PATH=/tmp/d122-no-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/d122-no-diagnostic.json python3 -B -m unittest tools.learn.test_capture_corrections SERVICES.sunheart-brain.curator.test_build_context SERVICES.sunheart-brain.curator.test_corrections` (17 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learn/capture_corrections.py tools/learn/test_capture_corrections.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/corrections.py SERVICES/sunheart-brain/curator/test_corrections.py`
- `python3 -B tools/learn/capture_corrections.py --dataset /tmp/d122-preference-pairs.jsonl --prompt "d122 retry context" --rejected "stale d011 answer" --preferred "d011 implementation is already present and verified"`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks
- No live Telegram chat, live Supabase/Postgres write, or production bot restart was run in this sandbox.
- A fresh d122 independent AI review was attempted with the local Claude CLI but failed with `API Error: Unable to connect to API (ConnectionRefused)`. The unchanged implementation remains covered by the existing `core/BUILD/reviews/build-SPEC_d011_intent-injector-correction-capt.md` approval, but this metadata-only d122 retry still needs a successful reviewer pass before claiming fresh independent review.
- The focused correction test emits a warning when the optional blueprint updater tries to write to the read-only parent checkout; the correction path is wrapped and continues, matching the intended non-blocking behavior.
- Build-context injection remains advisory and bounded. Runtime rollback remains `SH_BUILD_CONTEXT_DISABLE=1`; correction context limit remains controlled by `SH_CORRECTIONS_CONTEXT_LIMIT`.

## Rollback
Remove `core/BUILD/specs/SPEC_d122_d011-intent-injector-correction.md`, remove this result file, and remove the d122 registry entry. No runtime rollback is required because this branch does not alter implementation behavior.

## Intent solved
d122 no longer leaves the d011 fix loop ambiguous: the existing intent injector plus correction capture pipeline is registered, reverified, and ready for merge review as an idempotent retry.

## Downstream intent unlocked
The build loop can treat d122 as closed and continue to the next concrete liveness/learning repair instead of repeatedly re-queuing the already-built d011 pipeline.
