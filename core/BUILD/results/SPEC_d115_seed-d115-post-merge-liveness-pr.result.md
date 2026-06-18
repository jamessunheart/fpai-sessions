# SPEC_d115_seed-d115-post-merge-liveness-pr result

## Status
Done in working tree. Do not push or merge from this session.

## Files changed
- `SERVICES/sunheart-brain/index/schema.sql`
- `SERVICES/sunheart-brain/curator/decisions.py`
- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/test_liveness_probe.py`
- `tools/hot_memory/scanners/signal_scanner.py`
- `tools/hot_memory/test_signal_scanner.py`
- `core/BUILD/specs/SPEC_d115_seed-d115-post-merge-liveness-pr.md`
- `core/BUILD/specs/SPEC_d116_retroactive-liveness-audit-d001-d092.md`
- `core/BUILD/results/SPEC_d115_seed-d115-post-merge-liveness-pr.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added optional `brain_index.decisions.liveness_check` support for decision rows and threaded it through `curator.decisions pending-builds`.

After an auto-merge, `tools/build_loop/server_build_loop.sh` now runs the decision's `liveness_check` shell command when present, after activation scripts. Passing checks write an ops-ledger row with event `liveness:pass`; failing checks write `liveness:fail`, save a bounded log under `/opt/fpai-build/logs/`, and queue a follow-up repair spec through `curator.decisions seed`. Runtime kill switch: `LIVENESS_PROBE_DISABLE=1`; timeout override: `LIVENESS_PROBE_TIMEOUT`.

HOT_STATE signal scanning now reads recent `liveness:fail` rows from ops_ledger and promotes them as high-weight signal facts. Seeded `SPEC_d116_retroactive-liveness-audit-d001-d092.md` so the existing orphan-spec seeder can queue the retroactive merged-vs-live audit after d115 lands.

## Tests
- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -B -m unittest tools.build_loop.test_liveness_probe tools.build_loop.test_revision_agent`
- `python3 -B -m unittest tools.hot_memory.test_signal_scanner tools.hot_memory.test_hot_memory`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/decisions.py tools/hot_memory/scanners/signal_scanner.py tools/build_loop/test_liveness_probe.py tools/hot_memory/test_signal_scanner.py`
- `python3 -B -m unittest tools.build_loop.test_seed_orphaned_specs tools.build_loop.test_liveness_probe tools.build_loop.test_revision_agent tools.hot_memory.test_signal_scanner tools.hot_memory.test_hot_memory`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks
The sandbox did not run a live server build-loop merge, execute a real liveness command against server services, or write the live Postgres schema. The decision CLI attempts an idempotent `ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness_check TEXT`; if live DB permissions reject DDL, `pending-builds` falls back to `NULL::text AS liveness_check` and probes will not run until Ember applies the schema.

`liveness_check` is an operator-provided shell command. The build loop bounds it with a timeout and repo working directory, but the command itself must remain scoped and non-secret.

## Rollback
Revert the listed files. Runtime-only rollback is `LIVENESS_PROBE_DISABLE=1`; existing merge behavior then continues without running liveness probes.

## Intent solved
Future auto-merged decisions can prove merged means live by carrying an explicit post-merge liveness command.

## Downstream intent unlocked
d116 can audit d001-d092 for retroactive live/not-live state using the same liveness vocabulary and queue focused repairs for gaps.
