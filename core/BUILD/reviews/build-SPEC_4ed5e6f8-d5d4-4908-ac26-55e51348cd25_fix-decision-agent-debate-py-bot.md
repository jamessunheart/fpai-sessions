# AI Review — build/SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot

**Verdict:** APPROVE · **Risk:** low

**Summary:** Hardens council debate.py voice wrappers (claude/codex/glm) to fail transparently and log isolated voice errors to ops-ledger; read-only, in-scope, no prod/money/secrets/main touched.

## Findings
- Minor: gpt_voice/run_claude_json now log raw CLI stderr/stdout (truncated 200ch) to the ops-ledger via _ops — if an auth failure echoes a token in stderr it could be persisted locally. Low risk (local ledger only), but consider scrubbing known secret patterns before logging.
- _resolve_cli falls back to a possibly-nonexistent configured_path when shutil.which returns None; subprocess then raises FileNotFoundError. Handled (caught+logged in gpt_voice, propagates to debate_error in run_claude_json), so behavior is transparent — not a bug, just noting the path.
- Tests correctly inject a runner and never execute live CLIs; logic for wrapped-JSON parse, non-zero exit, and auxiliary voice isolation is covered.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
