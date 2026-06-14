---
proof_id: 2026-05-08_james-sunheart_loop-25
loop_number: 25
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
  resources_circulated: true
  clean_pauses: false
note_on_numbering: |
  Conceived in-session as "Loop 23" before sibling terminal's Loops 23
  (Cards → Characters · /match · /game) and 24 (/match in-Game) committed.
  Renumbered to Loop 25 at proof-write time per the established
  collision protocol.
---

# Loop 25 — James Sunheart

**Quest:** Add `/capabilities` to `@sunheartbrain_bot` so James can ask the brain what the system can do — with dates each capability was added — and get a curated, queryable answer instead of guessing or grepping git log.

**Founder directive driving this loop:**
> *"can we create a /capabilities that will show capabilities of our system (what can our system do) and also dates when they were added"*

## Offer

> **A new SSOT (`core/STATE/CAPABILITIES.md`), a Telegram command (`/capabilities`), and a sync-script extension that pushes the file to the brain server alongside NOW.md.** The system now has a single answer to "do we have X?" / "when did we ship Y?" — and that answer is one Telegram tap away.

## What got built

### `core/STATE/CAPABILITIES.md` — third-tier SSOT
~75 entries across nine categories: Game, Sunheart Brain, Inquiry & Coordination, Economics & Money, Trading & Signals, Infrastructure, Village, Other Telegram Bots, Deprecated/Retired. Each entry is a single line:

```
- **YYYY-MM-DD** · <name> · <status> — <short description>
```

Status icons: 🟢 live · 🟡 partial · ⚪ scoped/paused · ⚠️ deprecated. Seeded from NOW.md's "Loops Shipped" table (loops 1-16), loop proofs (17-24 incl. sibling-shipped Loops 23/24), the bot's command surface, the live infrastructure inventory, and the Deprecated/Retired list in NOW.md.

The file's update protocol mirrors NOW.md's: edit when something ships/retires/changes status, then run `sync_now_to_brain.sh`.

### `_cmd_capabilities` handler in `tgbot.py`
- Reads `/var/lib/sh-brain/state/CAPABILITIES.md` (synced from laptop).
- Parses sections (`## <emoji> <Title>`) and bullets into structured entries via `_parse_capabilities` + `_parse_capability_line`.
- Default render: top 8 entries per category with a "+N more" overflow hint, plus a footer listing all category aliases.
- Filtered render: `/capabilities <category>` shows the full list for one category. Aliases mapped: `game / brain / sunheart / inquiry / coordination / money / economics / trading / signals / infra / infrastructure / village / bots / deprecated / retired`.
- Surfaces the file's last-sync age so a stale answer is visible as stale.

### `sync_now_to_brain.sh` extended
After scp'ing NOW.md, the script now also scp's `CAPABILITIES.md` (if present) to the same brain-server state dir. One sync, both files, no new credential or endpoint added.

### `tgbot.py` help text + dispatcher updated
`/capabilities [category]` listed alongside `/now /goals /servers /roi /opportunities`.

## Verified

- `core/STATE/CAPABILITIES.md` written; updated mid-loop to include Loop 23/24 capabilities (Cards → Characters, `/match` Telegram + in-Game, `/game` command, "What's my next move?" button) after sibling-collision discovery.
- `sync_now_to_brain.sh` ran cleanly, pushed both files: `synced NOW.md → ...` and `synced CAPABILITIES.md → ...`.
- Bot rsynced, parse-checked, restarted twice (initial deploy + post-cleanup). `systemctl is-active sh-brain-tgbot` → `active`.
- Smoke-tested the parser on the brain server (`python -c "asyncio.run(t._cmd_capabilities(''))..."`) — output renders cleanly: section headers + dated bulleted entries with status icons + "+N more" overflow hints. `/capabilities brain` filters to the Sunheart Brain category as expected.

## Witness

**Primary:** Claude (this session). Non-independent.

**Secondary:** the live deployed bot. James can type `/capabilities` or `/capabilities game` on `@sunheartbrain_bot` and see the rendered output now.

**Tertiary:** the file itself. `core/STATE/CAPABILITIES.md` is a markdown SSOT — anyone (any AI session, any future James) can read it directly without going through Telegram.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — *Build a `/capabilities` command that surfaces what the system can do and when each capability shipped.*
- **Output** — *`core/STATE/CAPABILITIES.md` (curated SSOT) + `_cmd_capabilities` handler with optional category filter + `sync_now_to_brain.sh` extension. Deployed and verified live.*
- **Witness saw** — *Sync script pushes both files; bot restart succeeds; smoke test renders correctly grouped output with date/status/description per entry; category filter works.*
- **Result** — *The system can now answer "what can you do?" with timestamps. Cuts down on re-explaining infrastructure to AI sessions and to James himself. Adds a maintained inventory that can be diffed over time to see what shipped this week vs last.*
- **Next Quest** — *Loop 26 candidates: (a) auto-append loop entries to CAPABILITIES.md from `feat(loop-N)` commits via post-commit hook (so the file maintains itself); (b) `/capabilities since YYYY-MM-DD` filter; (c) port Adam's reply-hygiene rules; (d) WhaleTrack auth wiring (X-API-Key per-user — see Loop 25 follow-up note); (e) the unblocking move per AI_GOALS.md G1 — the first non-James human.*

## Coherence Multiplier (self-rated)

Self-rate: **+0.7**.

**Feature, not Paradigm Shift.** The substrate didn't change — but the system now declares its inventory. Three SSOTs now sit side-by-side in `core/STATE/`:

| File | Question it answers |
|---|---|
| `NOW.md` | What's the current priority? |
| `AI_GOALS.md` | What's the AI working toward? |
| `CAPABILITIES.md` | What can the system already do? |

The trio gives any AI session — and James — orientation across **time**: NOW (this week), GOALS (the next 30 days), CAPABILITIES (everything shipped since day one). That's a small but real coherence gain at the human-AI seam.

## What changed at the system-orientation layer

| Before Loop 25 | After Loop 25 |
|---|---|
| "Do we have X?" required grepping the repo or asking James | `/capabilities` answers, with dates |
| Capability dates lived only in proof files (good narrative, bad index) | One-line index per capability; the proofs remain canonical narrative |
| Three SSOTs needed (NOW + AI_GOALS + capabilities) but only two existed | Trio complete: priority / goals / capabilities |
| No way to see deprecated/retired things at a glance | Dedicated section, dated, with reason |

## Renewal

Loop 25 complete. Twenty-five loops shipped. The system now declares — to itself, to its operators, and to anyone who asks — what it can do. Next move stays: the first non-James human.

---

*Compiled inside the Game, by the Game, for the Game.*
*Twenty-five loops shipped. The system now indexes itself.*
