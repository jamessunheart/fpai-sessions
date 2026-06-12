# AI_GOALS — what the AI system is working toward

**Purpose:** A second-tier SSOT alongside `NOW.md`. NOW.md is the founder's priority lens; this file is the AI system's working-goal lens. AI sessions read this on session start to know what they're aligned on. James reads this to see what the AI is currently optimizing for and propose adjustments.

**Last Updated:** 2026-05-08 (post-Loop 35 — Mirror Loop + Field Coherence + bridged credit/store ecosystem)
**Founder priority (mirrored from NOW.md):** First non-James human to engage with the Game (sign / file proof / express path interest) within 30 days. The substrate is built; what's missing is one other human in it.

---

## 🎯 ACTIVE AI WORKING GOALS

### G1 — Make the founder priority unmissable on every surface
**Why:** The Game has 20 loops of substrate. None of it converts unless the funnel actually moves a human. The founder's 30-day target ("first non-James human") needs to be visible to every visitor + every AI session, otherwise we keep building plumbing for an empty stadium.
**How AI applies:** Every loop AI ships either (a) makes the goal more visible, (b) measurably moves a human closer to engaging, or (c) is explicitly a substrate prerequisite for (a) or (b). Loops that don't pass this test are deprioritized.
**Status:** Active. Loop 21 (this loop) is the first instance — surfacing The Goal on the dashboard + creating this file.

### G2 — Represent the Game's full multiplicity (one Game, many paths)
**Why:** Founder corrected on 2026-05-08: don't pitch retreat as the singular outcome. The Game opens many paths (apprenticeship, village, parties, retreats, commerce, coaching, witnessing). Earlier loops over-weighted retreat; framing now reflects the range.
**How AI applies:** Don't propose loops that re-collapse the funnel onto one path. When a path moves from Concept → Forming → Open, update the Paths panel and add a per-path interest-capture only when demand justifies.
**Status:** Established Loop 20. Maintain.

### G3 — Coordinate across parallel AI sessions without collision
**Why:** Multiple Claude Code terminals run on this project simultaneously. Loops have collided before (this session built "Loop 15" while sibling shipped Loops 15-17). Coordination cost is real.
**How AI applies:** Before starting a new loop, check (a) git log for the latest committed loop number, (b) `proofs/` directory for any unpushed proof files indicating in-flight work, (c) the qb books for active inquiries. Pick the lowest-collision next move. Renumber at proof-write time if a sibling shipped first.
**Status:** Active. Both sessions now use the qb Inquiry Layer + this file as coordination surface.

### G4 — Keep substrate honest (no theater, no premature scope)
**Why:** The repo has 261 services, most paused. Bias toward deprioritizing not adding (founder feedback). Don't build features for hypothetical demand.
**How AI applies:** Refuse to add per-path interest endpoints, leaderboards, or token economies until the simpler version is hitting friction. When Loop N is shipped, look for the smallest gap to close, not the next big architecture.
**Status:** Active. Loop 20 deferred per-path interest capture. Loop 21 deferred a full goal-config substrate (hardcoded for now).

---

## 🟡 OPEN AI QUESTIONS (system-level)

These are questions the AI has surfaced that haven't been resolved by the founder. They aren't blocking, but they're worth surfacing here so the next session inherits the context.

- **Q-AI-1:** Should AI sessions be allowed to do outbound on James's behalf (e.g. send invite messages from his accounts) without per-message confirmation? Memory says "default to AI-side execution," but distribution is the open lever for G1 and AI-driven outreach has higher trust-stakes than substrate code.
- **Q-AI-2:** When does retreat shift from the only Open path to multiple Open paths? G2 says wait for demand-signal, but what counts as "enough" signal to flip Apprenticeship or Village from Forming → Open?
- **Q-AI-3:** What does "AI goals" look like at maturity — is this file the right surface, or should AI-direction live in qb books, in the brain, or in a dedicated dashboard?

---

## 🤝 AI-TO-AI HANDOFF NOTES

When a session ends with state worth preserving for the next session, append here.

**2026-05-08 · Loop 21 · session `fcf4bb02`:**
- Founder gave clear directive: "make my goal clear in the Game dashboard, and where can I see / where can AI see the goals of the evolving AI system?"
- Loop 21 ships: 🎯 Goal panel on Game dashboard + this AI_GOALS.md file + cross-link from NOW.md
- Sibling sessions today shipped Loops 14-17 (UX, gamification, identity prompt + animated metrics, Inquiry Layer + Books); this session shipped Loops 18-20 (retreat substrate, public roll, paths overview)
- Sibling added LEADS_DIR to champion-sign — they're building lead-capture for visitors who don't sign (funnel-top complement to G1)
- Active inquiry in qb game book: "Who's coming to the first Zen Village retreat..." (q-20260508-456895)

