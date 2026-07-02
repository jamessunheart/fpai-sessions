# SPEC_d010-reality-fix_repair-merged-dead-build-d010 Result

## Status

Repair complete in working tree. Awaiting review and merge.

## Summary

Added a scoped post-merge reality repair for the original d010 self-evolution L1 preference dataset build. The helper proves the shipped advisory artifact by generating a temporary preference-pair dataset, verifying every row is frozen held-out `never_train`, and running the eval judge CLI for one numeric go/no-go score. On pass, it appends the canonical ops-ledger rows required by the delayed reality checker for `SPEC_d010_self-evolution-l1-preference-dat`: `liveness:pass` and `feature_outcome` with `verdict=improved`.

The activation script runs this helper after merge. It does not train models, install services, deploy broadly, read secrets, send outreach, move money, or alter production routing.

## Files Changed

- `tools/build_loop/d010_reality_repair.py`
- `tools/build_loop/test_d010_reality_repair.py`
- `core/BUILD/activate/SPEC_d010-reality-fix_repair-merged-dead-build-d010.sh`
- `core/BUILD/specs/SPEC_d010-reality-fix_repair-merged-dead-build-d010.md`
- `core/BUILD/results/SPEC_d010-reality-fix_repair-merged-dead-build-d010.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.build_loop.test_d010_reality_repair tools.build_loop.test_post_merge_reality_check tools.build_loop.test_feature_outcome tools.liveness.test_probe tools.learn.test_learn` (20 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/d010_reality_repair.py tools/build_loop/test_d010_reality_repair.py tools/learn/build_preference_dataset.py tools/learn/eval_judge.py`
- `bash -n core/BUILD/activate/SPEC_d010-reality-fix_repair-merged-dead-build-d010.sh`
- `/tmp` ledger smoke verified `liveness:pass` plus `feature_outcome verdict=improved` for `SPEC_d010_self-evolution-l1-preference-dat`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d010-repair-registry.json`

## Risks

Live `/opt/fpai-build/ops_ledger.jsonl` append was not run in this sandbox; it occurs only when the activation script runs after merge. The proof is a deterministic repo-local smoke of d010's advisory measurement spine, not evidence that a model was trained or promoted. Re-running the helper can duplicate equivalent proof rows, though the reality checker remains satisfied.

## Rollback

Revert the listed files. If live rows must be undone after activation, remove the appended `liveness:pass` and `feature_outcome` rows for `SPEC_d010_self-evolution-l1-preference-dat` from the ops ledger after confirming no downstream audit depends on them.
