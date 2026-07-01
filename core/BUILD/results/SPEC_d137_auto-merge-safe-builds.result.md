# SPEC_d137_auto-merge-safe-builds Result

- Status: done in working tree / awaiting independent AI review + merge
- Branch: `build/SPEC_d137_auto-merge-safe-builds`
- Base: `feat/headless-build`

## Summary

Changed server build-loop governance so only independent-review `APPROVE`
builds enter the auto-merge path. Protected-path review blocks still surface as
hard stops. Review results that remain flagged after the bounded revision-agent
passes are now held for manual review instead of being silently auto-merged as
`auto-merged-flagged`.

Approved builds that hit real merge conflicts still surface as merge conflicts,
so the conflict path remains separate from the review-held path.

## Files changed

- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/test_auto_merge_governance.py`
- `tools/build_loop/test_revision_agent.py`
- `core/BUILD/specs/SPEC_d137_auto-merge-safe-builds.md`
- `core/BUILD/results/SPEC_d137_auto-merge-safe-builds.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.build_loop.test_auto_merge_governance tools.build_loop.test_revision_agent tools.build_loop.test_liveness_probe` (14 OK)
- `bash -n tools/build_loop/server_build_loop.sh`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/test_auto_merge_governance.py tools/build_loop/test_revision_agent.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d137-registry.json`
- `git diff --check`
- `git diff --no-index --check /dev/null <new-file>` for each new d137 file

## Review / Commit

- Local commit attempt failed because the shared git worktree index is read-only:
  `Unable to create .../.git/worktrees/SPEC_d137_auto-merge-safe-builds/index.lock`.
- Best-effort local `claude -p --effort high` review over a generated
  working-tree diff timed out after 120 seconds with no output. Independent AI
  review remains a pre-merge gate.

## Risks

- This intentionally makes still-flagged non-protected builds wait for manual
  review after two revision attempts. That can slow some reversible builds, but
  it matches d137's stricter "AI-approved low-risk" auto-merge boundary.
- No live server build-loop run, merge, push, deploy, secrets, outreach, or
  money movement was performed.

## Rollback

Revert the listed files. Runtime effect reverts to the previous behavior where
still-flagged non-protected builds could be silently auto-merged after revision
attempts.

## Intent

- Intent solved: trivial low-risk builds keep auto-merging after independent
  approval, while review-flagged/risky/irreversible cases surface honestly
  instead of landing silently.
- Downstream intent unlocked: James's merge surface can shrink to real risk,
  irreversibility, protected-path changes, and true merge conflicts.
