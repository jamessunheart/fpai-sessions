# AI Review — build/SPEC_d094_wire-the-forge-as-pre-build-scou

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds a fail-open, non-blocking pre-build Forge scout that asks `claude -p` for reuse/library hints and appends a bounded report to specs; no money/prod/identity/secrets/main touched, guardrails intact.

## Findings
- Spec content is passed to claude only via stdin, not interpolated into the `bash -c "$CLAUDE_CMD"` command string, so no command injection from spec text; CLAUDE_CMD is operator-env controlled — acceptable.
- Behavior note (not a blocker): the scout mutates the spec file in the working tree (appends `## Forge Scout Report`) before Codex builds, so the report will get committed with the build branch — this is within spec intent but means specs are no longer pristine post-loop.
- New behavior: orchestrator now fires one live `claude -p` call per PENDING spec each loop. Consistent with existing $0-marginal subscription-CLI pattern and timeout-bounded (30s, fail-open), so within cost guardrails.
- Duplicate-append protection, FORGE_SCOUT_DISABLE/ENABLED kill switches, and fail-open JSONL logging are all present and tested (6 tests pass).

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
