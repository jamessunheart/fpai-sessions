# SPEC_d011-reality-fix_repair-merged-dead-build-d011 Result

## Status
done in working tree / awaiting independent review + merge

## Summary
Added a scoped proof repair for the original d011 intent-injector and correction-capture pipeline. The helper runs a deterministic repo-local smoke with temporary evidence: correction-pair creation and append dedupe, correction signal capture against a supplied bot turn with external writes stubbed out, correction memory rendering, bounded advisory build-context rendering, and static verification that `tgbot.py` still wires `capture_if_correction` and `build_context_system_suffix`.

When the smoke passes, it appends the two canonical ops-ledger rows required by the delayed reality checker for `SPEC_d011_intent-injector-correction-capt`: `liveness:pass` and `feature_outcome` with `verdict=improved`. The activation script runs this helper after merge; it does not send Telegram messages, write the live DB, restart the bot, install services, or deploy broadly.

## Files Changed
- `tools/build_loop/d011_reality_repair.py`
- `tools/build_loop/test_d011_reality_repair.py`
- `core/BUILD/activate/SPEC_d011-reality-fix_repair-merged-dead-build-d011.sh`
- `core/BUILD/specs/SPEC_d011-reality-fix_repair-merged-dead-build-d011.md`
- `core/BUILD/results/SPEC_d011-reality-fix_repair-merged-dead-build-d011.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests
- `python3 -B -m unittest tools.build_loop.test_d011_reality_repair tools.build_loop.test_post_merge_reality_check tools.build_loop.test_feature_outcome tools.liveness.test_probe tools.learn.test_capture_corrections SERVICES.sunheart-brain.curator.test_build_context SERVICES.sunheart-brain.curator.test_corrections` (39 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/d011_reality_repair.py tools/build_loop/test_d011_reality_repair.py tools/learn/capture_corrections.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/corrections.py`
- `bash -n core/BUILD/activate/SPEC_d011-reality-fix_repair-merged-dead-build-d011.sh`
- `/tmp` ledger smoke verified `liveness:pass` plus `feature_outcome verdict=improved`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d011-repair-registry.json`
- `git diff --check`

## Risks
- Live `/opt/fpai-build/ops_ledger.jsonl` append was not run in this sandbox; it occurs only when the activation script runs after merge.
- The proof is a deterministic repo-local smoke for d011's advisory measurement spine, not a long-horizon production chat quality metric.
- Re-running the helper can duplicate equivalent proof rows, though the reality checker remains satisfied.

## Rollback
Revert the listed files. If live rows must be undone, remove the appended `liveness:pass` and `feature_outcome` rows for `SPEC_d011_intent-injector-correction-capt` from the ops ledger after confirming no downstream audit depends on them.

## Intent Solved
The original d011 correction-capture and build-context injector build gets the missing live-artifact and metric-movement proof rows required to repair its `merged_dead` status.

## Downstream Intent Unlocked
The delayed post-merge reality checker can classify the d011 live-amnesia repair as real after the activation script writes proof on server 162.
