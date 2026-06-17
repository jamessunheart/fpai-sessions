# SPEC_d075_versioned-merge-with-rollback Result

## Status

Done / independently AI-reviewed / awaiting protected-path human merge review.

## Files changed

- `tools/merge/pre_merge_snapshot.sh`
- `tools/merge/test_pre_merge_snapshot.sh`
- `tools/merge/merge_gate.sh`
- `tools/merge/test_merge_gate.sh`
- `tools/merge/process_merge_requests.sh`
- `tools/autobuild/doc_only_merge_resolver.py`
- `tools/autobuild/test_doc_only_merge_resolver.py`
- `core/BUILD/specs/SPEC_d075_versioned-merge-with-rollback.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`
- `core/BUILD/results/SPEC_d075_versioned-merge-with-rollback.result.md`

## Summary

Added a reusable pre-merge rollback snapshot helper that creates local numbered tags on the base branch before a merge. The default tag series is `fpai/pre-merge/0001`, `fpai/pre-merge/0002`, and so on. Re-running the helper for the same base SHA reuses the existing tag instead of minting duplicate versions.

Wired the helper into:

- `tools/merge/merge_gate.sh`, which now creates/verifies a snapshot before printing Ember's merge command and fails closed if the snapshot cannot be created.
- `tools/merge/process_merge_requests.sh`, which now snapshots after checkout/pull and before the phone-approved merge.
- `tools/autobuild/doc_only_merge_resolver.py`, which now snapshots immediately before executing its reviewed doc-only merge.

The manual gate no longer prints `git pull` after snapshot creation, because pulling after the snapshot could move the base away from the rollback point. If Ember needs to pull the base, the printed instruction now says to pull first and rerun the gate.

## Tests

- `bash tools/merge/test_pre_merge_snapshot.sh` — 4 passed.
- `bash tools/merge/test_merge_gate.sh` — 5 passed.
- `python3 -B -m unittest tools.autobuild.test_doc_only_merge_resolver` — 10 tests OK.
- `bash -n tools/merge/pre_merge_snapshot.sh tools/merge/merge_gate.sh tools/merge/process_merge_requests.sh tools/merge/test_pre_merge_snapshot.sh tools/merge/test_merge_gate.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/autobuild/doc_only_merge_resolver.py tools/autobuild/test_doc_only_merge_resolver.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Independent review

Completed by subagent. The first review found blockers in review bypass env handling, stale-base phone merges after failed `git pull`, and snapshot-skip env handling. Fixes removed the review/snapshot bypass env hooks, made the phone merge path fail closed on pull failure, and expanded the regression test to grep both merge scripts for bypass hooks. A final blocker-only re-review found no remaining P1/P2 blockers.

## Risks

This intentionally modifies `tools/merge/`, which is listed in `core/BUILD/PROTECTED_PATHS.txt`. That means the normal merge gate's protected-zone check should escalate this branch for James/Ember human-directed review rather than auto-merge it. The change is still scoped to local Git refs and merge instructions: it does not push tags, push branches, merge, deploy, touch secrets, move money, or send outreach.

Rollback tags are local unless Ember later chooses to push them. A local-only tag is enough for the host performing the merge to reset back to the last known-good base, but it is not a remote backup by itself.

## Rollback

Revert the listed files and remove the d075 registry, result, and handoff entries. If any local `fpai/pre-merge/NNNN` tags were created only for testing and should not be kept, delete the unwanted tag with `git tag -d <tag>` from the affected repository.

## Intent solved

Before reviewed merge paths change `feat/headless-build`, the current base commit now receives a numbered rollback tag.

## Downstream intent unlocked

Ember can merge approved build branches with a stable last-known-good ref for fast rollback if a build needs to be reverted after merge.
