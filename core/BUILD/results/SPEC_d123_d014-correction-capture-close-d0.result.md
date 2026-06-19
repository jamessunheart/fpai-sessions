# SPEC_d123_d014-correction-capture-close-d0 Result

## Status
done in working tree / awaiting merge review

## Summary
Closed the remaining d014 correction-memory gap in the Telegram prompt path. The d011/d014 implementation already had the Supabase/Postgres `corrections` table, correction-signal detection, best-effort writes, and recent correction reads. This branch fixes the path where fresh `HOT_STATE` became the primary context and returned early before appending recent corrections.

Now `build_context_system_suffix()` still uses fresh `HOT_STATE` as the primary current-memory context, but also appends the last 10 rendered correction pairs for the conversation. That keeps James's correction memory visible on every owner bot turn, including the HOT_STATE path most likely to be active in production.

## Files Changed
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `core/BUILD/specs/SPEC_d123_d014-correction-capture-close-d0.md`
- `core/BUILD/results/SPEC_d123_d014-correction-capture-close-d0.result.md`
- `core/BUILD/REGISTRY.json`

## Existing Implementation Verified
- `SERVICES/sunheart-brain/index/schema.sql` contains the additive `corrections` table with `id`, `conversation_id`, `bot_turn_id`, `original_response`, `james_correction`, and `captured_at`.
- `SERVICES/sunheart-brain/curator/corrections.py` detects explicit corrections and negation/restatement, writes correction pairs to `brain_index.corrections`, optionally mirrors through Supabase REST, and reads recent pairs.
- `SERVICES/sunheart-brain/curator/tgbot.py` calls `capture_if_correction()` on the owner plain-text path before answer generation and logs the bot answer afterward.
- `SERVICES/sunheart-brain/curator/build_context.py` injects correction memory into generated prompt context.

## Tests
- `env HOT_MEMORY_STATE_PATH=/tmp/d123-no-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/d123-no-diagnostic.json python3 -B -m unittest tools.learn.test_capture_corrections SERVICES.sunheart-brain.curator.test_build_context SERVICES.sunheart-brain.curator.test_corrections` (18 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learn/capture_corrections.py tools/learn/test_capture_corrections.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/corrections.py SERVICES/sunheart-brain/curator/test_corrections.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`

## Risks
- The sandbox did not run a live Telegram correction cycle, live Supabase/Postgres write, live Supabase log audit, production bot restart, deploy, push, merge, outreach, secrets, or money movement.
- The focused correction test emits a warning from the optional blueprint updater trying to write to the read-only parent checkout; the correction path remains non-blocking and the tests pass.
- Fresh independent AI review was attempted with local Claude and failed with `API Error: Unable to connect to API (ConnectionRefused)`. Existing d011/d014 review artifacts remain approved, but this d123 delta still needs a successful reviewer pass before claiming `independent-AI-reviewed`.

## Rollback
Revert the listed files. Runtime mitigation without reverting remains `SH_BUILD_CONTEXT_DISABLE=1` to disable build-context injection, or `SH_CORRECTIONS_CONTEXT_LIMIT=0` only if the live code is adjusted to treat zero as disabled.

## Intent solved
d123/d014 no longer leaves correction memory suppressed when HOT_STATE is fresh; James's recent correction pairs are appended to owner chat context on the active prompt path.

## Downstream intent unlocked
Ember can run one live proof cycle after merge: send a harmless Telegram correction, confirm a row lands in `brain_index.corrections` or Supabase REST, and confirm the next bot turn includes that correction memory even while HOT_STATE is fresh.
