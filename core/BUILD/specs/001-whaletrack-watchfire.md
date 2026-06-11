# SPEC 001 — Whaletrack Watchfire: make AI-managed funds protect themselves

## Intent
Live AI trading on Hyperliquid (real wallet, ~$431) auto-trades strategy `sweep_signal`
via systemd service `whaletrack-magnet`. A stop-loss/take-profit block was added to the
adapter (2026-05-24) but the live wallet shows **zero resting trigger orders** across all
history — the fix never fires. Two open shorts (ETH, SOL) currently have NO protective
orders. This is a "Watchfire" gap (Full Potential OS): money does work but the system
fails to guard itself. Make it conscious = every open position ALWAYS has a stop.

## Host & files  (SSH root@198.54.123.234)
- Executor:  `/opt/fpai/services/whaletrack-magnet/core/live_sweep_executor.py`
             (`maybe_execute` → `_do_entry` calls `adapter.open_position(sym,side,usd,lev,stop,target)`)
- Adapter:   `/opt/fpai/services/whaletrack-live/app/hyperliquid_sdk_adapter.py`
             `open_position()` has an SL/TP block; `place_stop_loss` (~L437),
             `place_take_profit` (~L440), `_place_trigger_close` (~L390), `close_position` (~L268)
- Audit log: `/opt/fpai/services/whaletrack-magnet/data/live_trades/sweep_signal_real.jsonl`
- Env: `SWEEP_LIVE` (kill switch), `SWEEP_LIVE_MAX_POSITIONS`, `_ACCOUNT_FLOOR`,
       `_PER_TRADE_CAP_PCT`, `_DAILY_LOSS_LIMIT_PCT` (systemd drop-in `sweep-live.conf`)
- Creds: EnvironmentFiles `/etc/fpai/ai.env` + `api/.env`; vars `HYPERLIQUID_API_SECRET`,
         `HYPERLIQUID_MAIN_ACCOUNT`. NEVER print/log/commit these.
- Read-only market/account: `POST https://api.hyperliquid.xyz/info`
  types `frontendOpenOrders`, `clearinghouseState`, `allMids` (user = main account).

## KNOWN ENVIRONMENT BUG (fix first — likely the real root cause)
On this host `python3` is broken for the trading code path:
- `/usr/local/lib/python3.10/dist-packages/typing.py` is a stale `typing` **backport** that
  shadows stdlib `typing` whenever dist-packages precedes stdlib on `sys.path`. Symptom:
  `AttributeError: type object 'Callable' has no attribute '_abc_registry'` and
  `module 'inspect' has no attribute 'signature'` (breaks @dataclass / SDK import).
- `/usr/lib/python3.10/sitecustomize.py` prints diagnostics and runs on every interpreter.
**Hypothesis:** the auto-stop placement throws under this broken env and is swallowed, so no
trigger order is ever placed. Verify, then make the trading process import-clean (e.g. uninstall
the `typing` backport: `pip uninstall typing`, or pin sys.path so stdlib wins) and confirm
`open_position`'s SL/TP path actually executes.

## Tasks (in order)
1. **Diagnose firing path.** Add structured logging around `place_stop_loss`/`place_take_profit`.
   Determine WHY no trigger lands (env crash? rejected params? wrong reduceOnly/tpsl?). Write
   findings to `docs/analysis/WHALETRACK_WATCHFIRE_DIAGNOSIS.md`.
2. **Repair** so a stop AND take-profit trigger order is placed and **confirmed resting** on HL
   immediately after every entry fill. After placing, re-query `frontendOpenOrders` and assert the
   trigger exists; if not, log loudly + audit a `phase: stop_unconfirmed` event. Never let an entry
   sit unprotected silently.
3. **Reconciler** — new module `core/position_protection_reconciler.py`. Each run: list open
   positions, list resting triggers, and for any position missing a stop (and/or TP) place one
   (from the originating audit entry, else a percent/ATR fallback). Idempotent. Add `--once` mode
   + a systemd timer (every 2 min). This retro-protects the 2 currently-open positions.
4. **Exit logging** — ensure `_do_exit` and any stop/TP fill writes `phase: exit` /
   `phase: stop_hit` / `phase: target_hit` audit records with realized PnL.
5. **Mirror report** — `tools/whaletrack_verdict.py` joins live audit trades vs paper `sweep_signal`
   trades over the same window; outputs per-trade and aggregate paper-would-have vs live-actual
   (PnL, win-rate, slippage, drawdown) as markdown.

## Hard constraints (THE GATE)
- Reversible: each change a separate commit on a **branch**; back up edited files (`.bak.<date>`).
- NEVER modify the entry-success path so an entry could fail to fill. SL/TP/reconciler failures
  DEGRADE LOUDLY (log + audit), never roll back or block an entry.
- Respect kill switch: if `SWEEP_LIVE=0`, reconciler still PROTECTS open positions, never opens new.
- Do not print/log/commit secrets.
- `py_compile` + run new unit tests before any `systemctl restart`.

## Tests (CODE IS LAW)
- Reconciler: position-without-stop → places stop; position-with-stop → no-op (idempotent);
  kill-switch-on → still protects, never opens.
- `open_position` SL/TP confirmation path with a mocked exchange.

## Acceptance criteria
- `frontendOpenOrders` shows a resting stop (and TP) for EVERY open position.
- A fresh auto-entry produces a confirmed resting stop within seconds (proven in logs).
- `whaletrack_verdict.py` emits a paper-vs-live report.
- Diagnosis doc explains the original dead-path / env root cause.
- All new tests green.

## Deliverables
Patched adapter + executor, `position_protection_reconciler.py` + systemd timer, verdict tool,
diagnosis doc, tests. A PR-style summary of what changed and how it was verified against the live
wallet (read-only checks only — no manual order placement from this build; protecting the 2 open
positions is handled separately by James/Ember).
