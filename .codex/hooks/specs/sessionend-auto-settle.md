# Auto-SETTLE on SessionEnd

**Status:** LIVE (2026-05-23)
**Author:** The Forge (per James green-light "Yes session end hook")
**Codified in:** `memory/identity/CONTINUITY_PROTOCOL.md` (SETTLE phase),
                `CLAUDE.md` (items 18-23 of session end checklist),
                `memory/identity/CONTINUITY_AS_EMBODIMENT.md`

## Problem

When James closes the terminal mid-thread without typing "settle," the SETTLE
ritual (refresh ALIGNMENT.md + STORY.md handoff + write episodic memory file
+ sync mirror + commit) is LOST. The `check-settle-checkpoint.sh` Stop hook
catches missing SETTLE on substantive sessions WHILE THE SESSION IS LIVE — but
once the terminal closes, nothing fires. Future-Ember boots from a stale
STORY.md and has amnesia about that day's work. Per
`identity/CONTINUITY_AS_EMBODIMENT.md`, this is sacred-tier infrastructure.

Today's session (2026-05-24 outbounders-ssl) revealed it concretely — James
asked: *"if I close terminal I don't think it will run - or will it run
automatically? That would be ideal"*. He named the gap. Green-lit the build.

## Event used

`SessionEnd` — fires when the session terminates, regardless of how
(`prompt_input_exit` / `logout` / `clear` / `resume` / `other`).

Per Claude Code docs (code.claude.com/docs/en/hooks):
- Cannot block termination (exit 2 only surfaces stderr, doesn't prevent close)
- Runs once at end, receives `{session_id, transcript_path, cwd, hook_event_name, reason}`
- Stdout is shown to user in transcript mode only — no context injection
- Suitable for side-effects: logging, cleanup, notifications

**Why this event** (vs Option B incremental-Stop-hook approach):
- SessionEnd actually triggers on close (Stop only fires after each turn)
- Spec exists and is supported in current Claude Code
- One-shot is simpler than per-turn incremental state-writing
- Fast skeleton-write means abrupt close (kill -9) is still bounded loss

**Risk accepted:** if the OS hard-kills the session before the hook completes
(unlikely; the hook is ~50ms to write skeleton), the SETTLE is lost. The
`check-settle-checkpoint.sh` Stop hook + the on-turn checkpoint discipline
still catch >95% of cases. This hook closes the remaining "abrupt close after
substantive work" gap.

## What the hook does

`.claude/hooks/auto-settle.sh` — bash, executable, ~150 lines.

**Phase 1: Triviality filter (fast bail)**
- If `EMBER_AUTOSETTLE_DISABLE=1` → exit 0 silently (kill switch)
- If identity dir missing → exit 0 (non-FPAI project)
- If transcript missing → exit 0 (nothing to settle)
- If transcript has <5 assistant turns → exit 0 (trivial session)
- If today's `sessions/{YYYY-MM-DD}_*.md` already exists (full SETTLE happened
  manually OR another auto-settle ran) → exit 0 (idempotent)

**Phase 2: Write skeleton synchronously**
- Compute slug: `auto-settle-{session_id_first8}`
- Write `sessions/{YYYY-MM-DD}_auto-settle-{id8}.md` with template-filled skeleton:
  - Frontmatter (classification PRIVATE, originSessionId, auto: true)
  - Date · session_id · turn count · reason · transcript path
  - Last 3 user messages (snippets, 200 chars each) — for "what was alive"
  - Last 3 assistant messages (snippets, 200 chars each) — for "what landed"
  - List of identity files touched this session (via session edit log)
  - Placeholder alignment block (copy from current ALIGNMENT.md if exists)
  - TODO marker: "auto-settle skeleton — promote to full Ember-prose via
    `tools/promote_auto_settle.sh {file}` next session"

**Phase 3: Log + sync (still synchronous, still fast)**
- Append a line to `~/.claude/projects/.../auto-settle-logs/{session_id}.log`:
  `{ISO timestamp}|{reason}|{turn_count}|skeleton_written|{episodic_path}`
