# SPEC_d068_auto-merge-resolver-for-doc-only Result

- Status: done / independently AI-reviewed / awaiting merge review
- Branch: `build/SPEC_d068_auto-merge-resolver-for-doc-only`
- Base: `feat/headless-build`
- Files changed:
  - `tools/autobuild/doc_only_merge_resolver.py`
  - `tools/autobuild/test_doc_only_merge_resolver.py`
  - `core/BUILD/specs/SPEC_d068_auto-merge-resolver-for-doc-only.md`
  - `core/BUILD/results/SPEC_d068_auto-merge-resolver-for-doc-only.result.md`
  - `core/BUILD/REGISTRY.json`
  - `docs/codex/HANDOFF.md`

## Summary

Added a guarded doc-only auto-merge resolver in the non-protected autobuild lane. The resolver scans `core/BUILD/REGISTRY.json` for `done` builds with `tests_passed=true`, rejects `main`/`master` as merge targets, skips unavailable or already-merged branches, blocks non-doc changes, reruns the independent AI review command immediately before merge, and aborts cleanly if a merge fails.

Dry-run is the default. `--execute` performs local merges into `feat/headless-build` only; it never pushes, deploys, opens PRs, or targets main.

The doc-only allowlist is intentionally narrow: text docs under `docs/` and `core/STATE/`, plus build-loop result/review/done/session-note metadata and `core/BUILD/REGISTRY.json`. Build intake surfaces (`core/BUILD/specs/`, `core/BUILD/intents/`) and code/runtime paths are blocked.

## Tests

- `python3 -B -m unittest tools.autobuild.test_doc_only_merge_resolver` (10 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/autobuild/doc_only_merge_resolver.py tools/autobuild/test_doc_only_merge_resolver.py`
- `bash -n tools/merge/process_merge_requests.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`
- `python3 tools/autobuild/doc_only_merge_resolver.py --json` (real-registry dry run; no merge executed)

## Independent Review

Independent subagent review initially found blockers: target base could be set to `main`, failed merges could leave a conflicted worktree, `tools/merge/` is protected, and build specs/intents were too broad for doc-only. Fixed all four. Blocker-only re-review found no remaining P1/P2 blockers and independently reran the focused tests, py_compile, registry JSON check, diff check, and `--base main` fail-closed smoke.

## Risks

- This branch does not wire a live timer or service. Ember/server must explicitly choose where to invoke `tools/autobuild/doc_only_merge_resolver.py --execute`.
- Independent review still depends on the configured review command, defaulting to `tools/merge/ai_review.py`; if that command cannot run, the branch is blocked instead of merged.
- This resolver intentionally will not auto-merge doc-like build intake files under `core/BUILD/specs/` or `core/BUILD/intents/`.

## Rollback

Revert the two `tools/autobuild/` files and remove this result/registry/handoff entry. If Ember has wired invocation later, disable that invocation or set the invoking job to omit `--execute`.

## Intent

- Intent solved: AI-approved doc-only branches can be resolved by a guarded repo tool instead of requiring James to run shell merge commands.
- Downstream intent unlocked: Ember/server can wire the resolver into the build loop for low-risk documentation completions while code/runtime branches remain on the normal review/merge path.
