---
proof_id: 2026-05-08_james-sunheart_loop-22
loop_number: 22
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
---

# Loop 22 — James Sunheart

**Quest:** Port Adam's regenerative-discipline IP into `@sunheartbrain_bot` so the active brain inherits the cost/value hygiene that kept Adam from being a money pit. While in the file, also expose live server/hosting status as `/servers` per founder ask.

**Founder directive driving this loop:**
> *"I used to have Adam working on openclaw api etc. and I wonder what's useful or valuable from Adam telegram bot / brain that we had before that we can transfer over to the sunheart brain"*
>
> Plus mid-loop: *"Can you make sure that when I type /servers into sunheart brain it also has stats and details about currently active servers and hosting"*

## Offer

> **Three new bot commands + two nightly jobs that put Adam's hardest-earned discipline into the active brain:**
> - **`/roi`** — yesterday's cost-vs-engagement ledger (bot replies, James messages, est cost, value proxy, alerts).
> - **`/opportunities`** — on-demand run of the daily proactive scan (silent if nothing).
> - **`/servers`** — live server inventory + brain-host vitals + brain-service systemctl status + public-surface HTTP pings.
> - **`brain-curator-roi.timer`** — nightly 23:55 ROI ledger row + threshold alerts.
> - **`brain-curator-opportunities.timer`** — morning 08:15 proactive scan, silent unless there's a real deliverable.

## What got built

### `curator/jobs/roi.py` — daily ROI ledger
- Reads `brain_index.tg_messages` for the owner over the last 24h, grouped by role.
- `bot_replies_24h` is the Claude-call proxy (each bot reply ≈ 1 LLM call).
- `est_cost_usd_24h` = `bot_replies_24h × COST_PER_CALL_USD` (default $0.03, configurable via `SH_ROI_COST_PER_CALL_USD`).
- `value_proxy_james_per_bot_reply` = james_in / bot_out when bot_out > 0.
- Appends one JSON row per run to `/var/lib/sh-brain/roi.jsonl`.
- **Self-throttle alert**: bot_out > 50 AND james_in == 0 → Telegram ping.
- **High-burn alert**: bot_out > 100 → Telegram ping.
- The thresholds are exactly what Adam learned by burning real money before metaclaw was killed (2026-04-30).

### `curator/jobs/opportunities.py` — daily proactive scan
Gathers cheap signals (no LLM cost):
- NOW.md priority + GOALS + OPEN QUESTIONS sections (parsed from synced state file)
- Recent owner Telegram messages (last 48h, top 20)
- Yesterday's ROI ledger row (cost discipline context)
- Brain digest (chunks added 24h)
- Game KPIs (champion list, leaderboard, retreat interest — best-effort)

One LLM call (`curator.llm.complete`, force_json=False) → strict 3-opportunity format. **Silence rule**: if the model emits `NONE — keeping quiet today.` the job logs but sends no Telegram message. Otherwise the deliverables go to James via `tg.send`. Every run appends a JSON row to `/var/lib/sh-brain/opportunities.jsonl` regardless.

This is the load-bearing piece of Adam's IP: *$0 is a valid output*. The daily nudge stops being noise the moment it learns to keep quiet.

### `tgbot.py` — three new commands
- **`/roi`** reads the tail of `roi.jsonl` and renders the most recent row: bot replies, James messages, est cost, value proxy, alerts, lifetime totals.
- **`/opportunities`** runs the scan on demand, fire-and-forget; sends a "kept quiet" line if the model returns NONE.
- **`/servers`** combines four sources:
  - **NOW.md `### Servers`** subsection (canonical inventory: Primary 198.54.123.234, Brain 162.0.208.88, Legacy 209.74.93.72)
  - **Brain-host vitals** from `/proc/{uptime,loadavg,meminfo}` + `shutil.disk_usage('/')` — load, mem%, disk%
  - **systemctl is-active** for `sh-brain-tgbot`, `sh-brain-index`, `sh-mcp-http`, `postgresql`, `ollama`
  - **HTTP pings** to the public surface: `fullpotential.com/`, `fullpotential.ai/`, `fullpotential.com/api/champion/list` (status code + ms)
- Help message updated; dispatcher branches added.

### Systemd timers
- `brain-curator-roi.timer` — `*-*-* 23:55:00 America/Denver` → `brain-curator@roi.service`
- `brain-curator-opportunities.timer` — `*-*-* 08:15:00 America/Denver` → `brain-curator@opportunities.service`

Both reuse the existing `brain-curator@.service` template — no new service unit needed, only the two timers and the two job modules.

### `curator.py` — dispatcher
Added `roi` and `opportunities` to the `_run()` job map and the docstring usage block. `python -m curator roi` and `python -m curator opportunities` are now valid invocations.

## Skipped (intentional)

