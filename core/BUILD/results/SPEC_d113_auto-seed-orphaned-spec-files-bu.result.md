# SPEC_d113_auto-seed-orphaned-spec-files-bu Result

## Status
Done in working tree; awaiting review/merge.

## Files changed
- `tools/build_loop/seed_orphaned_specs.py`
- `tools/build_loop/test_seed_orphaned_specs.py`
- `tools/build_loop/server_build_loop.sh`
- `core/BUILD/specs/SPEC_d113_auto-seed-orphaned-spec-files-bu.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`
- `core/BUILD/results/SPEC_d113_auto-seed-orphaned-spec-files-bu.result.md`

## Summary
Added a build-loop preflight that scans `core/BUILD/specs/SPEC_dNNN*.md` before `curator.decisions pending-builds`, skips specs with result files or existing `brain_index.decisions.id = dNNN` rows, and seeds missing rows as `status='answered'`, `needs_build=true`, `spec_written=false` using the original `dNNN` id and full spec body.

The server loop calls the helper non-fatally so a DB/import problem cannot halt the build loop. `ORPHAN_SPEC_SEED_DISABLE=1` disables the preflight.

## Tests
- `python3 -B -m unittest tools.build_loop.test_seed_orphaned_specs`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/seed_orphaned_specs.py tools/build_loop/test_seed_orphaned_specs.py`
- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `ORPHAN_SPEC_SEED_DISABLE=1 python3 -B tools/build_loop/seed_orphaned_specs.py --repo .`
- `git diff --check`

## Risks
Live DB seeding was not run in this sandbox. The helper assumes `brain_index.decisions.id` accepts explicit `dNNN` values and has an id conflict target, matching the existing server loop's `dNNN` contract. If live schema has drifted, the helper logs a warning and the server loop continues.

No deploy, push, merge, secret access, outreach, public send, or money movement occurred.

## Rollback
Revert the listed files. Runtime-only rollback is `ORPHAN_SPEC_SEED_DISABLE=1`.

## Intent solved
Orphaned `SPEC_dNNN` files no longer sit invisible to the decision-driven server build loop.

## Downstream intent unlocked
The autonomous build loop can recover from a dropped spec artifact by rehydrating the missing decision row before reading pending builds.
