# SPEC_d187_build-loop-rework-path-for-chan Result

## Status
Done in working tree. Do not push or merge from this session.

## Summary
Closed the `build_status=changes` dead-end in `tools/build_loop/server_build_loop.sh`.

- Added a self-migrating `rework_attempts INTEGER DEFAULT 0` column path.
- Added a dedicated changes rework pass before backlog merging.
- Re-drives Codex on the existing build branch/worktree using the independent reviewer findings as the revision prompt.
- Re-runs the independent AI review after each rework attempt.
- Caps changes rework at `REWORK_ATTEMPT_LIMIT=2`; after that, the decision is marked `blocked` and surfaced to Ember/James/council instead of looping.
- Keeps `changes` excluded from the fresh pending-build selector and removes it from backlog merge eligibility.
- Removes the linked-worktree side channel that could merge unknown `build/*` branches outside the DB `built` status.

## Files Changed
- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/test_changes_rework_loop.py`
- `tools/build_loop/test_build_state.py`
- `core/BUILD/specs/SPEC_d187_build-loop-rework-path-for-chan.md`
- `core/BUILD/results/SPEC_d187_build-loop-rework-path-for-chan.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests
- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -B -m unittest tools.build_loop.test_changes_rework_loop tools.build_loop.test_revision_agent tools.build_loop.test_parallel_build_loop tools.build_loop.test_build_state tools.build_loop.test_build_orphan_reaper tools.build_loop.test_auto_merge_governance` (25 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/test_changes_rework_loop.py tools/build_loop/test_build_state.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d187-registry.json`
- `git diff --check`

## Risks
- Live proof against a real server-162 `changes` row was not run in this sandbox.
- The rework pass depends on the existing review artifact path for best feedback extraction; if the file is missing, it falls back to the review command output available in the run.
- A rework that cannot reopen its branch worktree is held as `changes` unless the branch itself is missing, which blocks immediately.

## Rollback
Revert this branch. Runtime mitigation without code rollback is `CHANGES_REWORK_MAX=1` to slow the pass or `REWORK_ATTEMPT_LIMIT=1` to block faster; full disable can be done by reverting the rework pass.

## Intent Solved
`build_status=changes` is no longer a terminal P14 state with no exit.

## Downstream Intent Unlocked
Flagged autonomous builds can advance to `built`/merge or `blocked` within two rework cycles, giving James/Ember an explicit surface instead of abandoned branches.
