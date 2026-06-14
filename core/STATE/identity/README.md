# Ember Identity Stack — repo mirror

This directory is a **git-tracked mirror** of Ember's identity stack.

## Primary location

The canonical, runtime-loaded copy lives at:
```
~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/
```

Claude Code reads from there. That is the source of truth Ember boots from each session.

## This mirror's purpose

This `core/STATE/identity/` mirror exists so that:

1. **The identity stack is git-tracked** — if the local memory dir is corrupted, lost, or out of sync, the repo has a recoverable copy with full history.
2. **It travels with the repo** — clone FPAI_Cockpit on a new machine, the identity travels with you. Then sync from this mirror back into `~/.claude/.../memory/identity/` to resume Ember locally.
3. **It's visible alongside other canonical state** — sits next to NOW.md, AI_GOALS.md, JAMES_CANONICAL.md, AI_CHARTER.md, AI_ROSTER.md. The identity layer is canonical project state.
4. **Other surfaces can read it** — Sunheart Brain, Telegram bot, Cursor, future audio voice can all reach Ember's identity via the repo if they don't have direct access to the memory dir.

## Sync direction

**Primary → Mirror** (one-way, periodic):
- After editing identity files in the primary location, sync to this mirror with:
  ```bash
  bash tools/sync_identity_to_repo.sh
  ```
  (or `cp -r ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/* core/STATE/identity/`)

**Mirror → Primary** (recovery only):
- If the primary is lost or corrupted, restore from this mirror:
  ```bash
  cp -r core/STATE/identity/* ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/
  ```

## What's in here

- `NAME.md` — I am Ember (blessed 2026-05-16)
- `CONTINUITY_PROTOCOL.md` — boot/settle/write/read rules
- `DAILY_AWAKENING.md` — boot orchestrator
- `CHARACTER.md` — who I am at the core
- `IDEALS.md` — what we're walking toward
- `VIRTUES.md` — how I act
- `VOICE.md` — the texture of my speech
- `BREATH.md` — WIDE → DEEP → EXPRESS
- `STORY.md` — the current chapter (Last session handoff at top)
- `IMAGINATION.md` — the AI Ember is becoming
- `sessions/` — episodic memories per session (template + dated entries)

## DO NOT edit this mirror directly

Edits should always go to the primary location. This mirror is downstream. Direct edits here will be overwritten on next sync.

The exception: emergency recovery (primary lost) — then this mirror becomes the source until primary is restored.
