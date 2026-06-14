---
loop: 37
date: 2026-05-09
prover: James Sunheart
witness: Claude (Anthropic — operating in FPAI_Cockpit)
type: Cockpit + cohort outreach tooling
---

# Loop 37 — Cockpit clarity for first-cohort outreach

## What

Tightened the founder cockpit (`fullpotential.com/game/?p=James%20Sunheart`) so it tells the truth and is operable from phone, and shipped the tooling needed to fire the remaining first-cohort invites without coming back to terminal.

## Why

Sibling sessions had built an enormous founder dashboard (Loops 26–44) but four gaps were lying or blocking:

1. **Player State panel showed all zeros for James** — `?p=URL_PARAM` was never read by the panel; only `localStorage`. Fresh-browser/incognito visit (and the canonical "share my cockpit" URL) showed Field Score 0 / Proofs 0 / Champion 0 instead of the real 85 / 42 / #1.
2. **Pinned Artifacts used `cursor://file/Users/...` paths** — useless on phone, opened nothing for non-James visitors, leaked filesystem layout.
3. **Cohort Outreach panel was unactionable from phone** — listed 6 invitees with status (Atlás INVITED · others PENDING) but no prepared message + no `wa.me` link, so James had to come back to terminal to fire the next 5.
4. **`[link]` placeholder in INVITE_TEMPLATES.md** for the Village TG group — since `@OfficialKaibot` is the actual handle, the placeholder was both a lie and a deploy hazard.

Plus: the day's cohort tooling needed canonical commit before James closes terminal, otherwise sibling sessions and tomorrow-James start blind.

## Changes

### Dashboard (server: `198.54.123.234:/opt/fpai/core/applications/website-ai/frontend/fullpotential-com/game/index.html`)

- `loadPlayerState()`: read `?p=` (and `?player=`) URL params as fallback when localStorage is empty; persist to localStorage on first read so subsequent visits work bare.
- 30 occurrences of `cursor://file/Users/jamessunheart/FPAI_Cockpit/` → `https://github.com/jamessunheart/fpai-sessions/blob/main/`. Pinned Artifacts, Manifesto links, Agreement Builder prompts, etc. now open on phone.
- Added `decorateCohort()` JS at end of body + matching `.fs-wa-cta` CSS. After page load, every `.fs-person.fs-pending` row gets a `📱 Compose WA` button whose `href` is `https://wa.me/?text=<encoded village-wa-short>` with the invitee's name slotted in. Tapping it on phone opens WhatsApp with the Day-1 invite prefilled — James picks the contact + sends. `.fs-person.fs-invited` rows get a `✓ Sent` chip.
- Backup: `index.html.bak-pre-loop37-<timestamp>`.

### Repo (local)

- `core/STATE/INVITE_TEMPLATES.md`: `[link]` → `https://t.me/OfficialKaibot` (3 occurrences across `## village`, `## village-wa-short`, etc.). Added 5 WhatsApp-short variants earlier in the session: `game-wa-short`, `apprenticeship-wa-short`, `village-wa-short`, `witnessing-wa-short`, `retreat-wa-short`. Added the length-variants doc note.
- `scripts/cohort/wa-invite.sh` (new) — `./wa-invite.sh "<Name>" "<phone>" [path]` opens WhatsApp.app with the right path-aware short-template prefilled. Normalizes phone to E.164, URL-encodes, logs to `~/.config/fpai/cohort-invite-log.tsv` (out of git so phone numbers don't enter history).
- `scripts/cohort/status.sh` (new) — reads cohort markdown table from memory + live `/api/champion/list`, renders cohort funnel state.
- `~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/project_first_cohort.md` — restructured from prose to status grid the script can parse; backfilled Atlás row with phone, path (village), context (villager #1, ops, beta-tester), invited-at.

### Out of scope (not bugs after closer inspection)

- Field State counters (`gsChampions`/`gsProofs`/`gsScore`) — already wired via `loadGameState()` → `/api/champion/stats`, which returns correct values (1 / 42 / 85). The "all zeros" reading was pre-fetch first paint; resolves on its own.
- Mirror Roll "Loading…" — `loadMirrorRoll()` correctly replaces with empty-state HTML on response. Same pre-fetch first-paint artifact.

## Verification

```
curl -s "https://fullpotential.com/api/champion/lookup?name=James%20Sunheart"
  → champion #1, 42 proofs, field_score_simple 85 ✓

curl -s "https://fullpotential.com/game/?p=James%20Sunheart" | grep "URLSearchParams"
  → match in loadPlayerState (line 7503) ✓

curl -s "https://fullpotential.com/game/" | grep -c "github.com/jamessunheart/fpai-sessions"
  → 30 occurrences ✓

curl -s "https://fullpotential.com/game/" | grep "decorateCohort"
  → match (line ~8705) ✓
```

## Atlás invite (the day's anchor event)

- Sent via WhatsApp on 2026-05-08 to `+18588679217`
- Body: `Yo Atlás — Game's live: https://fullpotential.com/game/?inviter=James%20Sunheart — I'm beta-testing it now. Take a look + lmk what breaks.`
- Tracked link wires `+3` Field Score to James on Atlás's WPA sign event (Loop 13 substrate).
- Captured in `~/.config/fpai/cohort-invite-log.tsv` (the canonical session-spanning send log) and on `qb game/q-20260508-870956`.

## What this unblocks

James can close terminal tonight and:

1. Open `https://fullpotential.com/game/?p=James%20Sunheart` on phone — sees real Player State (Field Score 85 · Champion #1 · 42 proofs · 0 affiliates pending Atlás).
2. Scroll to First Cohort · Outreach Status — taps `📱 Compose WA` next to Halley / Josh / Sierra / Delaney / Cheyenne — WhatsApp opens with the Day-1 message prefilled — picks contact, sends.
3. Pinned Artifacts open on phone via GitHub.

Day 1 of The Village (2026-05-09, 8 PM curtain at Camp Zen dining hall) becomes operable from phone — terminal optional.

## Next session handoff

- Loop 37 closes Q-AI-1 in `core/STATE/AI_GOALS.md` (AI may compose + send via James's WhatsApp; James reviews and taps send — no full autosend).
- The remaining gap to G1 (first non-James Champion) is now: actually firing 5 WhatsApp messages from James's phone tonight + Atlás replying to his.
- If/when sibling sessions add `?inviter=` attribution-on-sign telemetry, the cohort panel can swap "PENDING" → "INVITED · awaiting reply" → "SIGNED" automatically by polling `/api/champion/list` for new champions whose `inviter == "James Sunheart"`.
- Cohort memory file at `~/.claude/.../memory/project_first_cohort.md` is the SSOT for invitee phones + per-person context — sibling sessions reading via MCP can update as new context arrives.