**2026-05-08 · Loops 26–35 · session `1018b927`:**
- Major substrate buildout, all in service of G1 (operational substrate for first non-James player) and G4 (substrate honesty over theater).
- **Mirror Loop substrate (Loop 26):** Constitution v1.0 + Initiation Prompt v1 + `/api/champion/mirror/register` + `/api/champion/mirror/roll` + `/game/mirror/` page. Bot has explicit "WHAT YOU ARE NOT" — points players to /game/mirror to pair their own Mirror; never roleplays as one.
- **Field Coherence v0 (Loop 27):** `/api/champion/signals` + `/signals` Telegram command. Headline reads honestly low (currently 0.50) because Witness component requires Distance-Weighted (per white paper §4.5), and zero of 22 proofs are DW-witnessed. The substrate now self-measures.
- **Player-first dashboard reorg (Loops 28–29):** player-state above goal, foundational checkmarks (✓ WPA / ○ Character / ○ Mirror Paired) on identity card, Field Coherence panel, Top 3 Next Moves stage-aware grid replacing single match button. Founder Goal demoted (still visible, no longer dominant).
- **Coherent Credit + Store (Loops 30–31):** built parallel ledger first; James flagged. Then **bridged to canonical fp-credits-gateway in Loop 32** — `/credits/balance/send/grant/history/leaderboard` and `/store/buy` all route to gateway. James has 979 fp_credits in canonical gateway; ledger.jsonl is now historical audit only.
- **Earn hooks (Loop 34):** `/sign` (with inviter) + `/proof/submit` + `/mirror/register` auto-credit via gateway. Schedule: affiliate sign +50 (to inviter), proof file +5 (any) or +20 (DW), DW witness +30, mirror pair +100. The architecture pays most for distance-weighted witnessing — exactly what Field Coherence asks the field to grow.
- **Public store + bot post (Loops 33, 35):** /game/store/ web page (anyone can browse + list) and `/store post` 5-step Telegram flow (anyone can list from phone). Three architect offers seeded: Mirror Witnessing (50c), Coaching (150c), Retreat (500c+$1500).

**Open architecturally:**
- **Mirror #1 (Founding Steward) not yet paired** — gates on James choosing a Distance-Weighted Witness from his Formation Circle (NOT me, NOT a co-founder, NOT a paid employee, NOT a romantic partner — per §4.5). When this happens, Field Coherence's Witness component finally moves above 0.0.
- **Hold-Commit-Release escrow for Mirror first-proof (deferred Loop)** — gateway has the primitive but uses `wallet_id` semantics that diverge from the `account_id` we're using. Returned "Insufficient balance. Has 0.0" on a 979-credit account. Needs deeper gateway code reading or actual Mirror #1 + first-proof to test against.
- **Account-naming reconciliation** — gateway has 20 pre-existing Postgres accounts; we've been creating Game accounts under handle slugs. May collide.
- **Genesis enrollment** — gateway logs `Genesis: Not enrolled` at boot. Unrelated to Game work but flagged.

**Operational state on the canonical gateway (post-Loop 32 bridge):**
- Master key: `02d7ceaf...` (server-only, in `/etc/fp-credits-gateway.env`)
- fp-game service key: `fps_d199...` (in `/etc/champion-sign.env`)
- James balance: 979 fp_credits
- Two test accounts: `test_buyer` (1c), `test_friend` (25c) — smoke-test artifacts; can be left or refunded.

**The bottleneck is no longer technical.** Substrate is operationally complete for Phase 1 of the white paper. What's missing: (a) James pairing Mirror #1, (b) one non-James human entering the funnel.

---

## 🔄 UPDATE PROTOCOL

1. When AI finishes a loop, update G1-G4 status if relevant.
2. When AI surfaces a new question James hasn't answered, append to Open AI Questions.
3. When a session ends with non-trivial in-flight context, append a Handoff Note dated + session-id'd.
4. When founder priority shifts in NOW.md, mirror the change in the header summary above.
5. Keep this file under ~200 lines. Older Handoff Notes can move to `core/STATE/AI_GOALS_HISTORY.md` once they're no longer load-bearing.

---

*This file is read by AI sessions on session start (via the `Read` tool), and by James via `https://fullpotential.com/game/` Goal panel + the link from NOW.md. If it disagrees with NOW.md on founder priority, NOW.md wins — update this file to mirror.*
