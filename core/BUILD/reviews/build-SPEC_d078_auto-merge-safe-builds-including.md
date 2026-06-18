# AI Review — build/SPEC_d078_auto-merge-safe-builds-including

**Verdict:** APPROVE · **Risk:** med

**Summary:** Extends the doc-only auto-merge resolver with a narrow, well-tested 'safety-build' policy for autobuild tooling; bounded (non-main, no push/deploy, review-gated, manual --execute) but now allows the loop's own guardrail code to be auto-merged.

## Findings
- Verified hard boundaries hold: validate_base/branch_ref/eligible_entries still refuse main/master; merge_branch does a LOCAL --no-ff merge only — no push, deploy, or PR. No money/secrets/identity/memory touched.
- Scope expansion is explicit and conservatively tested: negative tests confirm tools/merge/merge_gate.sh, general tools/, other build specs, and core/STATE json stay blocked. classify_policy falls through doc-only → safety-build → blocked correctly.
- RECURSIVE-SELF-MODIFICATION SURFACE (watch): the safety-build policy now makes tools/autobuild/* AND tools/build_loop/build_orchestrator.sh auto-mergeable into feat/headless-build — i.e. the loop's own merge/revert/orchestration guardrail code can be merged after only an AI self-review (default tools/merge/ai_review.py). A buggy/weakening change to those files could be auto-merged. Acceptable only because --execute is gated on independent-review approval and merges non-main locally.
- NOT wired into the autonomous loop: build_orchestrator.sh's own AUTO_MERGE path is separate and unchanged; the resolver remains a manually-invoked tool. Recommend it stays manual-invoke and is never cron/loop-wired to run --execute without a human gate.
- d078 is self-referential — under its new policy the d078 branch itself qualifies as safety-build; this is the intended self-merge, still subject to the independent review gate, so acceptable but should be approved by a review host that actually runs the gate (the sandbox commit/review was blocked, per the result file).

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
