# AI Review — build/SPEC_d047_intent-protocol-extractor-v0-1

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds an intent-protocol extractor that turns explicit James-stated rules into durable memory/protocols files; in-scope, well-guarded (no push, no cron install, kill switch), but auto-commits LLM-extracted rules to the shared memory repo — worth a human gate at deploy.

## Findings
- Branch correctly targets feat/headless-build, never main. SQL against brain_index.tg_messages is parameterized (no injection) and filters private_flag IS NOT TRUE (privacy-respecting). No secrets, money, or prod-server writes in this branch — the cron is a reviewed artifact only, not installed, and deploy/link is explicitly left to a human decision. Good guardrails: INTENT_PROTOCOL_EXTRACTOR_DISABLE kill switch, --dry-run, no git push (local commit only).
- MEMORY-TOUCHING / behavior-shaping (the main residual risk): validate_protocols only gates on rule length>=8 and slug uniqueness — there is NO semantic check before an LLM-extracted 'rule' is written and (with --commit, as the cron uses) auto-committed to the shared memory/protocols repo that every surface reads. A hallucinated or misattributed protocol could silently shift system behavior. Recommend a human-review gate (or surface-before-sync) before committed protocol files propagate via the 162 SSOT sync. Mitigated for now because cron install + deploy are explicitly human-gated.
- Independent merge review could not be completed in the sandbox (git index.lock read-only FS; claude -p API socket failure). This branch was NOT independently diff-reviewed by the standard gate — this review is the substitute. Confirm the live proof run (3 expected clarification files created+committed) before trusting the path end-to-end.
- Minor: DEFAULT_MEMORY_REPO/runtime path is /opt/fpai/build while the repo artifact lives in the cockpit worktree — ensure the deployed script and the memory repo it commits to are the intended targets, since a wrong path would commit protocols into the wrong git repo.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
