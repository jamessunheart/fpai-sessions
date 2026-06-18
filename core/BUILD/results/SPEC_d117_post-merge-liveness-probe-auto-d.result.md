# SPEC_d117_post-merge-liveness-probe-auto-d Result

## Status
done in working tree / awaiting merge review

## Summary
Added typed post-merge liveness declarations and honest live-state surfacing. The server build loop now carries both `liveness` declarations and legacy `liveness_check` commands, runs a read-only typed probe after `activate.sh`, logs `live` / `partial` / `dead` / `planned` rows to the ops ledger, and auto-queues the existing activation follow-up path when the probe is not live. HOT_STATE now surfaces merged-but-not-live partial/dead rows, and morning digest/live-system status report the honest map of what is running, partial, dead, or only planned.

## Files Changed
- `tools/liveness/probe.py`
- `tools/liveness/test_probe.py`
- `tools/liveness/__init__.py`
- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/test_liveness_probe.py`
- `SERVICES/sunheart-brain/curator/decisions.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `SERVICES/sunheart-brain/curator/liveness_status.py`
- `SERVICES/sunheart-brain/curator/jobs/digest.py`
- `SERVICES/sunheart-brain/curator/jobs/test_digest_liveness.py`
- `SERVICES/sunheart-brain/curator/live_system_status.py`
- `SERVICES/sunheart-brain/curator/test_live_system_status.py`
- `tools/hot_memory/scanners/signal_scanner.py`
- `tools/hot_memory/test_signal_scanner.py`
- `core/BUILD/specs/SPEC_d117_post-merge-liveness-probe-auto-d.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d117_post-merge-liveness-probe-auto-d.result.md`
- `docs/codex/HANDOFF.md`

## Tests
- `python3 -B -m unittest tools.liveness.test_probe tools.build_loop.test_liveness_probe tools.hot_memory.test_signal_scanner`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator/jobs -p 'test_digest_liveness.py'`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_live_system_status.py'`
- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile ...`
- `python3 -B -m tools.liveness.probe --repo-root . --declaration $'liveness:\n  - type: file\n    path: core/BUILD/specs/SPEC_d117_post-merge-liveness-probe-auto-d.md' --spec-id SPEC_d117_post-merge-liveness-probe-auto-d --decision-id d117 --branch build/SPEC_d117_post-merge-liveness-probe-auto-d --ops-ledger /tmp/d117-liveness-ops.jsonl`
- `git diff --check`

## Risks
- Live systemd, live Postgres table probes, and live endpoint/port checks were not exercised in this sandbox.
- External endpoint checks default to disabled unless `LIVENESS_ALLOW_EXTERNAL_ENDPOINTS=1`, so externally hosted liveness should either use a local health proxy or explicitly opt in.
- Legacy `liveness_check` commands still exist as fallback for d115 compatibility; new specs should prefer typed `liveness:` declarations.

## Rollback
Revert the listed files. Runtime-only rollback is `LIVENESS_PROBE_DISABLE=1`; the digest/HOT_STATE/status additions are read-only summaries from the ops ledger.

## Intent solved
Post-merge status is no longer inferred from merge success; each merge can prove and log whether the expected runtime state is live, partial/dead, or merely planned.

## Downstream intent unlocked
The autonomous loop can close merged-but-not-live gaps in the next cycle via activation follow-up specs, while morning surfaces report what is actually running.
