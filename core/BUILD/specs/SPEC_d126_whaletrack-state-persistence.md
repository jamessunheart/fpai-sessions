# SPEC d126 — WhaleTrack engine state persistence (no-blackout restarts)

**Status:** QUEUED
**Stream:** Treasury/Watchfire
**Priority:** MEDIUM — reliability of the signal layer (consumed by coracle/aria/data-service)

## The gap

`WhaleTrackTradingSystem` (server 198, `whaletrack-magnet`) holds `last_state` and
`candle_cache` in memory only. On every `systemctl restart`, all per-symbol state is wiped
and `get_summary()` returns `{"status":"initializing"}` (HTTP 503) until each symbol
re-accumulates ~100 candles from its bridge. Observed blackout: ~3 minutes across BTC/ETH/SOL/XRP
during the 2026-06-25 symbol-API patch. Any code deploy that needs a restart silently dark-windows
the public `/whaletrack` page and every downstream signal consumer.

## What to build

Persist + rehydrate per-symbol engine state across restarts.

1. On each `TRADING_SESSIONS[symbol].update()`, write a compact snapshot to disk
   (`/opt/fpai/services/whaletrack-magnet/data/state/<symbol>.json` or sqlite):
   - last `candle_cache[symbol]` (last 200 candles) — enough to rebuild without waiting for live ticks
   - `last_state` summary fields (or enough to recompute on load)
   - timestamp
2. On startup, before serving, load the newest snapshot per symbol into `candle_cache` and
   replay `update()` once so `last_state` is populated immediately → no 503 window.
3. Guard: ignore snapshots older than N minutes (staleness) and fall back to live warmup.
4. Throttle disk writes (e.g. every Nth update or every 30s) to avoid IO churn.

## Guardrails

- Small blast radius: snapshot read/write must never raise into the request path
  (wrap in try/except, log + continue).
- Reversible: feature-flag via env `WT_STATE_PERSIST=1`; off = current behaviour.
- Backup main.py + trading_system.py before edit (`.bak.*` convention already in use).
- Do NOT silently create blank sessions on load (see existing comment at `/api/whale/update`
  handler — that bug previously collapsed whale confidence to 0 and silenced alerts).

## Proof

- Restart `whaletrack-magnet`; `curl /api/whale/status?symbol=BTC` returns full JSON within
  <5s (not 503) for all 4 symbols.
- Downstream consumers (coracle-engine, aria-command) see no 503 gap in their logs across the restart.

## Context

Surfaced during the 2026-06-25 WhaleTrack revival session (Ember + James). Fixes already shipped
that session: position-protection tick-size rounding bug, and `?symbol=` support on
`/api/whale/status` (was BTC-only). This spec closes the remaining reliability gap those fixes exposed.
