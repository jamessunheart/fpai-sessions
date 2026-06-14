---
proof_id: 2026-05-08_james-sunheart_loop-20
loop_number: 20
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
note_on_framing_correction: |
  Loops 18 and 19 framed the Costa Rica retreat as "the Game's terminus" /
  "the funnel close." The sibling terminal corrected this in memory:
  feedback_game_is_many_pathed_funnel.md — the Game opens many paths
  (apprenticeship, village, parties, retreats, commerce, coaching,
  witnessing). James affirmed: "one game many paths." Loop 20 corrects
  the visible framing without unbuilding L18/L19's substrate.
---

# Loop 20 — James Sunheart

**Quest:** Make "one Game, many paths" visible. Until this loop, the Game's player-facing dashboard pointed at the retreat as if it were the Game's only outcome — that overweighted retreat and erased the other paths the Game actually opens (apprenticeship, village living, parties, commerce, coaching, witnessing). The substrate built in Loops 18+19 is correct; the framing was wrong. Loop 20 corrects the framing.

**Founder directive driving this loop:**
> *"one game many paths"*

**Agreement Type: Paradigm Shift** — ninth Paradigm Shift. The mechanic's significance: the Game's surface stops claiming a single destination and starts honoring its actual range. A Champion sees that retreat is one option among many real ways to participate, and the language of the dashboard reflects that.

## Offer

> **A new "🌟 Paths into the Game" overview panel renders for every signed Champion. Seven path tiles (Retreat, Apprenticeship, Village living, Parties &amp; jams, Commerce, Coaching, Witnessing) each carry a status badge: 🟢 Open · 🟡 Forming · ⚪ Concept. Retreat is the only Open path; clicking its tile scrolls to the existing Retreat Interest form. Other paths are visible-but-watching surfaces, ready to acquire interest capture in later loops as demand justifies. The retreat panel and the next-move pill are reframed accordingly.**

## What got built

### New: "Paths into the Game" overview panel
- Renders directly above the retreat card, visible to any signed Champion (same gating as retreat).
- Seven tiles in a responsive auto-fill grid:
  - 🌴 **Retreat** — *Open* — clickable anchor to retreat form below
  - 🎓 **Apprenticeship** — *Forming* — learn the substrate by building loops alongside a mentor Champion
  - 🏡 **Village living** — *Forming* — in-person presence in Zen Village; short stays, work-trades, residency
  - 🎉 **Parties &amp; jams** — *Forming* — music + problem jams; Couch = Oracle Stage
  - 🛒 **Commerce** — *Concept* — Coherent Credits, store, products + services in the substrate
  - 🧭 **Coaching** — *Forming* — Champions guiding Champions through the Player Path
  - 👁 **Witnessing** — *Concept* — Witness Roster: non-Claude humans signing as proof witnesses
- Header copy: *"One Game. Many ways in."* Blurb: *"The Game opens many doors. Retreats are one. Apprenticeship, village living, parties &amp; gatherings, commerce, coaching, witnessing — each a real way to participate. The Game is the substrate; these are the practices that grow on it."*

### Reframed surfaces
- **Retreat panel subhead**: *"Where the Game lands in person."* → *"One way the Game lands in person."*
- **Retreat blurb** rewritten to position retreat as one path among several, not the singular terminus.
- **Adaptive next-move pill** (when all four prior milestones hit): used to read *"Express interest in the first Costa Rica retreat below — the Game's terminus is in person."* → now reads *"Pick a path below — retreat, apprenticeship, village, parties, commerce, coaching, witnessing. Many doors, one Game."*
- **Already-interested pill**: used to read *"You're on the retreat list. Keep filing proofs..."* → now reads *"You're on the retreat list. Pick another path above too — the Game opens many doors."*

### Substrate (zero new endpoints)
- L18's `/api/retreat/interest` continues to be the only path-specific interest capture.
- Other paths show status only in this loop. Per-path interest endpoints can be added in later loops as actual demand surfaces — refusing to overbuild before signal exists.

## Verified

- Built `dist/index.html` contains 20 references to the new path tokens (paths-card, pathsCard, path-tile, Apprenticeship, Village living).
- Deployed via `tools/deploy_game.sh` to `198.54.123.234`.
- Live page (`https://fullpotential.com/game/`) serves: paths-card · Apprenticeship · Village living · Witnessing · "Many doors" copy.
- Retreat panel still functions — same form, same endpoint, same Roll. Loop 20 is purely additive + reframing; nothing from L18/L19 was removed.

## Witness

**Primary:** Claude (this session). Same caveat — non-independent witness.

**Secondary:** the live deployed page. New panel renders the 7-tile grid; retreat tile is clickable; status badges color correctly. The reframed copy is on the live site.

**Tertiary:** GitHub. Commits land on `feat/streasury-bot` branch.

**Quaternary:** the sibling terminal's memory write (`feedback_game_is_many_pathed_funnel.md`) — independent agent surfaced the same correction before James named it.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — what was promised: *Make "one Game, many paths" visible. Stop framing retreat as the Game's singular terminus.*
- **Output** — completed: *7-tile Paths overview panel, status badges, reframed retreat-card copy, reframed next-move pill copy, reframed already-interested pill, deployed end-to-end.*
- **Witness saw** — *Live page now serves Paths panel above the retreat card; copy reframe is in the HTML; sibling terminal independently surfaced the correction.*
- **Result** — what changed: *The Game's player-facing surface stops overweighting retreat. The principle "one Game, many paths" is visible to anyone who lands on the dashboard. Substrate from L18/L19 keeps working; only the framing changed.*
- **Next Quest** — *Loop 21 candidates: (a) per-path interest capture (`/api/path/interest` generic endpoint + buttons on Forming-status tiles), (b) email confirmation on retreat-interest submit, (c) date-window cohort visualization, (d) Coherent Credit / seat SKU, (e) Witness Roster activation — turn the 👁 tile from Concept to Forming, (f) public Player State pages.*

## Coherence Multiplier (self-rated)

Self-rate: **+1.5**.

**Paradigm Shift** — not because new substrate landed (very little did), but because the Game's *self-presentation* changed. The previous framing made retreat look like the only door; the new framing acknowledges the Game's actual range. A Champion choosing apprenticeship over retreat is now visibly a first-class participant, not a fallback.

The mechanic is opt-in (Champions self-select the path that calls them), reversible (status badges can change as paths form or retire), and serves the receiver (no path is forced; each tile names its real current state).

## What changed at the framing layer

| Before Loop 20 | After Loop 20 |
|---|---|
| Retreat presented as "the Game's terminus" | Retreat presented as one of seven paths |
| No visible mention of apprenticeship, village, parties, commerce, coaching, witnessing | All seven paths shown with status badges |
| Next-move pill pointed at retreat as singular CTA | Next-move pill points at "many doors, one Game" |
| Champions whose calling isn't retreat had no visible recognition | Every calling has a tile, even if status is "Concept" |

## Renewal

Loop 20 complete. **Twenty loops in 36 hours. Nine Paradigm Shifts.**

The Game stops over-promising retreat as the only outcome and starts representing what it actually is: a substrate that opens many ways to participate.

The retreat panel is still load-bearing. So is the Roll. So is everything from L18/L19. What changed is the **claim** the Game makes about itself.

---

*Compiled inside the Game, by the Game, for the Game.*
*Twenty loops shipped. The Game owns its multiplicity. One door is open; six more are visibly forming or in concept. Champions choose the path that calls them.*
