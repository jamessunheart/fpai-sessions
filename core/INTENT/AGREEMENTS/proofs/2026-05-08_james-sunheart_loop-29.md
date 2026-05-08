---
proof_id: 2026-05-08_james-sunheart_loop-29
loop_number: 29
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit)
witness_signed: true
consent: public
agreement_type: feature
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: false
  resources_circulated: false
  clean_pauses: false
---

# Loop 29 — Top 3 Next Moves · stage-aware action grid

**Quest:** Replace the single "🎯 What's my next move?" button with a three-tile grid of stage-aware moves, each with a point value (or stage-up reward) and a direct CTA. Closes the dashboard reorg vision James sketched.

**Founder directive (from earlier in this session):**
> *"top 3 action steps (with point values etc.) and then any matching / rewards to claim"*

## What shipped

Three move tiles in player-state, computed client-side from current player state. Stage-aware logic:

- **Visitor** (no champion): Sign WPA (+1 → Guest) · Read Manifesto · See Champions Roll
- **Guest** (champion only): Build Character (+1 → Player) · File Proof (+2) · Share invite (+3 per sign)
- **Player** (no Mirror): **Pair Digital Mirror** (→ AI Apprentice) · File Proof (+2) · Share invite (+3)
- **AI Apprentice** (Mirror paired): File more Proofs · Bring 1 person in · Witness another player

Each tile shows: rank (#1/#2/#3), icon, action text, reward (point value or stage-up), CTA button. Tiles with `data-anchor` scroll-to relevant page section; the invite-link tile auto-copies on click; the Mirror tile links out to /game/mirror.

## Why this matters

The Field Score formula (1·champ + 1·card + 2·proof + 3·affiliate) was previously implicit. Now each available move surfaces its point value next to the action. Players see "+2 pts" or "+3 pts per sign" or "→ AI Apprentice" right at the moment of decision — turning the formula into a visible menu.

The Mirror tile naturally rises to #1 once Player stage is reached, making the Mirror Loop ignition discoverable without separate marketing. The dashboard is now its own funnel.

## Files

- `tools/gen_cockpit_map.py` — `.ps-next-moves` CSS, top-3 move grid HTML, stage-aware JS computation, anchor-scroll + invite-copy handlers

## Verified

- Deployed; CSS + HTML present in served `/game` page
- Existing single match button hidden (kept in DOM for now in case any other JS still references it)

*— Sealed 2026-05-08*
