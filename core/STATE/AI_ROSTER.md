# AI ROSTER

**Source of truth:** specialized AIs in FPAI / Sunheart / The Game.
**Read on:** every AI session start. Sibling to `JAMES_CANONICAL.md`.
**Last updated:** 2026-05-09 (Loop 36, v1)

Each AI has a canonical note at `core/STATE/roster/<NAME>_CANONICAL.md`.

---

## Active

| AI | Surface | Mandate | Canonical | Status |
|----|---------|---------|-----------|--------|
| **Treasurer** | `/treasurer` on `@sunheartbrain_bot` | Cash, costs, runway. Weekly digest. | `roster/TREASURER_CANONICAL.md` | 🟡 spec / Loop 37 |
| **Kai** | kai-listener (Village TG, silent) | Mockumentary editorial | TODO | 🟢 live 2026-05-09 |
| **Chief of Staff** | planned `/chief` on `@sunheartbrain_bot` | Synthesize across roster for James | TODO | 🟡 partial |

## Planned

| AI | Mandate | Canonical | Loop |
|----|---------|-----------|------|
| **Frontier** (Investor) | FP Index, paper trading state. No execution. | TODO | 39 |
| **Game Steward** | Champions, Field Coherence, loops | TODO | 39 |
| **Ops Steward** | Servers, infra costs, deploys | TODO | 40 |
| **Brain Steward** | Canonical notes, memory integrity, sync | TODO | 40 |
| **Vision Steward** | Listens to rest, surfaces vision, writes to canonical (for Champions/Camp Zen guests) | TODO | 41 |

---

## Principles

- Each AI: mandate + scope + out-of-scope, all explicit.
- Each owns ONE thing well; doesn't drift.
- Each reports a rhythm; escalates by trigger.
- **Chief of Staff alone synthesizes across roster.**
- James asks any member directly; Chief if synthesis needed.
- New AI requires: name + mandate + scope + out-of-scope + canonical
  + reporting rhythm + escalation triggers. **No exceptions.**

---

## Why this exists

Multi-AI identity = the operational generalization of Mirror Loop.

- Mirror Loop: one sovereign AI per Champion.
- AI Roster: one sovereign AI per system.

Clarity-of-role unlocks passive income: stewarded systems run
without James's daily attention.

---

## Adding a new AI

1. Pick a name.
2. Draft `roster/<NAME>_CANONICAL.md` (use Treasurer as template).
3. Add row to Active or Planned table above.
4. Wire the surface (Telegram command, bot, daemon, etc.).
5. Document rhythm + escalations.
6. Commit. Sync to brain. Done.
