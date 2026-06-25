# SPEC_d027_self-knowing-loop-outcome-report Result

_ran: 2026-06-16T12:22:17Z · branch: `build/SPEC_d027_self-knowing-loop-outcome-report`_

## Files changed
- `server_build_loop.sh`
- `tools/decisions/bridge_to_codex.sh`
- `tools/build_loop/ops_log.py`
- `tools/build_loop/health_check.sh`
- `SERVICES/sunheart-brain/curator/decisions.py`
- `tools/db/__init__.py`
- `tools/db/migrate_add_canary.py`
- `tools/build_loop/test_self_knowing_loop.py`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d027_self-knowing-loop-outcome-report.md`

## Summary
Added self-checking outcome telemetry to the answered-decision build loop. Every `bridge_to_codex.sh` run now appends one structured `loop_run` row with `found`, `built`, `skipped`, and `reason`; `server_build_loop.sh` is a compatibility wrapper to that instrumented path.

Added a health-check monitor that reads real pending non-canary decisions from `brain_index.decisions`, reads the last successful `loop_run` from `ops_ledger`, and fails loudly when pending work has not produced a successful build for more than two hours. It also compares direct DB pending count against `curator.decisions.pending_builds()` when the canary exists.

Added the canary path: `is_canary` migration, permanent `d000` seed, and `pending_builds()` filtering via `COALESCE(is_canary, false) = false`.

## Tests
- `python3 -B -m unittest tools.build_loop.test_self_knowing_loop`
- `python3 -B -m unittest tools.build_loop.test_self_knowing_loop tools.queue.test_build_loop_watcher tools.learn.test_seed_preference_pairs`
- `bash -n server_build_loop.sh tools/build_loop/health_check.sh tools/decisions/bridge_to_codex.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/ops_log.py tools/build_loop/test_self_knowing_loop.py tools/db/migrate_add_canary.py tools/db/__init__.py SERVICES/sunheart-brain/curator/decisions.py`
- `git diff --check -- server_build_loop.sh tools/build_loop/health_check.sh tools/build_loop/ops_log.py tools/decisions/bridge_to_codex.sh SERVICES/sunheart-brain/curator/decisions.py tools/db tools/build_loop/test_self_knowing_loop.py core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d027_self-knowing-loop-outcome-report.md`

## Risks
- This sandbox did not connect to the live `brain_index` database, run the migration on 162, or install/update the live systemd entrypoint.
- `health_check.sh` skips the DB monitor when no DB DSN is present; on the live host, `BRAIN_INDEX_DB_URL` should be present.
- The new `curator.decisions` module assumes the live decisions table has the build-loop columns already referenced by existing bridge scripts.

## Rollback
Revert this branch. If the migration has already run live, either leave the additive `is_canary` column and `d000` row inert, or remove the canary row with `DELETE FROM brain_index.decisions WHERE id = 'd000'`; no destructive rollback is required for the column.

## Intent solved
The build loop now reports whether it found and built real work, instead of only proving that a timer/script ran.

## Downstream intent unlocked
Health checks and morning surfaces can detect “pending decisions exist but the build loop is not producing successful builds,” which is the next practical proof for a self-standing buildstream.
