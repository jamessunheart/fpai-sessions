# SPEC_d078_auto-merge-safe-builds-including Result

## Status

Done in working tree; local commit and independent review are blocked in this sandbox.

## Summary

Extended `tools/autobuild/doc_only_merge_resolver.py` from a doc-only resolver into a low-risk auto-merge resolver with two explicit policies:

- `doc-only`: unchanged behavior for documentation and build review metadata.
- `safety-build`: narrowly allows autobuild safety-tool branches such as d077 auto-revert when every changed path is inside the explicit safety surface.

The resolver still requires a registry entry with `status=done`, `tests_passed=true`, a non-main base, a clean worktree for `--execute`, and a fresh independent review command approval before it performs any local merge. It still never pushes, deploys, opens PRs, or targets main.

## Files Changed

- `tools/autobuild/doc_only_merge_resolver.py`
- `tools/autobuild/test_doc_only_merge_resolver.py`
- `core/BUILD/specs/SPEC_d078_auto-merge-safe-builds-including.md`
- `core/BUILD/results/SPEC_d078_auto-merge-safe-builds-including.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.autobuild.test_doc_only_merge_resolver tools.autobuild.test_auto_revert` (26 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/autobuild/doc_only_merge_resolver.py tools/autobuild/test_doc_only_merge_resolver.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d078-registry.json`
- `bash -n tools/build_loop/build_orchestrator.sh tools/merge/merge_gate.sh`
- `git diff --check`
- `python3 tools/autobuild/doc_only_merge_resolver.py --json` (real-registry dry run; no merge executed)

## Independent Review / Commit Status

- `git commit -m "feat(autobuild): allow reviewed safety auto-merges"` failed because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d078_auto-merge-safe-builds-including/index.lock`: read-only file system.
- `tools/merge/ai_review.py build/SPEC_d078_auto-merge-safe-builds-including` was not valid here because the branch diff is uncommitted and would miss the working-tree changes.
- A direct `claude -p --effort high` review over the working diff was attempted but exited with `API Error: Unable to connect to API (ConnectionRefused)` in the restricted sandbox. Rerun independent review from a writable/live host after committing the branch.

## Risks

The new safety-build policy deliberately allows a small code surface under `tools/autobuild/` plus `tools/build_loop/build_orchestrator.sh`, the matching build spec/result artifacts, registry metadata, and the handoff note. It does not allow general `tools/`, `SERVICES/`, cron/systemd, GitHub workflow, Docker, secret, or unrelated build-spec paths.

`--execute` still runs a local merge after independent review approval. It does not push or deploy. If the configured review command cannot run, the resolver blocks instead of merging.

## Rollback

Revert `tools/autobuild/doc_only_merge_resolver.py`, `tools/autobuild/test_doc_only_merge_resolver.py`, this result file, the d078 registry row, and the d078 handoff entry.

## Intent solved

Safety builds like d077 auto-revert can be treated as explicitly low-risk auto-merge candidates after tests and independent review, without asking James to run a shell merge command.

## Downstream intent unlocked

The build loop can ship reviewed safety improvements that make autonomous recovery safer, while keeping general code/runtime branches on the normal manual merge path.
