# SPEC_d150_swarm-verified-wire-post-merge Result

## Status
Done in working tree / awaiting review + merge.

## Summary
Wired `tools/build_loop/post_merge_reality_check.py` to a dedicated daily systemd timer. The reviewed unit artifacts live at `core/BUILD/cron/fpai-post-merge-reality.{service,timer}` and install after merge to `/etc/systemd/system/fpai-post-merge-reality.{service,timer}` via `core/BUILD/activate/SPEC_d150_swarm-verified-wire-post-merge.sh`.

The timer runs daily at 03:30 UTC with `Persistent=true`, loads the brain curator environment, uses the brain venv when available, appends the checker's `post_merge_reality` ops-ledger summary rows with `merged_dead` counts, and keeps the existing `POST_MERGE_REALITY_CHECK_DISABLE=1` kill switch. The broader build-loop health pulse no longer owns this cadence, avoiding duplicate daily runs.

## Tests
- `python3 -B -m unittest tools.build_loop.test_post_merge_reality_check tools.build_loop.test_liveness_probe tools.build_loop.test_feature_outcome tools.liveness.test_probe`
- `bash -n tools/build_loop/server_build_loop.sh core/BUILD/activate/SPEC_d150_swarm-verified-wire-post-merge.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/post_merge_reality_check.py tools/build_loop/test_post_merge_reality_check.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d150-registry.json`
- `systemd-analyze verify core/BUILD/cron/fpai-post-merge-reality.service core/BUILD/cron/fpai-post-merge-reality.timer` (exit 0; sandbox printed host DBus/snapd warnings)
- `git diff --check`

## Risks
This sandbox did not install or start the live timer. The activation script performs the live `/etc/systemd/system` copy and `systemctl enable --now` only after merge. The first live timer run depends on the target host having `/etc/sh-brain/curator.env`, the brain venv or `/usr/bin/python3`, DB connectivity, and write access to `/opt/fpai-build/ops_ledger.jsonl`.

## Rollback
Runtime rollback: `systemctl disable --now fpai-post-merge-reality.timer`. Optional soft kill: set `POST_MERGE_REALITY_CHECK_DISABLE=1` in the service environment or create `/opt/fpai-build/.post_merge_reality_disabled`. Code rollback: revert this branch.

## Intent solved
d150 gives the merged != live gate an explicit daily live timer instead of hiding it inside the broader build-loop health pulse.

## Downstream intent unlocked
After merge and activation, ops-ledger `post_merge_reality` rows can be monitored as a stable daily proof stream, with `merged_dead` counts available for repair prioritization.
