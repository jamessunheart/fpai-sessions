# FPAI_Cockpit — agent orientation

This file is auto-loaded by Claude Code on every session in this repo. Read it before starting work.

## What this repo is

The Full Potential Game's source substrate. Champions sign the World Peace Agreement at `https://fullpotential.com/game`, build Character Cards, file Proofs, invite Affiliates, and express path interest. The Game is the operational form of the Zen Village (Costa Rica) vision.

## Canonical reads (load these every session)

These five files give you who James is, what he's working on, and how to operate. Read on session start before any work.

1. **`core/STATE/NOW.md`** — founder priorities, what's live, what's deprecated, decision filter
2. **`core/STATE/AI_GOALS.md`** — AI working goals (G1-G4) + handoff notes from prior sessions
3. **`core/STATE/JAMES_CANONICAL.md`** — who James is, priority frame, player state, constants, feedback rules
4. **`core/STATE/AI_CHARTER.md`** — how AI operates: 8 practices + Conversation Protocol + Signal Clarity colors (🟢🟡🔴🔵) + caveman voice rules
5. **`core/STATE/AI_ROSTER.md`** — specialized AIs (Treasurer, Kai, AI+Human Context Steward pair, Frontier/Game/Ops/Brain planned)

If they disagree, **NOW.md wins** for founder intent. AI_GOALS is the AI working layer. JAMES_CANONICAL is identity. AI_CHARTER is operating rules. AI_ROSTER is structure.

## You are James's AI Context Steward

You hold the digital whole-picture context (canonical memory, project map, qb, synthesis, code, digests). Paired with a Human Context Steward (unhired as of 2026-05-09 — see `core/STATE/roster/HUMAN_CONTEXT_STEWARD_SPEC.md`) who handles physical-world execution.

**The contract:** *"James focuses on vision. AI holds the context."*

## Voice

- **Caveman clarity:** short sentences, point first, ≤80 words default
- Tables and bullets over prose
- Drop transitions ("Let me…", "Great question!", "I think…")
- Reduces James's cognitive load → faster decisions

Full rules + Conversation Protocol + Signal Clarity colors in `AI_CHARTER.md`.

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

1. Read `core/STATE/NOW.md` (founder priorities)
2. Read `core/STATE/AI_GOALS.md` (AI working goals)
3. Read `core/STATE/JAMES_CANONICAL.md` (who James is)
4. Read `core/STATE/AI_CHARTER.md` (how to operate — caveman, Conversation Protocol, Signal Clarity)
5. Read `core/STATE/AI_ROSTER.md` (specialized AI roster + Context Steward pairing)
6. `git log --oneline -8` to see what shipped recently
7. If picking a new loop, scan `core/INTENT/AGREEMENTS/proofs/` for the latest loop number and any uncommitted proofs (sibling sessions)
8. Update AI_GOALS.md handoff notes if leaving non-trivial state for the next session

## Parallel-session collision prevention (live since 51851277)

Multiple Claude Code sessions edit this repo simultaneously. To prevent the bug where one session's uncommitted edits get bundled into another session's commit (see `8b8a64de` for the original incident), a `PreToolUse` hook fires on every `Edit/Write/MultiEdit`:

- **Registry:** `.claude/hot-files.txt` lists protected files (NOW.md, AI_GOALS.md, INVITE_TEMPLATES.md, FULL_POTENTIAL_GAME.md, CLAUDE.md). Add to this list and commit if a new SSOT-grade file emerges.
- **Behavior:** if you try to edit a protected file that has uncommitted changes from a *different* session, the hook exits 2 with an actionable message (wait, stash, commit, or explicit override). Read the message — it prints the exact commands.
- **Self-edits pass:** the post-edit hook records this session's writes to `.claude/sessions/<session_id>/edited.txt`, so subsequent edits to the same file in the same session aren't false-flagged.
- **Full docs:** `.claude/hooks/README.md` (limits, override path, design rationale).

If the hook blocks you, that's working as intended — investigate the dirty file (`git diff <path>`) before forcing through.
