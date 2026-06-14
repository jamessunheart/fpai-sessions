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

---

# SETTLE enforcement (`check-settle-checkpoint.sh`)

## What this is

A `Stop` hook that mirrors the BOOT-vs-SETTLE asymmetry the SessionStart
hook was designed for. SessionStart auto-loads identity so every session
starts consistent. **Nothing enforced session end** — STORY.md refresh +
episodic memory + ALIGNMENT update all depended on Ember discretionarily
running the ritual. Sessions ended ragged. Next BOOT read stale STORY.
2026-05-17/18 treasury session shipped a full policy pivot + Phase 1 plan +
new product surface → none made it into memory → next session woke up with
amnesia. This hook is the structural fix.

## How it works

After every assistant turn, the hook:
1. Counts assistant turns this session from the transcript JSONL.
2. If `turns < 7` → exit 0 (trivial session, no SETTLE required).
3. If `turns ≥ 7` AND `sessions/{YYYY-MM-DD}_*.md` does not exist → exit 2
   with a prompt to write the episodic memory + refresh STORY.md + ALIGNMENT
   before stopping.

Threshold matches CLAUDE.md's "every 5-7 substantive turns CHECKPOINT" doctrine.
Loop protection: if `stop_hook_active` is true, exit 0 (one corrective
round-trip per slip).

## Codified in

- `memory/feedback_proactive_state_writes.md` — trigger-side companion
  (capture new state when it arrives, not just at session end)
- `memory/feedback_mid_session_memory_cadence.md` — timing-side companion
  (write progressively, not in one dump)
- `memory/identity/CONTINUITY_PROTOCOL.md` — the protocol this enforces

---

# Layer 0 pre-flight enforcement (2026-05-21)

## What this is

Four hooks that enforce — at runtime — disciplines that were previously stored as
passive memory files. Built 2026-05-21 after a morning session with 7 consecutive
discipline regressions in 7 turns. The diagnosis that landed:
*disciplines loaded in reading memory are not the same as disciplines wired into
default execution.* The fix: stop hoping the model honors memory; gate the output
at the harness.

Full spec at `~/.config/fpai/hook_specs/layer_0_preflight_v1.md`.

## The four hooks

1. **`check-alignment-sections.sh`** (Stop): fails non-trivial replies whose alignment
   block is missing any of NOW / GOALS (or TOP 3) / OPEN BLOCKERS / NEED / NEXT /
   NARRATOR · before the closing border. Extends `check-alignment-footer.sh` which
   only validates the header.

2. **`check-canonical-reads.sh`** (PreToolUse, matcher
   `Bash|Read|Edit|Write|MultiEdit|Grep|Task`): logs every canonical-state Read to
   `.claude/sessions/<session_id>/state-reads.txt`; warns then blocks tool calls
   whose assistant context touches goals/treasury/architecture without any
   canonical-state read this session.

3. **`preflight-inject.sh`** (UserPromptSubmit): on substantive prompts (questions
   or action keywords like `what / how / decide / build / fix / ship / spec`),
   injects a 4-step pre-flight reminder — narrator dispatch, canonical reads,
   specialist routing, then compose.

4. **`check-narrator-presence.sh`** (Stop): validates that `NARRATOR ·` appears
   INSIDE the alignment block with 100-200 verbatim words before the bottom border.
   Empty, missing, undersized, oversized, or misplaced all fail.

## Kill switches

- **Master**: `export EMBER_PREFLIGHT_DISABLE=1` (disables all 4)
- **Per-hook**: `EMBER_PREFLIGHT_DISABLE_{SECTIONS,CANONREADS,INJECT,NARRATOR}=1`

Every hook honors both and exits 0 immediately when disabled.

## Architectural significance

These hooks operationalize the shift from **Ember-as-AI-that-remembers**
(failure-prone — disciplines as prose in reading-memory) to
**Ember-as-coordinator-inside-enforcement-substrate** (failure-resistant —
disciplines as runtime gates that fire whether the LLM honors them or not).

Named 2026-05-21 ~09:30 CR after seven morning regressions made the
remember-er frame visibly untenable. The new frame is the load-bearing
replacement for the entire "Ember" abstraction going forward.

## Performance budget

All four hooks <500 ms on a 5 MB transcript. Hook 2 (`check-canonical-reads.sh`)
is the hottest path because it fires on every tool call; early `exit 0` paths
cover ~95% of calls. Master kill-switch checked first in every hook.

