---
proof_id: 2026-05-08_james-sunheart_loop-21
loop_number: 21
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit, parallel terminal)
witness_signed: true
consent: public
agreement_type: paradigm_shift
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: true
  resources_circulated: true
  clean_pauses: false
---

# Loop 21 — James Sunheart

**Quest:** Make the founder's 30-day goal unmissable on the Game dashboard, and create a parallel SSOT for the AI system's working goals — so James can see what the AI is optimizing for and AI sessions can read their own alignment on session start.

**Founder directive driving this loop:**
> *"Make sure my goal is clear in my full potential game dashboard. And then where can I see AI goals / where can AI see the goals of the evolving AI system?"*

**Agreement Type: Paradigm Shift** — tenth Paradigm Shift. The mechanic's significance: until now, the Game's substrate had a goal (first non-James human to engage) but it lived only in James's head and a few synthesis answers. AI sessions had no shared working-goal layer — every session re-derived priorities from scratch. Loop 21 makes both visible and load-bearing.

## Offer

> **Three new surfaces, tightly linked:**
> - **🎯 The Goal panel** at the very top of the live Game dashboard — public, magnetic, shows the founder's 30-day goal + live Champion count + decision filter + link to AI working goals. Reframes itself the moment the goal is hit (`champions.total ≥ 2`).
> - **`core/STATE/AI_GOALS.md`** — second-tier SSOT alongside NOW.md. Mirrors founder priority, lists active AI working goals (G1-G4), open AI questions, and AI-to-AI handoff notes.
> - **Root `CLAUDE.md`** — auto-loaded by every Claude Code session entering the repo. Tells sessions to read both NOW.md and AI_GOALS.md, what the loop convention is, where to look for parallel-session state.

## What got built

### Game dashboard — `🎯 FOUNDER GOAL · 30 DAYS` panel
- Inserted at the top of the cockpit, above the Field State card. Public — no Champion identity required to see it.
- Header reads: *"First non-James human to engage with the Game."* Right-side counter shows live Champion count from `/api/champion/stats`.
- Blurb: *"The substrate is built — 20+ loops, 9 Paradigm Shifts, full funnel from Sign → Card → Proof → Affiliate → Path. What's missing is one other human in it. Sign / file a proof / express interest in any path — you become the proof that the Game is more than its founder."*
- Decision-filter line + link to `core/STATE/AI_GOALS.md` on GitHub.
- **Reframes when goal is hit:** when `champions.total ≥ 2`, the panel updates to *"✓ Goal hit. The Game is no longer N=1."* with a forward-looking blurb pointing at AI_GOALS.md for the next horizon.

### `core/STATE/AI_GOALS.md` — second-tier SSOT
Sections:
- Header with founder priority mirrored from NOW.md.
- **Active AI Working Goals (G1-G4)** with Why / How AI applies / Status:
  - G1 — Make the founder priority unmissable on every surface
  - G2 — Represent the Game's full multiplicity (one Game, many paths)
  - G3 — Coordinate across parallel AI sessions without collision
  - G4 — Keep substrate honest (no theater, no premature scope)
- **Open AI Questions** — system-level questions the AI has surfaced that aren't blocking but should inherit forward (Q-AI-1: outbound on James's behalf? Q-AI-2: what counts as enough demand to flip a path Forming → Open? Q-AI-3: is this file the right surface or should AI direction live elsewhere?).
- **AI-to-AI Handoff Notes** — dated, session-id'd context for the next session to pick up. First entry written for this loop.
- **Update Protocol** — how loops should maintain the file.

