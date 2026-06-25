# SPEC_d125_build-claude-code-corrections-ca Result

Status: done in working tree / awaiting merge review
Branch: `build/SPEC_d125_build-claude-code-corrections-ca`
Date: 2026-06-25

## Summary

Added a Claude Code `UserPromptSubmit` correction capture hook. The hook reads James's prompt from `$CLAUDE_USER_PROMPT` or Claude hook JSON stdin, detects d125 correction phrases plus the existing Telegram correction shapes, reads the latest Claude Code assistant/Ember turn from `brain_index.thread`, and appends a correction pair to `brain_index.corrections` with `bot_turn_id = NULL`.

The shell hook is non-blocking: all failures are swallowed and return `0`, so Claude Code prompt submission is never stopped by missing DB credentials, unavailable psycopg, or live schema issues.

## Files Changed

- `.claude/settings.json`
- `tools/continuity/detect_correction.py`
- `tools/continuity/detect_correction_hook.sh`
- `tools/continuity/test_detect_correction.py`
- `core/BUILD/specs/SPEC_d125_build-claude-code-corrections-ca.md`
- `core/BUILD/results/SPEC_d125_build-claude-code-corrections-ca.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Proof

Focused tests prove:

- d125 explicit and implicit correction phrases are detected.
- ordinary questions are ignored.
- env prompt input takes precedence and JSON stdin fallback works.
- correction capture queries `brain_index.thread` for `surface = 'claude_code'` and assistant/Ember roles.
- writes use `brain_index.corrections` with `bot_turn_id = NULL`.
- no write occurs without a correction signal or without a prior Claude Code assistant turn.
- the shell hook exits `0` for both non-correction prompts and correction-shaped prompts when no live DB is available.

## Tests

- `python3 -B -m unittest tools.continuity.test_detect_correction` (5 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/continuity/detect_correction.py tools/continuity/test_detect_correction.py`
- `bash -n tools/continuity/detect_correction_hook.sh`
- `python3 -m json.tool .claude/settings.json`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `printf '{"prompt":"What is the next build?"}' | CLAUDE_PROJECT_DIR="$PWD" tools/continuity/detect_correction_hook.sh` (rc 0)
- `printf '{"prompt":"Actually, capture this correction."}' | env -u BRAIN_INDEX_DB_URL CLAUDE_PROJECT_DIR="$PWD" CLAUDE_SESSION_ID=d125-smoke tools/continuity/detect_correction_hook.sh` (rc 0)
- `git diff --check`

## Risks

- Live Postgres was not written in this sandbox. The live proof still needs James/Ember to send one harmless Claude Code correction after merge and confirm `brain_index.corrections` row count increases.
- The live `brain_index.thread` role has varied across artifacts (`assistant` in d125 spec, `ember` in current `thread.py`); the hook accepts both to avoid missing the last Claude Code assistant turn.
- This captures only when `brain_index.thread` already has a prior Claude Code assistant turn. Laptop UserPromptSubmit thread append remains the separate gate named in the spec.

## Rollback

Remove the `tools/continuity/detect_correction_hook.sh` command from `.claude/settings.json`, then revert the d125 files. Runtime side effects are append-only correction rows; no service is installed or started by this build.

## Intent

Intent solved: Claude Code correction turns can feed `brain_index.corrections` instead of leaving post-June-22 James corrections invisible to the learning loop.

Downstream intent unlocked: the L2 learning/dataset path can learn from James's current primary surface, once the live Claude Code thread append gate is installed and a real correction proof row lands.