What was tempting from Adam's stack but **not** ported:
- **`metaclaw` / `openclaw-gateway`** — disabled 2026-04-30 for cause; reviving the proxy would re-introduce the runaway loop these alerts now guard against. Direct `anthropic.com/v1/messages` via `curator.llm.complete` is the current path.
- **Ollama-first routing for classify/route** — sunheart-brain commits to a single quality path; an Ollama fallback re-introduces the cost-cutting noise that made Adam loud.
- **`zv-brain.sh` / brain-mesh-gateway tiered tokens** — superseded by sunheart-brain MCP + the `fpai_ai_token` convention.
- **`AGENTS.md` / `SOUL.md` / reply-hygiene docs** — high-value, but docs-only. Deferred to a later loop. The discipline lives in the *code* of these jobs (silent-when-empty, threshold alerts) before it lives in any orientation file.

## Verified

- Files created:
  - `SERVICES/sunheart-brain/curator/jobs/roi.py`
  - `SERVICES/sunheart-brain/curator/jobs/opportunities.py`
  - `SERVICES/sunheart-brain/curator/systemd/brain-curator-roi.timer`
  - `SERVICES/sunheart-brain/curator/systemd/brain-curator-opportunities.timer`
- Files edited:
  - `SERVICES/sunheart-brain/curator/curator.py` — dispatcher + docstring
  - `SERVICES/sunheart-brain/curator/tgbot.py` — `/roi` + `/servers` + `/opportunities` handlers + help message
- The bot file is committed on `feat/streasury-bot`. Deploy on the brain server is a separate step (rsync `curator/` to `/opt/sh-brain-src/`, drop the timer files into `/etc/systemd/system/`, `systemctl daemon-reload`, `systemctl enable --now brain-curator-{roi,opportunities}.timer`).
- The bot won't error on first run even if the ledger file is missing — `/roi` returns a friendly "no ledger yet" message; `/servers` degrades gracefully if `/proc/*` reads or systemctl probes fail.

## Witness

**Primary:** Claude (this session). Non-independent witness.

**Secondary:** the code itself. Both jobs are dispatcher-registered and discoverable by `python -m curator <job>`. The bot's command dispatcher routes `/roi`, `/servers`, `/opportunities` to the new handlers. Help text exposes them.

**Tertiary:** the next 24h of operation. The first nightly `roi` run will append a row; first morning `opportunities` run will either DM James three deliverables or silently log `NONE`. Either result is information.

## Consent Setting

**PUBLIC** — field-visible.

## Proof Log Fields

- **Agreement** — *Transfer Adam's regenerative-discipline IP into the active brain (`@sunheartbrain_bot`); also surface live server status as `/servers`.*
- **Output** — *Two nightly curator jobs (ROI ledger, opportunities scan), three new bot commands (`/roi`, `/opportunities`, `/servers`), two systemd timers. Adam's discipline now runs in the active brain instead of a retired one.*
- **Witness saw** — *Code present in repo on `feat/streasury-bot`; dispatcher registers jobs; bot routes commands; help message lists all three.*
- **Result** — *The brain that's actually shipping (`@sunheartbrain_bot`) inherits the alerts that would have caught the metaclaw runaway. Daily proactive scan is plumbed but disciplined to be silent when there's nothing to say. Server posture is one Telegram tap away.*
- **Next Quest** — *Loop 23 candidates: (a) port Adam's reply-hygiene doc as bot system prompt context; (b) `/roi` history view (last 7 days trend); (c) wire ROI alert thresholds to `core/STATE/NOW.md` so they're tuneable without code; (d) extend `/servers` with WhaleTrack + concierge surface; (e) actual outreach to land Champion #2 (the unblocking move per AI_GOALS.md G1).*

## Coherence Multiplier (self-rated)

Self-rate: **+0.6**.

**Feature, not Paradigm Shift.** The substrate didn't change — the active brain just inherited regenerative-discipline rails that the previous brain (Adam) earned the hard way. The value is preserved-knowledge: alert thresholds tuned by real burn, a silent-when-empty norm calibrated by real noise.

The mechanic serves the receiver: James gets a daily three-deliverable nudge only when something's worth nudging about, plus a one-tap server snapshot, plus invisible nightly accounting that surfaces only when something's going wrong.

## What changed at the brain-discipline layer

| Before Loop 22 | After Loop 22 |
|---|---|
| `@sunheartbrain_bot` had no cost-vs-engagement accounting | Nightly ROI ledger writes one JSON row per day; `/roi` renders it |
| No alert if the bot started talking to itself | self_throttle (>50 calls, 0 James) and high_burn (>100 calls) alerts ping Telegram |
| No proactive daily surface — James pulls, brain never volunteers | Morning opportunities scan; volunteers 3 concrete deliverables OR keeps quiet |
| `/servers` didn't exist; server posture lived in NOW.md prose only | `/servers` shows live load/mem/disk + service status + public surface pings + NOW.md inventory |
| Adam's regenerative IP frozen in `infra/adam-workspace-patches/` | Live in `curator/jobs/{roi,opportunities}.py`, scheduled, integrated |

## Renewal

Loop 22 complete. The active brain now has the rails that kept Adam from drifting. The next move is the first non-James human (per AI_GOALS.md G1) — the substrate has had enough discipline added; what's missing is one player who isn't James.

---

*Compiled inside the Game, by the Game, for the Game.*
*Twenty-two loops shipped. The dead brain's hardest-earned lessons now run in the live brain.*
