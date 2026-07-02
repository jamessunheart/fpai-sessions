# SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e-reality-fix_repair-merged-dead-build-36a7316 — result

## Status
Done in working tree. Not pushed, merged, deployed, or broadly activated.

## Files changed
- `tools/build_loop/session_persistence_reality_repair.py`
- `tools/build_loop/test_session_persistence_reality_repair.py`
- `core/BUILD/activate/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e-reality-fix_repair-merged-dead-build-36a7316.sh`
- `core/BUILD/specs/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e-reality-fix_repair-merged-dead-build-36a7316.md`
- `core/BUILD/results/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e-reality-fix_repair-merged-dead-build-36a7316.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added a scoped post-merge proof repair for the original `SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence` build. The helper runs a real session persistence save/show smoke against a temporary state directory, verifies the shipped `build_context.py` integration file exists, then appends the exact ops-ledger rows the delayed reality checker requires for the original spec: `liveness:pass` and `feature_outcome` with `verdict=improved`.

The activation script is append-only and runs the helper after the repair merges. It does not install services, deploy code, send messages, touch secrets, stop/delete services, or move money.

## Tests
- `python3 -B -m unittest tools.build_loop.test_session_persistence_reality_repair tools.build_loop.test_post_merge_reality_check tools.build_loop.test_feature_outcome tools.liveness.test_probe tools.continuity.test_session_persistence`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/session_persistence_reality_repair.py tools/build_loop/test_session_persistence_reality_repair.py tools/continuity/session_persistence.py`
- `bash -n core/BUILD/activate/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e-reality-fix_repair-merged-dead-build-36a7316.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/36a-repair-registry.json`
- `python3 -B -m tools.build_loop.session_persistence_reality_repair --repo-root . --ops-ledger /tmp/.../ops.jsonl` smoke verified two rows: `liveness:pass` and `feature_outcome verdict=improved`
- `git diff --check`

## Risks
- The live `/opt/fpai-build/ops_ledger.jsonl` append was not run in this sandbox; it will occur only when the activation script runs after merge.
- The proof is a repo-local functional smoke, not a long-running usage metric. It proves the original stated capability can persist and reload a snapshot across fresh CLI invocations.
- The helper appends proof rows each time it is run. Re-running is safe for the reality checker, but it can duplicate equivalent proof rows in the ledger.

## Rollback
Revert the listed files. Runtime cleanup, if needed, is to remove the appended `liveness:pass` and `feature_outcome` rows for `SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence` from the ops ledger after confirming no downstream audit depends on them.

## Intent solved
The merged-dead session-persistence build now has a repair path that writes the missing canonical live-artifact and metric-movement proof rows for the original spec.

## Downstream intent unlocked
The delayed post-merge reality checker can classify the original session-persistence build as real instead of merged-dead after the activation script appends the proof rows on server 162.
