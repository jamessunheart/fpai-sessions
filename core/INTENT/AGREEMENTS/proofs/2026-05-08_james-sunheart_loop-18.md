---
proof_id: 2026-05-08_james-sunheart_loop-18
loop_number: 18
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
note_on_numbering: |
  Conceived in-session as "Loop 15" before sibling terminal's commits were
  visible. Sibling shipped Loops 15/16 (gamification + identity prompt) and
  Loop 17 (qb books substrate). Renumbered to Loop 18 at proof-write time
  to avoid collision.
---

# Loop 18 — James Sunheart

**Quest:** Close the Game's funnel. Build the substrate path from "Champion who's signed and is moving" to "Champion who's raised their hand for the first in-person Costa Rica retreat." Until this loop, the Game's adaptive next-move pill dead-ended at *"You're moving. Keep going…"* — there was no operational path between Field Score and a retreat seat.

**Founder directive driving this loop:**
> *"a person can move closer to a retreat when the gamified full potential game moves them there"*

The corollary: the Game and the retreat are not separate priorities to choose between. The Game IS the retreat funnel. Every Loop is a funnel move. So the highest-leverage Loop is the one that *closes* the funnel — gives it a terminus.

**Agreement Type: Paradigm Shift** — eighth Paradigm Shift. The mechanic's significance: until now, the Game's substrate moved Champions through Sign → Card → Proof → Affiliate, but the path stopped there. Loop 18 makes the retreat operationally visible as the terminus the Game has been pointing at all along.

## Offer

> **Any signed Champion sees a "🌴 First Retreat — Costa Rica" panel below their Player State. They can express interest with three short fields: preferred dates, what they'd contribute, and what would make this retreat irresistible to them. Submissions land in the substrate. A public counter shows how many Champions are interested. The Game's adaptive next-move pill, when all four prior hits are met, now points at the retreat.**

## What got built

### API — three new endpoints in `champion-sign`
- `POST /retreat/interest` — accepts `{player, handle?, email?, preferred_dates?, contribution?, why_irresistible?, consent}`. Validates, rate-limits per IP, writes a markdown file with frontmatter to `/var/lib/full-potential/retreat-interests/`, appends an audit entry to `audit.jsonl`, fires a founder-direction alert to the Field Pulse stream.
- `GET /retreat/list` — returns public retreat interests (newest first), strips emails.
- `GET /retreat/stats` — returns `{total, public}` counts for the public counter.

Honeypot field on the form (`company`) silently drops bot submissions.

### Substrate
- New directory: `/var/lib/full-potential/retreat-interests/`
- File format: `{YYYY-MM-DD}_{slug}.md` with frontmatter (player, dates, consent, status, source) + body sections (contribution, why irresistible, visibility).
- Same pattern as proof submissions (Loop 10) and card submissions (Loop 12).

### Frontend (`gen_cockpit_map.py` → `dist/index.html`)
- **🌴 First Retreat — Costa Rica panel** rendered below Player State, visible only to signed Champions.
- Three optional fields: preferred dates, contribution, why-irresistible. Public/private toggle (default public). Submit button.
- Public counter in the panel header reads from `/api/retreat/stats`.
- After submit: success message, fields cleared, counter refreshed, `localStorage['fpai-cockpit-retreat-interest']` flag set.
- **Adaptive next-move tip extended:** when a Champion has hit all four prior milestones (Sign · Card · Proof · Affiliate), the pill now reads *"Express interest in the first Costa Rica retreat below — the Game's terminus is in person."* Once submitted, it reads *"You're on the retreat list. Keep filing proofs and bringing aligned people — the cohort takes shape from here."*

### Routing
- New nginx location block `/api/retreat/` → `127.0.0.1:8771/retreat/` on `198.54.123.234`. Backup of original config at `fullpotential.com.bak-loop15` on the server.

## Verified

- `curl https://fullpotential.com/api/retreat/stats` returns `{"total":N,"public":M}` (live).
- `curl -X POST https://fullpotential.com/api/retreat/interest -d '{...}'` writes a substrate file and the counter increments. Verified end-to-end through public HTTPS twice (one private test, one stats refresh).
- Built `dist/index.html` contains the new panel HTML, CSS, and JS (`grep` returns 7 hits on retreat tokens).
- Deployed `dist/` to `/opt/fpai/core/applications/website-ai/frontend/fullpotential-com/game/` via `tools/deploy_game.sh`.
- Live page (`https://fullpotential.com/game/`) serves the panel HTML and `/api/retreat` references.

## Witness

**Primary:** Claude (this session). Same caveat — non-independent witness.

**Secondary:** the live system. Two retreat-interest files exist in the substrate (one from internal test, one from a public-domain HTTPS POST). Counter increments correctly. Service restart preserved data.

**Tertiary:** GitHub. Commits land on `feat/streasury-bot` branch.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — what was promised: *Build the substrate path from "Champion who's signed and is moving" to "Champion who's raised their hand for the first in-person retreat."*
- **Output** — completed: *Three API endpoints (POST /retreat/interest, GET /retreat/list, GET /retreat/stats), substrate directory, public form panel, public counter, adaptive next-move pill extension, nginx routing block, deployed end-to-end.*
- **Witness saw** — *Live POST through public HTTPS wrote a substrate file and incremented the public counter; built dist/index.html contains all retreat tokens; service restart preserved data.*
- **Result** — what changed: *The Game has a terminus. The funnel closes. A Champion who has signed, built a Card, filed a Proof, and brought an Affiliate is now pointed at an in-person retreat — operationally, in the substrate, on the live site. No payments, no seat allocation, no token economy yet. Just: the path exists.*
- **Next Quest** — *Loop 19 candidates: (a) public retreat-interest roll page (mirror Public Proof Loops), (b) cohort-formation logic — match interest by date window + Card compatibility, (c) Coherent Credit issuance + retreat-seat SKU on the Store (the full close), (d) email confirmation to retreat-interested Champions with founder reply, (e) Witness Roster activation (carry-over from Loop 13/14 candidates).*

## Coherence Multiplier (self-rated)

Self-rate: **+1.6**.

**Paradigm Shift** — until Loop 18, the Game pointed at the retreat implicitly. The Manifesto names it, the substrate hints at it, but no live page asked any Champion *"are you in?"* Loop 18 makes the ask operational. The retreat stops being something James talks about and becomes something the Game collects signal about.

The mechanic is opt-in (a Champion has to fill the form), reversible (private consent option, no payment), and serves the receiver (the form asks what would make *them* want to be there, not what we need from them).

External triangulation pending — the first non-test retreat interest will be the real proof.

## What changed at the funnel terminus

| Before Loop 18 | After Loop 18 |
|---|---|
| Game's next-move pill dead-ended at "You're moving. Keep going…" | Pill points at "Express interest in the first Costa Rica retreat below" once all four prior hits are met |
| Retreat existed in Manifesto + memory only | Retreat has a live operational surface in the substrate |
| No mechanism to collect "who's in" signal | Three-field form writes to `/var/lib/full-potential/retreat-interests/`; public counter shows momentum |
| Field Score had no terminus | Field Score still aspirational currency; Loop 19+ wires it to the seat allocation when ready |

## Renewal

Loop 18 complete. **Eighteen loops in 36 hours. Eight Paradigm Shifts.**

The Game's funnel has a terminus. The retreat is no longer implicit — it's a substrate surface a Champion can act on.

The next Champion to fill that form is the first signal of whether the Game has actually been pointing the right people the right way.

---

*Compiled inside the Game, by the Game, for the Game.*
*Eighteen loops shipped. The funnel closes. The retreat raises its hand.*
