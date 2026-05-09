# Parallel-session collision prevention

## What this is

A pair of Claude Code hooks that prevent the bug we hit in commit `8b8a64de`:
session A leaves uncommitted edits in a hot SSOT file → session B does its
own edit and commits → A's unfinished work lands inside B's commit, with B's
commit message under-describing what's actually inside.

## How it works

1. **`hot-files.txt`** lists the files that need protection (currently
   `core/STATE/NOW.md`, `core/STATE/AI_GOALS.md`, etc.).
2. **`check-collision.sh`** is a `PreToolUse` hook on `Edit|Write|MultiEdit`.
   Before a write to a hot file, it checks `git status` for that file:
   - **Clean** → allow.
   - **Dirty AND this session's edit log mentions it** → allow (own work).
   - **Dirty AND foreign** → exit 2, surface a blocking message with concrete
     options (wait, stash, commit, or explicit override).
3. **`log-edit.sh`** is a `PostToolUse` hook that appends each successful
   write of a hot file to `.claude/sessions/<session_id>/edited.txt`, so
   subsequent edits in the same session aren't false-flagged.

The session-id comes from the hook stdin JSON (`session_id` field).
Per-session state lives at `.claude/sessions/<session_id>/` and is gitignored.

## Maintenance

- **To protect a new file**: add a line to `hot-files.txt` and commit.
  Sibling sessions pick it up immediately.
- **To override a block**: the error message prints the exact command —
  append the path to your session's `edited.txt` and re-attempt.
- **To inspect**: `cat .claude/sessions/$YOUR_SESSION_ID/edited.txt`.

## Limits

- **Only protects Edit/Write/MultiEdit via Claude Code.** Bash redirects
  (`cat > NOW.md`) and external editors bypass the hook entirely.
- **No active locking.** This is opportunistic detection on edit, not a
  real mutex. If two sessions both open a clean file simultaneously and
  edit before either has committed, the second to write still bundles —
  but it'll see the warning if it edits *again* before the first commits.
- **Session-id alone, no heartbeat.** A crashed session's edit log lingers
  until manually cleaned. Low impact (just causes false self-allows on the
  same path), but worth knowing.

## Why not the existing `docs/coordination/scripts/session-claim.sh`?

That scaffold was 100+ scripts from the MISSION_CONTROL / GOD_MODE era.
Heavyweight resource-claim system designed for a different problem
(multi-agent task coordination), not file-edit collision. Wrong tool,
wrong fit.
