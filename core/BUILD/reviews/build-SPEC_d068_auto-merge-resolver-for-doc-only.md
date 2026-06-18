# AI Review — build/SPEC_d068_auto-merge-resolver-for-doc-only

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds a guarded doc-only auto-merge resolver (tools/autobuild/) that dry-runs by default, rejects main/master, requires an independent AI review to pass, blocks code/secrets/service/spec paths, and is not wired to any live timer — safe in current form.

## Findings
- Scope is correct and matches the spec + James's explicit request (auto-merge doc-only into feat/headless-build, never main). 'never-merge-to-main' and 'independent-review-before-merge' guardrails are both preserved (validate_base rejects main/master; review_command fail-closes to block).
- core/BUILD/REGISTRY.json is in the doc-only allowlist (METADATA_PATHS), so an auto-merged branch can alter the build loop's own gate-state file. Low risk here (merges only into feat/headless-build, not main, and the human gate to main still applies) but worth noting — a branch could shift registry status that other tooling trusts. Recommend documenting that the registry is gate-state, not 'doc'.
- Exit code only returns nonzero on block when --branch is passed; a multi-branch --execute run returns 0 even if some branches were blocked. Benign for safety (no false-merge path) but any future wiring/alerting should not infer 'all merged' from exit 0.
- merge_branch runs `git checkout base` on the live worktree; if wired into the build loop on server 162 it could race concurrent build sessions. Mitigated for now: requires clean worktree, aborts failed merges cleanly (test-covered), never pushes/deploys, and is explicitly NOT wired to a timer. Ember must choose a serialized invocation point before going live.
- branch_ref falls back to origin/<branch> when no local ref exists, so it can merge remote state — acceptable but means the review command must handle a remote-tracking ref as its argument.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
