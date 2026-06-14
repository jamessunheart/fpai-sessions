# SPEC · World Scout activation — light the Lantern

**Room:** Lantern (Constellation #2 — notice reality, outward) · **Status:** GO blessed by James 2026-06-10 · **Builder:** Codex · **Spec by:** Ember

## Intent (Buildstream Law: what this unlocks)
The system's outward eyes. Two feeds revive: `NEWS FOR YOU` (James-relevant world signal) and `AI GROWTH FEED` (capabilities the system should adopt). Unlocks: informed treasury/AI decisions without James scanning the web, and the scout→adopt pipe (`scout_adopt.py`) getting real input. Lantern moves 🟡→🟢 in `docs/codex/CONSTELLATION_MAP.md`.

## Current state (read first, don't rebuild)
- `tools/scout/scout.py` — LOCAL deterministic ranker, no network. Keep as-is (it's the verdict engine, not the eyes).
- `~/.config/fpai/scout/prompt.md` — the two research lanes, already written (lane 1 growth, lane 2 news). Dead since 2026-05-31.
- Vault `00_MEMORY/NEWS FOR YOU.md` + `AI GROWTH FEED.md` — landing notes; NEWS marked `status: stalled` (honest) on 2026-06-10.
- `tools/decisions/scout_adopt.py` — downstream adopter, runs in fpull.

## Build
`tools/scout/scout_run.py`:
1. Execute the research lanes from `prompt.md` via a web-capable model call (Claude API + web search; model per `tools/router/route.py` — Instrument Rack chooses, default haiku-tier for cost).
2. Write results into the two vault notes — preserve header/structure, stamp date, flip `status:` to `live (scout pipe · last run YYYY-MM-DD)`.
3. Append run cost to vault `COST LEDGER` + a one-line entry to `PROOF LOG`.
4. Register both notes in `tools/vault/freshness.py` MACHINERY map → the Watchfire owns their promises from then on.

## Wiring
Ride the existing daily cadence — add a guarded call in `daily_sync.py` gated to **once per day** (cursor file `~/.config/fpai/scout/last_run.txt`), not every 2h tick. NO new LaunchAgent (Reserved-Class: background jobs).

## Guardrails (Gate)
- Cost: **≤ $1.50/run · 1 run/day** → fits P2 maintenance bounds (≤$5/day). Log every run.
- Kill switch: `SCOUT_DISABLE=1` env or `~/.config/fpai/scout/.disabled` file.
- Failure mode: on any error, leave notes untouched and `status: stalled` — never write a half-result as live (fresh file ≠ fresh truth).
- No installs · no sends · no account creation. Research-read only.

## Proof (done =)
- First run writes dated NEWS FOR YOU with ≥3 linked items + AI GROWTH FEED with ≥2 candidates.
- `FRESHNESS CHECK` shows both sources green the following tick.
- Cost line in COST LEDGER. CONSTELLATION_MAP Lantern flipped with evidence link.

## Rollback
Revert the commit + touch `.disabled`. Notes return to honest `stalled`.
