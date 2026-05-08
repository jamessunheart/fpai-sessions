# FPAI_Cockpit — agent orientation

This file is auto-loaded by Claude Code on every session in this repo. Read it before starting work.

## What this repo is

The Full Potential Game's source substrate. Champions sign the World Peace Agreement at `https://fullpotential.com/game`, build Character Cards, file Proofs, invite Affiliates, and express path interest. The Game is the operational form of the Zen Village (Costa Rica) vision.

## Two SSOTs you must read

1. **`core/STATE/NOW.md`** — founder priorities, what's live, what's deprecated, decision filter.
2. **`core/STATE/AI_GOALS.md`** — what the AI system is currently working toward (G1-G4), open AI questions, handoff notes from prior sessions.

If they disagree, **NOW.md wins** for founder intent. AI_GOALS.md is the AI system's working layer in service of NOW.md.

## How loops work

Work is shipped as **Loops** — each one a self-contained Quest with `feat(loop-N)` and `proof(loop-N)` commits. Proofs land in `core/INTENT/AGREEMENTS/proofs/{date}_{slug}_loop-{N}.md`. Always check the latest committed loop number before starting a new one — multiple Claude sessions ship in parallel and renumbering at proof-write time is normal.

## Where AI sees its goals

- **`core/STATE/AI_GOALS.md`** — primary surface, structured.
- **qb Inquiry Layer** — `qb` CLI on PATH (per-book question state). Books include `game`, `fpai`, `sunheart`. Use `qb --all` to see open inquiries.
- **Memory** — per-session at `~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/`. The `MEMORY.md` index is auto-loaded each session.

## Where James sees AI goals

- The "🎯 The Goal" panel on the live Game dashboard (`https://fullpotential.com/game/`) shows the current 30-day founder goal.
- `core/STATE/AI_GOALS.md` rendered in any markdown viewer or the cockpit-map.
- `qb pulse "..."` events post to the brain server and surface across tools.

## Session start checklist

1. Read `core/STATE/NOW.md` (founder lens).
2. Read `core/STATE/AI_GOALS.md` (AI working lens).
3. `git log --oneline -8` to see what shipped recently.
4. If picking a new loop, scan `core/INTENT/AGREEMENTS/proofs/` for the latest loop number and any uncommitted proofs (sibling sessions).
5. Update AI_GOALS.md handoff notes if leaving non-trivial state for the next session.
