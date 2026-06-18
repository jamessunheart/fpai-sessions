# AI Review — build/SPEC_d067_auto-merge-resolver-for-doc-onl

**Verdict:** REQUEST_CHANGES · **Risk:** high

**Summary:** Doc-only auto-merge resolver is well-gated for code files but defaults its merge TARGET to `main` and auto-commits there autonomously, bypassing the system's hard 'never merge to main / human merges' guardrail.

## Findings
- CRITICAL: `tools/forge/auto_merge.sh` defaults `TARGET=main` and `build_orchestrator.sh` passes `AUTO_MERGE_TARGET=${BUILD_AUTO_MERGE_TARGET:-main}`. The resolver does `git checkout main` + `git merge --no-edit` with no human in the loop. This directly violates the canonical hard gate 'never merge to main · independent review before merge' (CLAUDE.md / kill-switches). The build loop's established BASE is feat/headless-build, never main. An autonomous AI loop landing commits on main is exactly the guardrail this system forbids — flag and hold regardless of what the spec text said.
- HIGH: doc-only filter only blocks `.py/.sh/.sql/.env`. It does NOT protect identity/memory/SSOT markdown — files like core/STATE/NOW.md, AI_GOALS.md, identity/*.md, or memory files are all `.md` and would pass as 'doc-only', allowing autonomous auto-merge of identity/memory/state. That touches the identity/memory hard boundary. The .claude/hot-files.txt protected set is not consulted.
- MED: `mark_ai_review_approved()` sets `ai_approved`/`risk` in the registry from a loose regex over the review markdown, and the same loop then trusts that flag to auto-merge — the build pipeline writes its own approval gate. AI approval should not be self-asserted by the orchestrator from text scraping; risk=low can be spoofed by review wording.
- LOW: in the orchestrator the merge runs from a worktree ($wt) context; auto_merge.sh checks out TARGET in $ROOT — verify the checkout/merge does not race the worktree state or leave the repo on `main` for subsequent loop iterations.
- Recommendation: default TARGET to feat/headless-build (never main), add an explicit deny-list for identity/memory/SSOT/hot-files paths even when doc-only, and keep main merges human-only.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
