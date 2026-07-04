# SPEC_d176_throughput-parallelize-the-buil Result

## Status
Done in working tree / awaiting review + merge.

## Files changed
- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/build_state.py`
- `tools/build_loop/test_parallel_build_loop.py`
- `core/BUILD/specs/SPEC_d176_throughput-parallelize-the-buil.md`
- `core/BUILD/results/SPEC_d176_throughput-parallelize-the-buil.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Parallelized the server build loop for answered pending builds.

- Added `BUILD_CONCURRENCY` with default `3`; setting `BUILD_CONCURRENCY=1` restores serial worker launch.
- Added atomic DB claim before worker spawn by setting `build_status='building'` and `build_branch`.
- Updated the shared pending-build predicate so claimed `building` rows are no longer returned by `pending-builds`.
- Moved each pending build into `process_pending_build`, spawned workers in the background, and throttled with `wait -n`.
- Added `BUILD_TIMEOUT` with default `90m` around the primary `codex exec` so a hung build releases its slot.
- Serialized approved new-build merges and backlog merges behind `flock -x` on `MERGE_LOCKFILE` while leaving build/review work concurrent.

## Tests
- `python3 -B -m unittest tools.build_loop.test_parallel_build_loop tools.build_loop.test_build_state tools.build_loop.test_auto_merge_governance tools.build_loop.test_build_orphan_reaper` (16 OK)
- `bash -n tools/build_loop/server_build_loop.sh tools/build_loop/run_codex.sh tools/build_loop/build_orchestrator.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/build_state.py tools/build_loop/test_parallel_build_loop.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d176-registry-building.json`
- `git diff --check`

## Proof
Static regression tests verify the default concurrency cap, background worker spawn, atomic claim before spawn, `building` exclusion from pending rows, Codex timeout path, and `flock` wrapping of both new-build and backlog merge paths.

## Risks
This sandbox did not run a live multi-Codex server loop with real DB rows, so process-level proof of two simultaneous `codex` processes remains a server-162 live acceptance check after merge. The parent process only knows worker launch count; per-worker successful merge/accounting remains in existing DB, ops-log, and build alert paths.

## Rollback
Set `BUILD_CONCURRENCY=1` for immediate serial behavior. Full code rollback is reverting this branch, which restores the original serial `while read` pending-build loop and removes the `building` pending predicate.
