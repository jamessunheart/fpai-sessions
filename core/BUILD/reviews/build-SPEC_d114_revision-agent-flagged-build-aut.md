# AI Review — build/SPEC_d114_revision-agent-flagged-build-aut

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds a bounded (max-2, kill-switchable) self-revision loop to the server build loop that re-runs the independent ai_review.py after each Codex repair pass; preserves the review gate and protected-path RC=2 hard stop, no money/secrets/prod/main touches — matches the spec and James's explicit ask.

## Findings
- Self-revision-then-silent-auto-merge widens what merges without a human: Codex (the build AI) repairs its own flagged build and an upgraded RC=0 flows straight into the existing auto-merge path. Mitigated because the independent ai_review.py re-runs each attempt and RC=2 protected blocks stay hard stops, but a reviewer that can be fooled twice now yields an auto-merge where it previously stalled for human attention.
- Tests are static string-contract assertions only (test_revision_agent.py greps the shell source); no live build-loop cycle, real Codex subprocess, or ai_review.py invocation was exercised — author acknowledges this. Control-flow regressions (e.g. RC not updating, loop not terminating) would not be caught by these tests.
- run_revision_agent_attempt runs `codex exec --full-auto` in the worktree but does not check/create `/opt/fpai-build/logs/`; if absent the redirect fails and the codex pass aborts with a non-fatal error. Low impact (re-review still runs) but worth confirming the dir exists on host 162.
- review_file_for_branch assumes ai_review.py writes to core/BUILD/reviews/<branch>.md; if the path/format drifts, findings silently fall back to the raw $REVIEW stdout — acceptable degradation, but the revision prompt quality then depends on an unverified file path.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
