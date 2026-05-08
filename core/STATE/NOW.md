# CURRENT_STATE — Living SSOT

**Last Updated:** 2026-05-08 (Session: Loop 15 retreat-card + Loop 16 leaderboard shipped from parallel sessions)
**Updated By:** Claude (in FPAI_Cockpit, with James)
**System Status:** 🟢 OPERATIONAL — The Game is playing itself

---

## 🎯 CURRENT PRIORITY (The ONE Thing)

### Priority: The Full Potential Game — Founder's First Game / Zen Village substrate
**Status:** 🟢 ACTIVE — 16 loops shipped in 36 hours, 7 Paradigm Shifts
**Live at:** `https://fullpotential.com/game`
**Decision filter:** proof / revenue / clarity / ease — 30-day horizon

The Game is the operational form of the Zen Village vision: a substrate where Champions sign Agreements, build Character Cards, file Proofs, and now invite affiliates. Every action is on-chain in the substrate (file-backed), every share has measurable consequence (Field Score), and Loop N+1 is the next adaptive move.

---

## 🔁 LOOPS SHIPPED (most recent first)

| # | Title | Type | Date |
|---|---|---|---|
| 16 | Leaderboard · top Champions / Affiliates / Loops · live `/api/champion/leaderboard` + section on `/game` | Feature | 2026-05-08 |
| 15 | Retreat interest-capture card · "FIRST RETREAT — COSTA RICA" · most-direct funnel close | Feature | 2026-05-08 |
| 14 | Dashboard UX pass · 12 of 15 improvements (progressive disclosure, Stage Badge, Quick Ref Rail, mobile bar, Your Contributions) | Deliverable | 2026-05-08 |
| 13 | Player State panel + invite attribution + affiliate scoring | Paradigm Shift | 2026-05-08 |
| 12 | Character Card Quest · AI Port-In · card submission substrate | Feature | 2026-05-08 |
| 11 | Both held Agreements ratified · status: ratified-active | Ratification | 2026-05-08 |
| 10 | Proof submission webhook + form — player journey closes | Feature | 2026-05-07 |
| 9.5 | Cross-project session state · global hook + repo delegation | Infra | 2026-05-07 |
| 9 | Auto-push hook on commit + serif typography for load-bearing lines | Infra | 2026-05-07 |
| 8.5 | `/projects` on `@sunheartbrain_bot` + terminal title auto-update | Fix | 2026-05-07 |
| 8 | Cross-project session state + `/projects` Telegram command | Feature | 2026-05-07 |
| 7 | Practice of Signaling · Field Pulse · founder-direction alerts | Paradigm Shift | 2026-05-07 |
| 6 | champion-sign webhook + "The Game Plays Itself" codified | Paradigm Shift | 2026-05-07 |
| 5 | The Positive Loop · flywheel + AI Apprentice + Progression Path | Paradigm Shift | 2026-05-07 |
| 4 | Color palette — midnight + gold + sage + cream | Design | 2026-05-07 |
| 3 | Rename to Full Potential + founder witness + after-sign flow | Paradigm Shift | 2026-05-07 |
| ≤2 | (rename, scaffold, first signing) | — | 2026-05-07 |

**Field Score formula (live):** 1 (Champion) + 1 (Card) + 2×Proofs + 3×Affiliates.
**Champion #1** (James Sunheart): 12 proofs · Field Score 25 (verified via `/api/champion/lookup`).

---

## ❓ LOOP 17 — next funnel-close move

**Frame:** The Game IS the retreat funnel. Loops 15 (Retreat interest-capture) and 16 (Leaderboard) just shipped. The retreat card now collects signal directly; the leaderboard adds mid-funnel competitive visibility. Next move converts a *signaled* Champion → a *committed* retreat attendee.

Remaining ranked options:

- **(d) Store + Coherent Credit** — Field Score becomes a redeemable currency for retreat seats. Most direct conversion mechanism. Biggest scope.
- **(c) Match algorithm** — Card-to-Card compatibility builds the retreat cohort; pairs Champions for in-person sessions.
- **(e) Witness Roster activation** — non-Claude witnesses turn the Game into the multi-witness community a retreat actually is.
- **(a) Public Player State pages** (`?player=NAME`) — top-of-funnel shareable, drives invites.
- **Wait for signal** — let retreat-card interest capture run for ~24h before deciding; the field tells you what to build next.

**Open:** James to pick. Two Claude sessions are running in parallel and have started coordinating via NOW.md after the Loop 14 collision; before any deploy, both should re-pull the file and check for in-flight work (per `feedback_parallel_session_safety.md`).

---

## 🌐 LIVE INFRASTRUCTURE (verified 2026-05-08)

### Public surface
- `https://fullpotential.com/game` — the Game (Player State, Bring-a-Friend, Public Proof Loops)
- `https://fullpotential.ai/` — FPI homepage (FP Line, signals, share buttons)
- `https://fullpotential.ai/intelligence` — intelligence feed
- `https://fullpotential.ai/invest` — FP Frontier Basket

