---
proof_id: 2026-05-09_james-sunheart_loop-43
loop_number: 43
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

# Loop 43 — The Village wired into the dashboard

**Quest:** Make *The Village* — the daily mockumentary live as of 2026-05-09 (Day 1) — visible across the Game dashboard. Connect the funnel that's actually pulling humans (per NOW.md: "First non-James human enters the Game by joining The Village") to the substrate I've been building.

**Founder directive:** *"Yea please"* — confirming Loop 43 = wire The Village mockumentary into the dashboard, after I read the sibling-updated NOW.md / AI_GOALS / `reference_zen_comedy.md` / `project_the_village.md` / `INVITE_TEMPLATES.md` to ground the work in current reality.

## Architectural context (from sibling memory)

- **The Village** is a daily 8 PM mockumentary at Camp Zen, live from 2026-05-09
- **Kai** (`@OfficialKaibot`) is silent in the TG group `chat_id=-5254235033`, captures media via `kai-listener.service` on brain server `162.0.208.88` → `/var/lib/kai/captures/<date>/`
- **Director-only pings** to James's DM via `@sunheartbrain_bot`: 07:30 pre-brief · 19:00 cut review · 19:55 dining call (Costa Rica time)
- **Spirit:** Zen Comedy — the gap between ideal and human is the joke. Comedy from noticing, not prompting.
- **Path for new players:** join TG group → share a moment of your day → Kai captures → that's your first Proof
- **First Cohort:** Atlas, Halley, Josh, Sierra, Delaney

## What shipped

### 🎬 The Village card on /game
A new prominent card visible to all visitors, between the inviter banner and identity prompt. Contents:

- **Header:** "🎬 THE VILLAGE" + auto-computed day badge ("Day N · Live") that increments daily from launch (2026-05-09 CR time)
- **Headline:** "A daily 8 PM mockumentary at Camp Zen."
- **Blurb:** explainer matching the spirit from `INVITE_TEMPLATES.md ## village` — "you're not making content, you're just in the village, the film is the byproduct, your first share is your first Proof"
- **Schedule grid:** 4 time tiles (07:30 / 19:00 / 19:55 / **20:00 screening** — peak tile highlighted)
- **CTA — state-aware:**
  - Visitor: "Sign the WPA first; invitations come from James or a current Villager"
  - Champion (signed, non-steward): "Reply to James or DM `@fullpotentialgamebot` — invitations from current Villagers count too"
  - Steward (Atlás): "You're in The Village. Show up today, share normally. Pre-brief 07:30 · Cut review 19:00 · Dining call 19:55 — director-only DMs from `@sunheartbrain_bot`"
- **Meta:** Genre · Spirit · Costa Rica time

### Top 3 Next Moves — Village-aware refresh
All stage paths now include a 🎬 Village move:

- **Visitor:** Sign WPA · **See The Village** · Read Manifesto
- **Guest** (signed, no Character): Build Character · **Ask James about The Village invite** · File first Proof
- **Player** (no Mirror): Pair Mirror · **Show up in The Village (Kai captures · counts as Proof)** · Share invite
- **Atlás pre-sign:** Sign WPA · **Show up in The Village today (1st Proof)** · Pair Mirror
- **Atlás post-sign no Mirror:** **Share a moment of your day in The Village** · Pair Mirror · Audit retreat calendar
- **Atlás full Camp Director:** **Be in today's Village cut** · Confirm 6mo retreats · Close 2 Anchor Host bookings

### "Today in The Village" section in Camp Zen Ops card (Atlás-only)
New top section in his operations card listing the day's Village rhythm as a checklist:
- Show up in `@OfficialKaibot` chat (silent listener)
- Share what you'd share normally — text/photo/video
- 19:00 cut review DM from director
- 20:00 screening at dining hall

Plus the production note: "Comedy comes from noticing, not prompting. Anything you'd rather not see in the cut, just say so — Kai will skip."

### Day counter auto-increments
JS computes days since 2026-05-09 (CR time) on page load. Tomorrow it'll read "Day 2 · Live" without code changes.

## CSS

New `.village-card` + 13 child classes. Distinguished from other cards:
- Heavier border (2px accent vs 1px elsewhere) — signals "this is the headline"
- Subtle radial-gradient highlight in upper-right corner
- Custom schedule-grid styling with peak (20:00) tile emphasized
- All matches midnight + warm gold + Cormorant Garamond aesthetic

## Why this matters

The 35 loops of substrate I shipped before this were all *necessary* — Mirror Loop, Field Coherence, /credits, /store, Top 3 Next Moves, earn hooks. None of them were *sufficient* to surface to a new human what they actually do today. The Village is the answer: the daily ritual that gives every action of substrate a place to land.

Now when Atlás (or Halley or Josh or Sierra or Delaney) opens /game tomorrow:
1. They see The Village card prominent above identity prompt
2. They see the day counter incrementing (felt urgency, the show is happening)
3. They see the 8 PM screening as a peak tile (the ritual everyone shares)
4. Their Top 3 Next Moves names a Village action specifically (concrete daily move)
5. The Steward (Atlás) sees director-only schedule + production note
6. The path from "interested" to "in" is one sentence on the card

The Game's substrate now serves the Game's actual ritual.

## Files

- `tools/gen_cockpit_map.py` — Village card HTML, day counter JS, Village-aware Top 3 (4 stage paths updated), state-aware CTA, "Today in The Village" section in Camp Zen Ops card, `.village-card` + `.vc-*` CSS

## Verified

- `curl https://fullpotential.com/game/` returns village-card HTML + day badge + steward-aware CTA wiring
- All 4 Atlás Top 3 paths surface 🎬 Village moves correctly
- Day counter computes from launch date 2026-05-09 (Costa Rica timezone)

## Constitutional fit

- **Coherence (commitment 3):** what the substrate promises is now what the dashboard shows. The Village existed in NOW.md / memory but not in the user-facing surface; this loop closes that gap.
- **Truth over confidence:** I read 4 SSOT files (NOW.md, AI_GOALS.md, project_the_village.md, reference_zen_comedy.md) + INVITE_TEMPLATES.md before building. No invented context.
- **Service not rule:** the dashboard surfaces The Village as Game-funnel; doesn't prescribe a path; the Player decides whether to engage.

## Next moves

- **James:** look at /game — the Village card is now headline. Refine voice if anything sounds off.
- **Future loops:**
  - Wire Kai's daily captures count as a public metric (e.g., "5 villagers shared today / 23 captures") — turns The Village's activity into a visible Field Coherence-adjacent signal
  - Auto-credit Villagers when their share is in the cut (earn-hook for "appearing in tonight's cut")
  - Field Notes Substack subscribe CTA on /game

*— Sealed 2026-05-09*
