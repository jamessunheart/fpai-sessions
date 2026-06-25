# SPEC d125 — Claude Code Corrections Capture

**Status:** QUEUED
**Stream:** Game/Intelligence
**Priority:** HIGH — closes the last gap in the corrections → L2 learning loop

## The gap

`corrections.py` reads from `brain_index.tg_messages` (Telegram only). James switched to
Claude Code as his primary surface on June 22. Every correction since then is invisible to
the learning loop. `brain_index.corrections` has only 5 rows, last on June 17.

## What to build

A `UserPromptSubmit` hook (`tools/continuity/detect_correction_hook.sh`) that:

1. Reads James's current message from `$CLAUDE_USER_PROMPT`
2. Checks for correction signal (same patterns as `corrections.py.detect_correction_signal()`):
   - explicit: "no", "wrong", "that's not right", "incorrect", "not what I meant"
   - implicit: "fix", "change", "instead", "actually"
3. If signal detected: reads last Ember turn from `brain_index.thread` (WHERE surface='claude_code' AND role='assistant', ORDER BY at DESC LIMIT 1)
4. Writes correction pair to `brain_index.corrections`:
   - `conversation_id`: `$CLAUDE_SESSION_ID`
   - `bot_turn_id`: NULL (Claude Code, no update_id)
   - `original_response`: last Ember turn text
   - `james_correction`: James's current message
5. Non-blocking: failure silently exits 0

## Wire into settings.json

Add to `UserPromptSubmit` hooks array in `.claude/settings.json`:
```json
{
  "type": "command",
  "command": "$CLAUDE_PROJECT_DIR/tools/continuity/detect_correction_hook.sh"
}
```

## Rollback

Remove from settings.json. No side effects — append-only to `brain_index.corrections`.

## Proof

After build: `SELECT COUNT(*) FROM brain_index.corrections` increases when James sends
a correction in Claude Code. Check `SELECT * FROM brain_index.corrections ORDER BY captured_at DESC LIMIT 5`.

## Dependencies

- `brain_index.thread` populated via `append_turn.sh` hook (requires James to install on laptop)
- `brain_index.corrections` table exists (confirmed, 5 rows as of June 17)
- `/opt/sh-brain-src/.venv/bin/python3` with psycopg available on 162

## Notes

On server 162, thread.py appends via `append_session_hook.sh` → `append_turn.sh`.
On laptop, James must install the UserPromptSubmit hook for `append_turn.sh`.
This spec covers the detection hook; thread availability is a separate gate.