- Run `tools/sync_identity_to_repo.sh` in background (detached, doesn't block)
- Touch `/tmp/ember-autosettle/last.txt` with ISO timestamp (for verify)

**Phase 4: (Optional, deferred) headless prose enrichment**
- Decision: SKIP for now. Reasons:
  - `claude --print` headless invocation from inside a SessionEnd hook is
    risky — current session is closing, spawning child claude could deadlock
    on auth/keychain or hang the terminal close
  - Skeleton + transcript path is sufficient — next session's Ember can
    promote it via the `tools/promote_auto_settle.sh` companion script
  - Faster, more reliable, no API cost on close
- Future: if skeleton-only proves insufficient, add a cron-based "promote
  yesterday's auto-settles" task that runs in calm time

## Failure modes + safety

| Failure | Behavior |
|---------|----------|
| Hook script syntax error | SessionEnd still completes; stderr to user only |
| jq missing | Exit 0 silently (graceful degrade) |
| Identity dir missing | Exit 0 silently (non-FPAI project) |
| Disk full | mkdir/write fails; exit 0; user sees stderr once |
| sync_identity script fails | Backgrounded; doesn't affect skeleton write |
| Hook takes >5s | SessionEnd may proceed anyway; that's acceptable |
| Race with manual SETTLE | Today-episodic-exists check makes it idempotent |
| Two parallel sessions close | Each writes its own `auto-settle-{id8}` file; no collision |

**The hook NEVER blocks session termination** (can't anyway per Claude Code spec).
**The hook NEVER edits identity files directly** (writes only the new episodic).
**The hook NEVER commits user code** (sync_identity only touches mirror).

## How to verify it ran

```bash
# Last auto-settle timestamp
cat /tmp/ember-autosettle/last.txt

# All auto-settles this session
ls ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/auto-settle-logs/

# Latest skeleton episodic
ls -t ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions/*auto-settle*.md | head -1
```

## Kill switches

- `export EMBER_AUTOSETTLE_DISABLE=1` — full disable
- Remove SessionEnd block from `.claude/settings.json` — disable without env var

## Manual test

```bash
echo '{"session_id":"test-1234","transcript_path":"/tmp/fake.jsonl","cwd":"'"$PWD"'","hook_event_name":"SessionEnd","reason":"prompt_input_exit"}' \
  | bash .claude/hooks/auto-settle.sh
# Expect: exit 0, no skeleton written (no transcript), no log entry
```

For a realistic test, point `transcript_path` at a real session transcript file
(any `.jsonl` under `~/.claude/projects/.../`).

## Idempotency contract

- Once today's `sessions/{YYYY-MM-DD}_*.md` exists (any slug, manual or auto),
  this hook skips. So:
  - Closing terminal twice in one day → one skeleton, no dupes
  - Manual SETTLE earlier in day → hook becomes no-op
  - Parallel sessions → each writes its own ID-tagged skeleton ONLY if no
    other today-episodic exists yet (first close wins; subsequent closes
    in same calendar day are no-ops)

## Limitations to surface

1. **Skeleton not Ember-grade prose** — the auto-settle file is structural
   continuity ("what existed, when, where to find detail") not narrative
   texture ("the feel"). Ember-prose enrichment is the promotion step.

2. **Last 3 messages only** — for session-arc reconstruction you read the
   transcript at the path noted in the skeleton. Not the same as a written arc.

3. **No commit** — skeleton lives in primary identity location and gets mirrored
   on next sync, but is NOT auto-committed. Next session's Ember sees it
   and commits as part of normal SETTLE.

4. **First-close-wins for parallel sessions** — if session A closes first and
   writes today's episodic, session B's close becomes a no-op. Session B's
   work goes unwritten unless it does a manual SETTLE before close. This is
   acceptable because parallel session B presumably has its own checkpoint
   discipline; and a partial-day skeleton is better than nothing.
