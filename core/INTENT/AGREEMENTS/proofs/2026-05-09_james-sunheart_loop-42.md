---
proof_id: 2026-05-09_james-sunheart_loop-42
loop_number: 42
date_started: 2026-05-09
date_committed: 2026-05-09
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit)
witness_signed: true
consent: public
agreement_type: feature
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: true
  resources_circulated: false
  clean_pauses: false
---

# Loop 42 — Atlás's dashboard · role-aware Camp Zen Steward view

**Quest:** Make the Game's dashboard concretely useful for Atlás specifically. James said: *"Please clarity and update Atlás Full Potential Game dashboard to help build this."*

The dashboard had generic Top 3 Next Moves ("pair Mirror / file proof / share invite") — abstract. Atlás opening it should instead see Camp Director onboarding moves from the blueprint and a Camp Zen operations surface.

## What shipped

### Steward detection (JS-side)
`isCampSteward` checks if player_name matches "atlas" or "atlás" (case-insensitive, prefix-match). This is the simplest extensible primitive — future stewards can be added to the array, or a backend `role` field on champion records can replace this.

### Camp Zen Steward badge
A new pill on the player-state card alongside the foundational checkmarks: **🏕 Camp Zen Steward**. Hidden by default; shown only for stewards. Visual signal that the role is real and Game-recognized.

### Top 3 Next Moves — stage-aware override for Atlás
Replaces the generic stage logic with Camp Director-specific moves, sequenced by where Atlás is in onboarding:

**Pre-sign (current state):**
1. 🌀 Sign the World Peace Agreement — enter the Game · → Guest
2. 🪞 Pair your Digital Mirror — → AI Apprentice · +100c
3. 📅 Audit retreat calendar — next 6 months · Camp Director · Day 1

**Post-sign, no Mirror yet:**
1. 🪞 Pair your Digital Mirror — +100c
2. 📅 Audit retreat calendar — file as proof · +5–20c
3. 👥 1:1 with each team member — Josh · Halley · Michael · Sierra

**Mirror paired, in stabilize/improve phase:**
1. 🏠 Spend a full day as a guest — find friction · file proof · +20c
2. 📅 Confirm next 6 months of retreat dates
3. 🤝 Close 2 Anchor Host bookings (with Halley) — +50c per affiliate sign

Each move ties to the blueprint's days 1–30 / 31–60 / 61–90 phases AND surfaces the Game's earn-hook rewards inline. He sees what to do AND what the Game pays him for doing it.

### Camp Zen Operations card
A new full-width card that appears below the player-state for stewards only. Sections:

1. **Header** — Day N of 90 · stabilize phase
2. **Days 1–30 Stabilize checklist** (6 tasks from blueprint §4)
3. **Days 31–60 Improve checklist** (5 tasks, dimmed/future)
4. **Days 61–90 Lever Up checklist** (4 tasks, dimmed/future)
5. **Camp metrics** — 6-tile P&L dashboard (Retreat occupancy, Guest NPS, Anchor Host bookings, Operating margin, His revenue share this quarter, Credits earned). Targets per blueprint §6 noted.
6. **Non-negotiables** — the 6 from blueprint §8 always visible

Credits balance auto-pulls from the canonical fp-credits-gateway via `/api/champion/credits/balance/{slug}`.

### CSS
New `.camp-zen-card`, `.cz-section`, `.cz-task`, `.cz-metric`, `.cz-rules`, `.ps-steward-badge` — styled to match the established midnight + warm gold + Cormorant Garamond aesthetic.

## Why this matters

Per James's reframe in Loop 41: Atlás is a Player, the Game is his daily manager. This loop makes that real. When Atlás opens /game tomorrow:

- He sees his foundational state (○ WPA / ○ Character / ○ Mirror) PLUS his Camp Zen Steward role
- Top 3 Next Moves are concrete Camp Director actions, sequenced to his actual stage
- The Camp Zen Operations card gives him the full 90-day plan as a checklist with metrics
- Credit earnings show him the field economics in real-time

The substrate I shipped over Loops 26-41 — earn hooks, Field Coherence, Top 3, Mirror Loop, /credits — was always meant to be operational compensation primitives for actual Players. Atlás is the first Player to get a customized lens. The Game is no longer abstract; it's his operating system.

## Constitutional fit

- **Truth over confidence:** Camp metrics show "—" when there's no data (Day 1). They populate as actions register, not as fake placeholders.
- **Coherence:** what the offer letter (Loop 41) promises ("the Game is your daily manager") is now what the dashboard literally shows.
- **Service not rule:** the Game guides; James does Friday strategy. The dashboard's Top 3 IS the daily guidance.

## Files

- `tools/gen_cockpit_map.py` — steward detection JS, Camp Zen Operations card HTML, CSS for `.camp-zen-card` / `.ps-steward-badge` / `.cz-*`, credit balance integration

## Verified

- Page deploys cleanly via `tools/deploy_game.sh`
- HTML source contains `campZenOps`, `ps-steward-badge`, `cz-label` markers
- Steward detection logic present in JS
- Atlás's record in champion-sign confirmed (no champion yet — pre-sign state, dashboard correctly shows pre-sign Top 3)

## Next moves

- **James:** decide if/when to send Atlás the offer (Loop 41 v0.3) and the link to his customized dashboard
- **Atlás (when he visits):** he'll see the Camp Zen Steward view immediately, even pre-sign
- **Future:** when more stewards are named (Halley, Josh, Sierra, etc. with their own roles), extend the steward array and add per-role operations cards

*— Sealed 2026-05-09*
