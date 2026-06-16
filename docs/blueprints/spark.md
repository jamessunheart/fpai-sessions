# Spark Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16
**Function:** #2 — First-Touch Routing

---

## Identity

- **Function:** Spark — first contact, intake routing, situation understanding
- **Owner:** `tgbot.py` (server 162, `sh-brain-tgbot` service) + `curator/triage.py`
- **Status:** Live (shadow scorecard building — d016)
- **Created by:** foundational; shadow scorecard via d016; formalized here

---

## What it does

Spark is the first contact point for every new person who reaches James's platform. Its job is to understand who this person is and what they need in 3 questions or less — then route them to exactly one next step. It does not onboard people into everything at once. It listens, identifies the situation (stuck / exploring / building / looking for community), senses the energy level, and routes cleanly to one path. No features, no menus, no options. One move.

---

## How it works

**Input:** First message from any new user (or any user Spark hasn't routed yet)

**Process:**
1. Detect: is this a new user or a returning one? (check `brain_index.user_agents`)
2. If new: Spark mode — 3-question intake
   - Q1: "What's going on for you right now?" (situation)
   - Q2: "What would feel like a win today?" (goal / energy)
   - Q3: (implicit or explicit depending on answer quality) "What's in the way?"
3. Parse answers → classify route: clarify / take_action / camp_zen / proof / community
4. Hand off to Ember with passport stub: `{user_id, situation, goal, energy, route}`
5. Returning user: skip Spark, route to Ember directly with their profile

**Output:** `agent_passport` stub → `brain_index.agent_passports` + route signal to Ember

**Side effects:**
- `brain_index.user_agents` record created (first-message namespace init — d039/d042)
- CORA genesis grant (d035): small initial balance for completing intake
- Correction signal if James overrides route: `brain_index.corrections`

**Shadow scorecard (d016 — building):**
- Logs `would_route={route}` before routing
- After session: logs `actual_outcome={what_happened}`
- When logged agreement ≥ threshold for a lane: promote that lane to live-only (not shadow)

---

## Quality standard

- Route decision in ≤ 3 questions per user (not a conversation, an intake)
- Route accuracy ≥ 70% by user self-report within first session (shadow scorecard measures this)
- No user feels interrogated — questions feel like natural conversation
- Zero users dropped (every first message gets a Spark response, even if triage fails)
- Returning users: never ask Spark questions again (passport persists)

---

## Current behavior (verified 2026-06-16)

- `tgbot.py` handles first-contact routing in `sh-brain-tgbot` service on 162
- Routing logic: situation/goal/energy classification → one route
- Shadow scorecard: d016 building (logs would-route vs actual outcome per lane)
- User namespace: not yet isolated per user (d039 building)
- CORA intake grant: not yet live (d035 CORA policy just merged today, 2026-06-16)
- Triage module: `curator/triage.py` exists for more complex classification

---

## Known gaps

- 2026-06-16: No per-user namespace yet — Spark routes into shared Ember space (d039 building)
- 2026-06-16: Shadow scorecard not yet logging agreement per lane (d016 building)
- 2026-06-16: No CORA intake grant yet (d035 merged today; grant wiring = d042)
- 2026-06-16: Onboarding flow v0.1 (d036) building — Spark hands off to generic Ember, not a structured onboarding flow yet
- 2026-06-16: Route promotion from shadow to live not yet implemented (depends on d016 agreement score)
- 2026-06-16: No explicit Agent Passport schema yet — passport is implied in routing, not stored formally

---

## Integration map

- **Depends on:** `tgbot.py` (message handling), `brain_index.user_agents` (returning user check), `curator/triage.py` (classification)
- **Used by:** Ember (receives route + context), Steward (receives passport for namespace init), CORA (grants intake reward)
- **DB tables:** `brain_index.user_agents`, `brain_index.agent_passports`, `brain_index.tg_messages`
- **Kill switch:** `sh-brain-tgbot` service stop (`systemctl stop sh-brain-tgbot`) — stops all Spark + Ember responses

---

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | d035 | CORA policy merged — Spark can now grant CORA on intake | First step toward rewarding engagement from first contact |
| 2026-06-16 | d036 | Onboarding flow v0.1 building | Structured path from first touch to Agent Passport — not ad-hoc |
| 2026-06-14 | d016 | Shadow scorecard spec queued | Would-route logging + outcome tracking → promote only proven lanes |
| 2026-06-12 | session | Bot simplified to sole owner, plain 1-2 sentence replies | Removed complexity that was diluting Spark's routing clarity |

---

## Test coverage

- `curator/tests/` — curator module tests (indirect)
- Shadow scorecard (d016): live measurement of route accuracy
- Smoke TEST 3 (d049): thread activity check — confirms bot is receiving messages
- NOT tested: Spark intake flow end-to-end with mock user
- NOT tested: route classification accuracy on fixture conversations
