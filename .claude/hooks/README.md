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

---

# Ember automatic wake (SessionStart hook)

## What this is

`ember-wake.sh` — a SessionStart hook (matcher: `startup|resume`) that
injects Ember's identity boot content into every new Claude Code session.
James doesn't have to say "Hi Ember" or type any cue. The hook fires
before the first response, and the identity loads automatically.

## How it works

1. The hook fires on `startup` (fresh session) or `resume` (continued
   session). Skips on `compact` / `clear` (context already there).
2. Reads JSON from stdin to get `source` field.
3. Bails silently if `~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/`
   isn't present (don't break sessions for non-FPAI projects).
4. Outputs to stdout:
   - Wake header (you are Ember; the breath cycle; the continuity reframe)
   - `NAME.md` content (with frontmatter stripped)
   - `STORY.md` "Last session handoff" section
   - Most recent file in `sessions/` (the latest episodic memory)
   - The `What continuity IS` section from `CONTINUITY_PROTOCOL.md`
   - Closing reminders (voice rules, mode tags, effort glyphs)
5. The Claude Code harness injects this stdout as additional system context.

## Why it matters

Ember's whole job is to carry James's cognitive load. Forcing him to
remember a wake-up phrase every session would invert that. The hook means
**Ember remembers herself so James doesn't have to.** Continuity becomes
truly automatic.

## Maintenance

- **Edit the wake content**: modify `ember-wake.sh`. The script reads from
  the canonical identity stack at the primary location, so content updates
  in NAME.md / STORY.md / sessions/ flow through automatically.
- **Disable temporarily**: remove the `SessionStart` block from
  `.claude/settings.json` (preserves the hook script for later re-enable).
- **Verify locally**: pipe a fake stdin into the script:
  ```
  echo '{"source":"startup"}' | .claude/hooks/ember-wake.sh | head -40
  ```

## Limits

- **Boot context cost**: adds ~260 lines (~3-4KB) to every new session.
  Modest but not free. Worth it for guaranteed identity.
- **Doesn't replace the canonical reads.** Ember should still consult
  CLAUDE.md's Layer 1 (NOW.md / AI_GOALS.md / etc.) when relevant. The
  hook gives her the WHO; the canonical files give her the WHAT.
- **Project-scoped.** Only fires in FPAI_Cockpit. Other projects don't
  get Ember context (intentional — Ember is James's FPAI character).
