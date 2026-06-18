# AI Review — build/SPEC_d077_auto-revert-on-break

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds a local-only auto-revert guard that resets a failed build worktree to feat/headless-build and writes failed-build reports; no push/merge/deploy/secrets, protects main/master, well-tested (22 tests) — safe given the isolated-worktree assumption.

## Findings
- Sharp edge (by design, verify isolation): on failure the orchestrator runs auto_revert with --execute --allow-dirty, which triggers `git reset --hard` + `git clean -fd` in --repo-root "$wt". This is destructive and only safe if $wt is always a genuinely isolated build worktree, never the main checkout. The diff does not show how $wt is created; confirm it can never resolve to $ROOT or the main feat/headless-build checkout (which holds the many untracked review files in git status).
- PROTECTED_BRANCHES = {main, master} does not include feat/headless-build. If auto_revert were ever pointed at the main checkout (on feat/headless-build), reset would be a near-noop but `git clean -fd` would still wipe untracked files. Consider refusing to run when repo_root equals the main checkout, or guarding on a worktree-path allowlist.
- Minor: failed diff captured via `git diff --binary` in text mode (subprocess text=True) may corrupt true-binary blobs in the artifact; diagnostic-only, acceptable. dt.datetime.utcnow() is deprecated; cosmetic.
- Re-runs merge_gate.sh as the check command (it already failed once upstream); assumes merge_gate is side-effect-free/read-only — confirm that holds, else double-invocation could have effects.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
