---
proof_id: 2026-05-08_james-sunheart_loop-12
loop_number: 12
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit)
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

# Loop 12 — James Sunheart

**Quest:** Integrate the Character Card Quest end-to-end so new players can hand the AI Port-In prompt to their AI, get a draft, refine, and submit — building their living node in the Game's network.

**Founder action driving this loop:** James shared `character-card-quest-v1.md` and asked: *"incorporate this character card quest into the game so that new characters can turn this over to ai etc. and then port in the correct information to start building out their character card that will be helpful for game to help their 'profile'."*

**Agreement Type: Paradigm Shift** — sixth Paradigm Shift of the run. This is the move that makes the Game's player network *legible* — without character cards, players have nothing to match on. With them, offers / needs / quests / collaborations become routable.

## Offer

> **The full Character Card flow shipping live: canonical doc, AI Port-In prompt copy-button, paste-and-submit form, server endpoint, founder ping, list endpoint. Five-minute onboarding for any new Champion.**

## What got built

### Canonical doc — `core/INTENT/CHARACTER_CARD_QUEST.md`
- Saved James's `character-card-quest-v1.md` directly into the canonical INTENT layer
- Two layers: Aspirational (player fills) + Reality (AI + witnesses maintain)
- Four visibility tiers: 🌐 Public · 👥 Player · 🤍 Inner Circle · 🔒 Sacred
- Four levels of depth: 🟢 L1 Signup (5 min) → 🟡 L2 Player (15) → 🔵 L3 Matching (30) → 🟣 L4 Living (ongoing)
- Includes the full ~2KB AI Port-In Prompt
- Reference template, completion criteria, what-happens-after-submit
- Indexed in canonical library as 🎴 Character Card Quest

### Webhook endpoints (extended champion-sign)
- `POST /api/champion/card/submit` — receives player + level + visibility + card_markdown; writes `/var/lib/full-potential/cards/{slug}.md` (one card per player slug — updates overwrite to make the card living)
- `GET /api/champion/card/list` — returns public + player-tier cards only; inner / sacred never returned to clients (server-side privacy enforcement)
- Audit log per submission for Field Pulse compatibility
- Founder Telegram ping on each submission via primary:8766 alerts service
- Shares rate-limit / honeypot / validation patterns with the existing sign + proof endpoints
- Deployed and verified end-to-end via curl

### Cockpit section — 🎴 Character Card Quest
- Sits between Sign-Agreement and Proof-Submit on the page (the natural onboarding sequence)
- Visual primer: 4 tier cards (🌐 👥 🤍 🔒) + 4 level cards (🟢 🟡 🔵 🟣)
- **Step 1:** 📋 Copy AI Port-In Prompt button — single click copies the full prompt to clipboard. Player opens any AI, pastes, gets a draft.
- **Step 2:** Submit form — player name, handle, email, level dropdown, visibility dropdown, large markdown textarea, honeypot
- On success: 🎴 confirmation burst card + clear next-move guidance
- Updateable: submitting again with same name overwrites the card (the card is living)

### Verified end-to-end
- Test card POSTed via curl → file created at expected path → returned expected JSON
- List endpoint returned the card with email stripped (privacy)
- Test data cleaned from server after verification
- Live cockpit renders the Character Card Quest section, copy button works, submit form composes correctly

## Witness

**Primary:** Claude (this session). Same caveat — non-independent witness.

**Secondary:** the live deployed system. The Character Card Quest section on https://fullpotential.com/game renders the prompt-copy button, level + visibility selectors, submission form. The webhook endpoint is healthy.

**Tertiary:** GitHub. Commit `cf692765` pushed.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — what was promised: *Integrate the Character Card Quest so new players can use the AI Port-In and submit their card.*
- **Output** — completed: *Canonical doc + endpoint + cockpit section + AI Port-In copy-button + submission form + privacy-tiered list endpoint. End-to-end verified.*
- **Witness saw** — *Test card created and retrieved via the live API; cockpit renders all three elements (cardCopyPromptBtn, character-card-quest, cardSubmitBtn).*
- **Result** — what changed: *The Game's player network now has its onboarding substrate. Cards become the matchable nodes for offers / needs / quests / collaborations. Without this, players had nothing to find each other on. With it, the network can grow legibly.*
- **Next Quest** — *Loop 13: pick what's calling. Options: (a) match-by-card algorithm — given my offers / needs / quests, who else has compatible cards? (b) social syndication — public-tier card auto-posts to LinkedIn / X / Bluesky on consent, (c) Witness Roster activation — when someone names a witness, witness gets pinged to confirm.*

## Coherence Multiplier (self-rated)

Self-rate: **+1.7**.

**Paradigm Shift type** — the network now has matchable nodes. Without character cards, players were just signatures on a roll. With them, the substrate can *route* — offers find needs, quests find collaborators, witnesses find proofs to sign. The whole network becomes legible.

The reuse of the champion-sign pattern (third extension after sign + proof) means the substrate's pattern is now battle-tested: each new endpoint takes ~30 lines of FastAPI, 30 lines of cockpit JS, and a deploy.

External triangulation pending.

## What changed in the player journey

The conversion sequence is now:

```
Land → Read Manifesto inline (no popup)
     → Sign World Peace Agreement (Champion # within 60s)
     → Build Character Card (5 min · AI Port-In)  ← NEW
     → Run 7-Day First Game (AI prompt facilitates)
     → File Proof (web form, founder pings on submit)
     → Witness signs (off-page or future flow)
     → Ascend Player Path
```

Each step substrate-driven. None require James in the manual loop.

## Renewal

Loop 12 complete. **Twelve loops in 36 hours. Six Paradigm Shifts.**

The Game now has:
- Identity layer (Manifesto + CHRIST principles)
- Architecture layer (Framework, Ecosystem, Loop)
- Ratification layer (signed Agreements, witnessed)
- Onboarding layer (Sign + Card + Game prompt)
- Submission layer (Champion file + Proof file + Card file)
- Signaling layer (Field Pulse + founder Telegram + /projects)
- Cross-project layer (Sessions API + global session-state hook)

The substrate is dense. The Game plays itself across the full player arc.

---

*Compiled inside the Game, by the Game, for the Game.*
*Twelve loops shipped. Six Paradigm Shifts. The network has matchable nodes.*
