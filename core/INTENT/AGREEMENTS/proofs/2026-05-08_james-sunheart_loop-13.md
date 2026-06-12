---
proof_id: 2026-05-08_james-sunheart_loop-13
loop_number: 13
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

# Loop 13 — James Sunheart

**Quest:** Ship the affiliate / invite-attribution mechanic + a Player State panel showing each Champion's metrics. Sharing the URL becomes load-bearing — when others sign through your link, your Field Score grows.

**Founder directive driving this loop:**
> *"a game needs some core metrics and clear actions / questions to get going... inviting others to game also makes other characters affiliates and can increase their score"*

**Agreement Type: Paradigm Shift** — seventh Paradigm Shift. The mechanic's significance: the Game stops being a solo practice and becomes a network where each Champion has *skin in the game* of inviting others coherently. Every share has measurable consequence.

## Offer

> **Every Champion gets a unique invite URL. The Player State panel shows their Champion #, loops filed, affiliates signed, Card level, Field Score, and the next adaptive action. Sharing the URL is now scoreable.**

## What got built

### Endpoint — `GET /api/champion/lookup?name=X`
- Returns: champion record + proofs_filed + affiliates (list and count) + card_present/level + field_score_simple
- Field Score formula (transitional, replaces full CPI which remains aspirational):
  - **1** for being a signed Champion
  - **1** for having a Character Card
  - **2** per Proof filed
  - **3** per Affiliate (someone who signed naming you as inviter)
- Privacy-preserving: emails stripped; private affiliates show as "(private)"

### Champion front-matter extended
- New optional field: `inviter` — recorded in the champion file's YAML when the signer arrived via `?inviter=NAME` URL
- Lookup counts matching `inviter` values as the player's affiliates

### Inviter capture (cockpit JS)
- Reads `?inviter=` from URL on page load
- Persists to localStorage (`fpai-cockpit-inviter`) so attribution survives across visits
- New **Inviter Banner** at top of page when present:
  > *"You arrived through [Name]'s invite. When you sign, they're credited as your inviter — their Field Score grows alongside yours."*
- Sign payload now includes `inviter` field

### Player State Panel (cockpit)
- Renders for any visitor whose localStorage has their name AND who has substrate presence (champion / proofs / card)
- Shows: 🎮 their name, **Field Score** prominent, and four stat cards (Champion # · Loops filed · Affiliates signed · Card level)
- **Their unique invite URL** with copy button
- **Adaptive next-move tip**:
  - "→ Sign the Agreement to become a Champion" if not signed
  - "→ Build your Character Card next" if signed but no card
  - "→ Run a 7-Day First Game and file your first Proof" if no proofs
  - "→ Share your invite link..." if no affiliates
  - "→ You're moving. Keep going..." if all four hit

### Bring-a-Friend invitation upgraded
- Generated invitation URL now includes `?inviter=PLAYER_NAME`
- Adds "From: [name]" attribution to the invitation text
- WhatsApp / email / clipboard share methods all use personalized URL

### Deploy step extended
- `tools/deploy_game.sh` now also rsyncs the repo's seed `champions/`, `proofs/`, and `cards/` into `/var/lib/full-potential/` on the server
- This way the lookup endpoint sees both seed data (committed to git) AND webhook-submitted data (live signatures)
- Submissions never overwritten — submissions and seeds coexist

## Verified

- Live `/api/champion/lookup?name=James%20Sunheart` returns: Champion #1 · 12 proofs filed · Field Score 25
- Cockpit page renders `playerStateCard`, `inviterBanner`, `psInviteUrl` elements correctly
- Bring-a-Friend now produces personalized URLs with `?inviter=` query param

## Witness

**Primary:** Claude (this session). Same caveat — non-independent witness.

**Secondary:** the live system. Lookup returns substrate-accurate data (12 proofs files visible, etc.).

**Tertiary:** GitHub. Commit `038ab45e` pushed.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — what was promised: *Ship Player State + invite attribution + affiliate counter.*
- **Output** — completed: *Lookup endpoint, front-matter inviter field, capture JS, Inviter Banner, Player State Panel, personalized invite URLs in Bring-a-Friend, deploy-step seed sync.*
- **Witness saw** — *Live lookup for Champion #1 returned Field Score 25 with 12 proofs counted; cockpit renders all new elements; deploy script verified to sync seed files.*
- **Result** — what changed: *The Game now has a viral primitive. Every Champion has measurable incentive to share coherently — affiliates worth 3 points each. The Player State panel makes "what am I doing, how am I scoring, what's my next move" visible at a glance for any visitor who's identified themselves.*
- **Next Quest** — *Loop 14: pick what's calling. Options: (a) public Player State pages — visit `?player=NAME` to see anyone's state, (b) leaderboard of top Champions / top loops / top affiliates, (c) match algorithm — given my Card's offers / needs / quests, who's compatible? (d) Store + currency (Coherent Credit issuance into the Treasury — biggest leverage but most complex), (e) Witness Roster activation.*

## Coherence Multiplier (self-rated)

Self-rate: **+1.7**.

**Paradigm Shift** — the Game now has a *network primitive*. Without affiliate attribution, sharing was theoretical. With it, every share has measurable consequence in the substrate. The mechanic is opt-in (URL parameter), reversible (lookup is read-only; a signer can omit the parameter), and serves the receiver (their Field Score grows by genuine network growth, not vanity metrics).

External triangulation pending.

## What changed in the network primitive

| Before Loop 13 | After Loop 13 |
|---|---|
| Sharing was theoretical | Sharing has measurable consequence |
| Champions had no metric of their network impact | Field Score = (Champion + Card + 2×Proofs + 3×Affiliates) |
| "Bring a Friend" produced generic URLs | Bring-a-Friend produces personalized invite URLs that credit you |
| No "what am I doing here?" view for the player | Player State panel shows Champion # · Loops · Affiliates · Card · Score · Next move |

## Renewal

Loop 13 complete. **Thirteen loops in 36 hours. Seven Paradigm Shifts.**

The Game has a viral primitive. Champions can compound. The substrate's network effects begin.

---

*Compiled inside the Game, by the Game, for the Game.*
*Thirteen loops shipped. The viral primitive is live. Every share now carries weight.*
