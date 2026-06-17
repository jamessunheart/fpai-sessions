# SPEC_d077_auto-revert-on-break Result

- Status: done / independently AI-reviewed / awaiting merge review
- Branch: `build/SPEC_d077_auto-revert-on-break`
- Base: `feat/headless-build`

## Summary

Added a repo-local auto-revert guard for failed build verification. `tools/autobuild/auto_revert.py` runs an explicit check command, blocks protected branches, refuses dirty worktrees unless explicitly allowed for isolated build worktrees, preserves failed heads under `refs/fpai-auto-revert/<report-id>`, writes failed diff artifacts plus JSON/Markdown reports, resets to the known-good ref on failed verification, and verifies the post-reset HEAD and clean state before reporting `reverted`.

The build orchestrator now invokes this guard only after merge-gate failure, targeting the isolated build worktree with `--repo-root "$wt"` and resetting that failed build branch to `feat/headless-build` while still counting the build as failed for review.

## Tests

- `python3 -B -m unittest tools.autobuild.test_auto_revert tools.autobuild.test_doc_only_merge_resolver` (22 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/autobuild/auto_revert.py tools/autobuild/test_auto_revert.py`
- `bash -n tools/build_loop/build_orchestrator.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d077-registry.json`
- `git diff --check`

## Independent Review

Completed by subagent. Initial review found blockers in orchestrator worktree targeting, failed-head preservation, and post-reset verification. Fixes landed with regressions. A second review found report-ID collision risk; fixed with microsecond/PID/UUID IDs and a uniqueness regression. Final blocker-only re-review found no remaining P1/P2 blockers.

## Risks

`--allow-dirty` enables `git clean -fd` after `git reset --hard`; it is intended only for isolated generated build worktrees. The orchestrator passes `--repo-root "$wt"` to keep that destructive cleanup out of the main checkout. No push, merge, production deploy, secrets access, outreach send, money movement, timer install, or live service mutation was performed.

## Rollback

Revert `tools/autobuild/auto_revert.py`, `tools/autobuild/test_auto_revert.py`, and the d077 block in `tools/build_loop/build_orchestrator.sh`; remove this result file, the d077 registry row, and the handoff entry. Generated runtime reports can be deleted from `core/BUILD/reports/auto_revert/`, and preserved failed refs can be removed with `git update-ref -d refs/fpai-auto-revert/<report-id>` after review.

## Intent Solved

Build-loop failures now have a local automatic rollback path instead of leaving failed generated branches sitting as silent broken state.

## Downstream Intent Unlocked

The autonomous build loop can surface a concrete failed-build report to James/Ember while restoring the build worktree to the last known good base, making later self-healing and rebuild specs safer.
