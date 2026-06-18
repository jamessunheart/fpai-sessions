# AI Review — build/SPEC_d053_blueprint-weakness-auditor-tool

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds two read-only scanner agents (Blueprint Weakness Auditor + Tool Scout) that emit review-gated signal files under core/BUILD/signals/; no money/prod/identity/secrets touched, branches off feat/headless-build not main, all proposals needs_review=true/safe_auto=false.

## Findings
- No guardrail bypass or scope creep: cost cap (MAX_COST_USD=1.50) + FORBIDDEN_ACTION_RE fail-closed validation + needs_review on every proposal; systemd timers are review-only artifacts, not installed.
- WATCH (not a blocker): load_provider_payload runs subprocess with shell=True from env var TOOL_SCOUT_PROVIDER_CMD — operator-configured only, not from untrusted input, but is a shell-injection surface if that env is ever populated from external data.
- WATCH (not a blocker): tool-scout systemd service runs --live, making unauthenticated GitHub API GETs on a timer; read-only and low-volume (6 reqs/run), fine, but confirm no token leak when Ember installs.
- WATCH: both agents append to the live /opt/fpai-build/ops_ledger.jsonl by default — consistent with existing loop pattern (append-only, low risk), gated behind --no-ledger for tests.
- Note: tool_scout.py run()/validate_payload()/dedupe were truncated in the provided diff and not fully verifiable here, but visible code is clean and 14 tests pass covering live-collector, cost-cap, and fail-closed paths.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
