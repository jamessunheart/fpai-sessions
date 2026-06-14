---
proof_id: 2026-05-08_james-sunheart_loop-23
loop_number: 23
date_started: 2026-05-08
date_committed: 2026-05-08
player: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit, parallel terminal)
witness_signed: true
consent: public
agreement_type: feature
status: complete
mvs_increments:
  agreements_kept: true
  outputs_shipped: true
  transformations_witnessed: true
  resources_circulated: true
  clean_pauses: false
note_on_numbering: |
  Conceived in-session as "Loop 22" before sibling terminal's Loop 22
  (Adam discipline → sunheart-brain port) committed. Renumbered to
  Loop 23 at proof-write time per the established collision protocol.
---

# Loop 23 — James Sunheart

**Quest:** Three tightly-linked moves the architect requested:
1. Rename "Cards" → "Characters" everywhere user-facing so the existing `/characters` Telegram command matches the dashboard's terminology.
2. Add `/match` — a Telegram command that returns one specific helpful next move for a named Champion, computed from their current state.
3. Add `/game` — a vital-stats command for the architect to see the Game's current state at a glance.

**Founder directive driving this loop:**
> *"how about instead of cards we call them characters so that /characters work. Also we can start to test /match features and it matches you with one specific thing each time that might be helpful to move along in game. As architect I would like to see /game show me some vital game stats"*

**Agreement Type: Feature** — substrate-additive, terminology-aligning, surfacing the architect-side view that's been implicit until now.

## Offer

> **The Game's vocabulary aligns end-to-end. Champions build Characters (formerly Cards). A `/match` command returns one Game move scoped to your current state — not a list, not a recommendation engine, just one move that advances you. A `/game` command returns vital stats: 30-day goal status, Champion count, Characters built, proofs, affiliates, Field Score, retreat interest, weekly growth, latest loops.**

## What got built

### 1. Rename Cards → Characters (frontend)
- All user-facing labels in `tools/gen_cockpit_map.py` swept:
  - "Character Card" → "Character" (every occurrence)
  - "Cards built" KPI → "Characters built"
  - Player State pill `🎴 Card ${level}` → `🎴 Character ${level}`
  - Mobile stage bar `→ Build Card` → `→ Build Character`
  - Funnel arrow narrative `Sign → Card → Proof` → `Sign → Character → Proof`
- API endpoint paths kept stable (`/api/champion/card/submit` still works) — internal-only, no breaking change to the brain-bot's existing `/characters` data fetcher.
- CSS class names (`.character-card-quest`) left as-is for diff hygiene.

### 2. New `/api/champion/match` endpoint (champion-sign service)
- Reads player state via existing lookup logic.
- Returns one move based on hard gates first (no Champion → sign · no Character → build · no Proof → file · no Affiliate → share invite), then random selection from soft moves (retreat, paths, file another, deepen affiliate, witness another) once all four milestones hit.
- Each move includes: `move` (text), `icon`, `action` (machine-friendly tag), `url` (deep link to the relevant section).
- Anonymous call (no name) returns the universal "sign first" move. Useful for cold cockpit visitors.

### 3. New `/match` Telegram command (sh-brain-tgbot on `162.0.208.88`)
- Defaults to "James Sunheart" when no name provided. Override: `/match Some Name`.
- Calls `/api/champion/match`, renders icon · move · action URL · action tag.
- Best-effort — degrades to a friendly error when the API is unreachable.

### 4. New `/game` Telegram command (sh-brain-tgbot)
- Composes vital stats from three existing endpoints in parallel: `/api/champion/stats`, `/api/retreat/stats`, `/api/champion/leaderboard`.
- Renders:
  - **30-day goal status** — explicit ✓/✗ on whether `champions ≥ 2` (first non-James human in)
  - Champions (total · public)
  - Characters built
  - Proofs filed (total · public)
  - Affiliate links generated
  - Field Score sum
  - Retreat interest (total · public)
  - Growth this week
  - Latest 3 loops with player + quest preview
- Architect-grade single-screen read.

## Verified

- **Frontend rename:** Live page (`https://fullpotential.com/game/`) returns 34 occurrences of "Character" and "Cards built" no longer present.
- **`/api/champion/match` endpoint:**
  - `?name=James%20Sunheart` returns *"Build your Character. Open the AI Port-In prompt..."* — correct gate (James has 0 Characters).
  - Anonymous call returns *"Sign the World Peace Agreement to enter the Game."* — universal cold path.
- **brain-bot deployed:** rsynced `tgbot.py` to `/opt/sh-brain-src/curator/`, `systemctl restart sh-brain-tgbot` succeeded, service is `active`, journal shows `sh-brain-tgbot starting; polling messages + callback_query`.
- **`/match` and `/game`** are now in the bot's command handler and listed in `/help` text.

## Witness

**Primary:** Claude (this session). Same caveat — non-independent witness.

**Secondary:** the live deployed services. Frontend serves Character labels; `/api/champion/match` returns substrate-correct moves; brain-bot is polling.

**Tertiary:** GitHub. Commits land on `feat/streasury-bot` branch.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — what was promised: *Rename Cards → Characters, ship `/match`, ship `/game`.*
- **Output** — completed: *Frontend rename swept; `/api/champion/match` endpoint deployed to primary; `/match` + `/game` Telegram commands deployed to brain-bot.*
- **Witness saw** — *Live page serves new terminology; match endpoint returns correct gated move for James (Build Character); brain-bot service active and polling after restart.*
- **Result** — what changed: *The Game's vocabulary aligns. The architect can ask `/game` for a single-screen vital read. Any Champion can ask `/match` and get one specific move scoped to their state — not a list, not advice, the single move that advances them.*
- **Next Quest** — *Loop 24 candidates: (a) `/match` button on the Player State panel itself (so a logged-in cockpit visitor can hit one move on demand without leaving the page), (b) per-path interest capture (`/api/path/interest` generic + buttons on Forming-status path tiles), (c) email confirmation on retreat-interest submit, (d) the founder-side play: James actually fills his own Character + sends his invite link to one specific person.*

## Coherence Multiplier (self-rated)

Self-rate: **+1.4**.

**Feature loop, not Paradigm Shift.** The substrate added one new endpoint and two Telegram commands; the rename was cosmetic but vocabulary-aligning. The compounding effect comes from `/match` itself being a forcing function: every time a Champion runs `/match`, they get *one* move. That single-move framing is the antidote to "what should I do?" overwhelm — the Game answers with one move at a time.

## What changed at the architect-side surface

| Before Loop 23 | After Loop 23 |
|---|---|
| "Cards" on dashboard / "characters" in Telegram — vocabulary mismatch | All surfaces say "Character" |
| No way to ask "what should I do next?" from Telegram | `/match` returns one specific scoped move |
| Architect had to read multiple endpoints to see Game vital stats | `/game` composes goal status + 9 vital stats + latest loops |
| Cockpit visitor identifies → sees Player State, but next move was a paragraph | `/match` returns next move as exactly one thing |

## Renewal

Loop 23 complete. **Twenty-three loops in 36+ hours. Ten Paradigm Shifts.**

The architect now has a vital-stats console (`/game`). Every Champion has a one-move oracle (`/match`). The vocabulary aligns.

The next move that matters is still the same one Loop 21 surfaced: **James plays his own Game once.** The substrate is now refined enough that the founder-side play takes minutes, not loops. `/match` will tell him exactly which move when he asks.

---

*Compiled inside the Game, by the Game, for the Game.*
*Twenty-three loops shipped. Cards became Characters. Match returns one move. Game shows the field at a glance.*