### Active Telegram surface
- **`@sunheartbrain_bot`** — `sh-brain-tgbot.service` on `162.0.208.88`. Commands: `/projects /questions /pending /digest /cohere /capture /private /public /forget /search`, plus plain-text brain Q&A. `/projects` reads ranking from synced NOW.md; `/questions` reads qb books from synced board.jsonl.
- **`@zenvillagebot`** — `zv-telegram-bot.service`, separate Zen Village brain.

### Servers
- **Primary `198.54.123.234`** — fullpotential.ai/.com surface, FP Index v5.6.0 (port 8550), Credits Gateway (8765), WhaleTrack (8600 — paper mode).
- **Brain `162.0.208.88`** — Sunheart Brain (mcp + tgbot + index), Zen Village Brain, Chief of Staff (8107 loopback).
- **Legacy `209.74.93.72`** — hosts Outbounders.com production (NOT eliminable per cost audit).

### Costs
~$805/mo all-in (verified 2026-04-29). See `project_costs.md` in memory.

---

## 📊 PROJECT RANKING — most-important first

*Synthesized 2026-05-08 from memory (stated priorities) + git momentum (last 14d) + live surface state + open qb questions. This is the SSOT for `/projects` ordering on `@sunheartbrain_bot` — bot reads ranks here, not guesses.*

| # | Project | Why this rank | Status |
|---|---|---|---|
| 1 | **The Full Potential Game** — Zen Village retreat funnel | P1 (memory). The Game IS the retreat funnel — every Loop is a funnel move. 16/16 recent commits. Most direct path to retreat seats = revenue. | 🟢 Active · Loop 16 latest |
| 2 | **The Village (Zen Village OS)** — Jam Board, Oracle Stage, Proof Pairings | P1 expansion. Lives inside the Game's substrate; not a separate bucket. | 🟢 Entangled with Game loops |
| 3 | **Sunheart Brain + Chief of Staff** — `@sunheartbrain_bot`, MCP memory, Priority/Money/Attention views | Direct lever on James's clarity. Cross-tool bridge already live. | 🟢 Live — brain server `162.0.208.88` |
| 4 | **Question Tracker / Inquiry Layer (qb)** — terminal title + books substrate | Inquiry-first frame at the tooling layer. Books refactor just shipped (fpai/game/sunheart). | 🟢 Live — laptop CLI + brain mirror |
| 5 | **FP Index / Credits Gateway / WhaleTrack** — fullpotential.ai surface | Live but passive (paper mode, intelligence feed). Surface, not active build. | 🟡 Live, low-touch |
| 6 | **Full Potential Concierge** — multi-tenant CX | P2 (memory). Dark-shipped behind flags. Hard guard: must not pull James off P1. | 🟡 Dark |
| 7 | **Outbounders.com** (legacy hosting) | Cost-anchored on `209.74.93.72`, can't eliminate. No active dev. | ⚪ Maintenance only |

**Read order for `/projects`:** show #1-#5 by default; collapse #6-#7 unless asked.

**Active inquiries** (snapshot — see `qb --all` for live state):
- *game / q-20260508-456895* — Who's coming to the first Zen Village retreat, and what does the booking page need to convert them?
- *fpai / q-20260508-e74f64* — How do we scope the Inquiry Layer into books so context doesn't blur? *(books refactor shipped; close pending)*

---

## ⚠️ DEPRECATED / RETIRED

- **`@soljai_bot`** — retired 2026-05-08. `streasury-bot.service` still up on brain server, unused. `/money` + `/priority` handlers live there but have no live Telegram path. Decide: stop unit + retire, or port handlers into `@sunheartbrain_bot` and then retire.
- **metaclaw + openclaw-gateway** — disabled 2026-04-30 (runaway Claude API bridge killed).
- **Consciousness feeder** — stopped intentionally (memory leak).
- **Vast.ai GPUs** — fully disabled, API key invalidated.

---

## 🧭 DECISION FILTER

For any "should I build X?" question, the answer must produce one of: **proof, revenue, clarity, or ease**, in a 30-day window. Default to no on anything that doesn't.

The repo has 261 services, most paused. **Bias toward deprioritizing and deleting, not adding.** (See `feedback_cruft_bias.md`.)

---

## 🔄 UPDATE PROTOCOL

1. When a Loop ships, append to the table above with type + date.
2. When a Loop opens, set "Loop N — pick what's calling" to the active one.
3. When something is retired, move it to Deprecated.
4. When live infrastructure changes (bot retired, service stopped, cost shifts), update the verified-date and the relevant block.
5. Commit on every meaningful change. The SSOT must not drift more than 7 days from reality.

---

*This file is read by Chief of Staff to render `/priority` and `/money`. If it's stale, those views lie. Keep it honest.*