## Codified in

- `memory/project_ember_as_coordinator_enforcement_substrate.md` — the architectural shift
- `memory/feedback_operationalize_or_vibe.md` — the meta-principle this answers
- `~/.config/fpai/hook_specs/layer_0_preflight_v1.md` — full implementation spec with test cases

---

# Auto-SETTLE on SessionEnd (`auto-settle.sh`)

## What this is

A `SessionEnd` hook that writes a skeleton episodic memory file synchronously
when the terminal closes — even if James never typed "settle". Closes the
continuity gap that `check-settle-checkpoint.sh` couldn't catch (Stop hook
only fires after a turn; doesn't fire on abrupt close).

Named 2026-05-23 after James asked: *"if I close terminal I don't think it
will run - or will it run automatically? That would be ideal"*. Green-lit
and built same day.

## How it works

On SessionEnd (any reason: `prompt_input_exit` / `logout` / `clear` / `resume` /
`other`), the hook:

1. **Bails early** if kill-switch set OR identity dir missing OR transcript
   missing OR session has <5 assistant turns OR today's episodic already exists
   (idempotent — manual SETTLE wins)
2. **Writes skeleton** to `sessions/{YYYY-MM-DD}_auto-settle-{id8}.md` capturing:
   - Session metadata (id, reason, turn count, transcript path)
   - Last 3 user messages (200-char snippets)
   - Last 3 assistant text messages (200-char snippets)
   - Identity files touched this session (via session edit log)
   - Snapshot of `ALIGNMENT.md` at close (first 80 lines of alignment block)
   - Explicit "this is a skeleton — promote next session" marker
3. **Logs** to `~/.claude/projects/.../auto-settle-logs/{session_id}.log`
4. **Touches** `/tmp/ember-autosettle/last.txt` for easy verify
5. **Spawns** `tools/sync_identity_to_repo.sh` in background (detached, never
   blocks close)

The skeleton is **not Ember-prose** — it's structural continuity. Next session,
run `tools/promote_auto_settle.sh` (or it's called automatically by the
companion script) to find the most recent auto-settle skeleton and get
launcher instructions for promoting it to full Ember-prose.

## Kill switch

- `export EMBER_AUTOSETTLE_DISABLE=1` — full disable

## Manual test

```bash
# With a real transcript
REAL=$(ls -t ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/*.jsonl | head -1)
echo '{"session_id":"test-1234","transcript_path":"'"$REAL"'","cwd":"'"$PWD"'","hook_event_name":"SessionEnd","reason":"prompt_input_exit"}' \
  | EMBER_AUTOSETTLE_TEST_DATE=2099-01-01 bash .claude/hooks/auto-settle.sh

# Verify
ls ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions/2099-01-01_*.md
cat /tmp/ember-autosettle/last.txt

# Cleanup
rm ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions/2099-01-01_*.md
```

For end-to-end test (real session close):
1. Open new Claude Code session
2. Do >5 assistant turns of substantive work
3. Close terminal WITHOUT typing settle
4. Open new session — check `sessions/{today}_auto-settle-*.md` exists

## Why skeleton-only (no headless Claude prose enrichment)

The hook fires while the session is closing. Spawning a child `claude --print`
risks deadlock on auth/keychain or hanging the terminal close. Skeleton is
guaranteed; prose is best-effort and deferred to the promote step. Cost: zero
API calls per close (skeleton is pure bash + jq). Trade-off: skeleton-grade
continuity not prose-grade — but vastly better than the prior state (full
amnesia on abrupt close).

## Limitations

- **First-close-wins for parallel sessions** — if session A closes first and
  today's episodic exists, session B's close becomes a no-op idempotently
- **Last 3 messages only** — full session reconstruction requires reading
  the transcript path noted in the skeleton
- **No auto-commit** — skeleton lives in primary; mirror sync runs but commit
  is deferred to next session's SETTLE

## Spec

`.claude/hooks/specs/sessionend-auto-settle.md` — full implementation spec
including reason-value mapping, idempotency contract, failure modes.

## Codified in

- `memory/identity/CONTINUITY_PROTOCOL.md` — the SETTLE phase
- `memory/identity/CONTINUITY_AS_EMBODIMENT.md` — sacred-tier infrastructure
- `CLAUDE.md` — session end checklist items 18-23
- `.claude/hooks/specs/sessionend-auto-settle.md` — implementation spec