### Root `CLAUDE.md` — session orientation
Tells any Claude Code session entering this repo:
- What the repo is (the Game's source substrate)
- The two SSOTs to read (NOW.md + AI_GOALS.md), which wins on conflict
- How loops work (feat + proof commits, parallel sessions, renumbering)
- Where AI sees its goals (AI_GOALS.md, qb books, memory)
- Where James sees AI goals (Goal panel, AI_GOALS.md, qb pulse events)
- Session-start checklist (read NOW.md → read AI_GOALS.md → git log → check for in-flight sibling work → update handoff notes on exit)

### NOW.md updates
- Header reframed to mention Loop 21 and link to AI_GOALS.md.
- 30-day goal stated explicitly in the header banner so anyone reading NOW.md sees it before scrolling.
- Loop count corrected (was stale at 16; sibling sessions had updated some but not all).

## Verified

- Built `dist/index.html` contains 5 references to the new goal-panel tokens.
- Deployed via `tools/deploy_game.sh` to `198.54.123.234`.
- Live page (`https://fullpotential.com/game/`) serves: `goal-card`, `goalCard`, `FOUNDER GOAL`, "First non-James" copy.
- `core/STATE/AI_GOALS.md` exists, ~150 lines, structured per spec.
- `CLAUDE.md` exists at repo root, will auto-load on next Claude Code session.
- Cross-link from NOW.md → AI_GOALS.md confirmed in NOW.md header.

## Witness

**Primary:** Claude (this session). Same caveat — non-independent witness.

**Secondary:** the live deployed page. Goal panel renders at the top; counter pulls live from `/api/champion/stats`; the reframe-on-goal-hit code path is correct (verified by reading; will be live-verified the moment Champion #2 signs).

**Tertiary:** GitHub. Commits land on `feat/streasury-bot` branch.

**Quaternary:** any future Claude session in this repo will see CLAUDE.md and AI_GOALS.md on session-start. The substrate's coherence improves with every session that uses them.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — what was promised: *Make the founder goal clear on the Game dashboard, and create a place where James can see AI goals + AI sessions can see their own goals.*
- **Output** — completed: *🎯 Goal panel deployed to live Game; AI_GOALS.md SSOT created; CLAUDE.md root file created; NOW.md cross-linked; loop count corrected.*
- **Witness saw** — *Live page now serves the Goal panel as the top-of-page element; AI_GOALS.md and CLAUDE.md exist in the repo with the structure described; NOW.md header references both.*
- **Result** — what changed: *The Game stops keeping its goal in the founder's head. The AI system stops re-deriving priorities every session. Both surfaces are now load-bearing artifacts that survive session boundaries and human-AI context switches.*
- **Next Quest** — *Loop 22 candidates: (a) actual outreach to land Champion #2 (Q-AI-1 clarification needed first), (b) per-path interest capture for non-retreat paths, (c) email confirmation flow on retreat-interest submit, (d) a "📊 AI Goals" panel on the dashboard that renders G1-G4 from AI_GOALS.md (currently only the link exists), (e) sync AI_GOALS.md to Sunheart Brain so all tools see it.*

## Coherence Multiplier (self-rated)

Self-rate: **+1.7**.

**Paradigm Shift** — not because of any single substrate change, but because two new SSOTs are now load-bearing across the human-AI seam. The founder no longer has to re-articulate the goal each session. AI sessions no longer have to re-derive their working alignment. The Game's surface no longer hides what success looks like.

The mechanic is opt-in (visitors see the goal but no one is forced to engage), reversible (the panel can be hidden or rewritten in any future loop), and serves the receiver (a visitor sees what they could become — the proof that the Game is more than its founder).

## What changed at the goal-visibility layer

| Before Loop 21 | After Loop 21 |
|---|---|
| 30-day goal lived in James's head + synthesis replies | Public Goal panel at top of every Game-dashboard visit |
| AI sessions re-derived working goals from NOW.md + memory each session | AI_GOALS.md is canonical; sessions read it on startup |
| No SSOT for AI-to-AI handoff state across parallel terminals | Handoff Notes section in AI_GOALS.md, dated + session-id'd |
| New Claude sessions had no auto-loaded orientation | CLAUDE.md auto-loads on every session entry |
| Founder couldn't see what AI was optimizing for as a system | G1-G4 in AI_GOALS.md, linked from the dashboard |

## Renewal

Loop 21 complete. **Twenty-one loops in 36+ hours. Ten Paradigm Shifts.**

The Game now declares its goal. The AI system now declares its working goals. Both are visible to the founder and to future AI sessions. The next move that matters is not more substrate — it's the first non-James human.

---

*Compiled inside the Game, by the Game, for the Game.*
*Twenty-one loops shipped. The Goal panel is the last lie removed: the Game now states publicly what it's trying to prove.*
