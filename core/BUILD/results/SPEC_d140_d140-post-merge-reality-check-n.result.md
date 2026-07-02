# SPEC_d140_d140-post-merge-reality-check-n result

## Status
Done in working tree. Not pushed or merged.

## Files changed
- `SERVICES/sunheart-brain/curator/decisions.py`
- `tools/build_loop/post_merge_reality_check.py`
- `tools/build_loop/test_post_merge_reality_check.py`
- `tools/build_loop/server_build_loop.sh`
- `core/BUILD/specs/SPEC_d140_d140-post-merge-reality-check-n.md`
- `core/BUILD/results/SPEC_d140_d140-post-merge-reality-check-n.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added a daily delayed post-merge reality checker. It scans `brain_index.decisions`
rows still marked `build_status='merged'` after the grace window (default 3
days), then requires two ledger-backed proofs for the original spec:

- LIVE artifact proof from a `liveness:pass` / `liveness_status=live` ops-ledger row.
- Metric movement proof from a `feature_outcome` ops-ledger row with `verdict=improved`.

If either proof is missing, the checker marks the source decision
`build_status='merged_dead'`, records reality audit columns, auto-queues one
focused `*-reality-fix` repair decision, appends a `post-merge-reality`
ops-ledger summary row, and sends a one-line Telegram alert when run with
`--send-alert`.

The server build loop now runs this checker once per UTC day during the existing
health pulse, guarded by `/opt/fpai-build/.post_merge_reality_check_day` and
`POST_MERGE_REALITY_CHECK_DISABLE=1`. The decision CLI now stamps `merged_at`
when existing `mark-merged <id>` calls succeed, so future delayed checks start
from actual merge time.

## Tests
- `python3 -B -m unittest tools.build_loop.test_post_merge_reality_check tools.build_loop.test_liveness_probe tools.build_loop.test_feature_outcome tools.liveness.test_probe`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/post_merge_reality_check.py tools/build_loop/test_post_merge_reality_check.py SERVICES/sunheart-brain/curator/decisions.py`
- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d140-registry.json`
- `git diff --check`

## Risks
- The metric proof is intentionally strict: no `feature_outcome verdict=improved`
  means the merged decision is treated as dead after the grace window. This may
  queue repair specs for older builds that never emitted feature outcomes.
- Existing merged rows without `merged_at` fall back to available timestamp
  columns such as `updated_at` or `created_at`, so the first live run may catch
  older dead-on-arrival merges immediately.
- Live DB mutation, live Telegram send, and a real server timer run were not
  exercised in this sandbox.

## Rollback
Revert the listed files. Runtime mitigation without code rollback:
`POST_MERGE_REALITY_CHECK_DISABLE=1` disables the daily checker path in
`server_build_loop.sh`.

## Intent solved
Merged decisions no longer stay trusted by status alone; after the grace window
they must prove both artifact liveness and metric movement.

## Downstream intent unlocked
d131-style dead-on-arrival merges become automatically visible repair specs
within the daily build-loop reality check instead of requiring James to discover
them by hand.
