# Whaletrack Watchfire Diagnosis

Date: 2026-06-11

## Status

This Codex session could not reach the production host. A read-only SSH probe to
`root@198.54.123.234` failed with `Operation not permitted`, so the live files,
live Python path, systemd drop-ins, journal logs, and Hyperliquid account state
were not inspected from this sandbox.

That means the original dead path is not fully proven here. The known host bug
remains the leading hypothesis: a stale `typing` backport in
`/usr/local/lib/python3.10/dist-packages/typing.py` can shadow stdlib `typing`
and break imports used by dataclasses / the SDK before the SL/TP placement path
finishes.

## Repo-local findings

- The approved spec is present at `core/BUILD/specs/001-whaletrack-watchfire.md`.
- The exact production files named in the spec were not mirrored in this worktree:
  - `/opt/fpai/services/whaletrack-magnet/core/live_sweep_executor.py`
  - `/opt/fpai/services/whaletrack-live/app/hyperliquid_sdk_adapter.py`
- `_staged_repos/whaletrack-magnet-engine/` exists but is empty in this worktree.
- Older local trading helpers exist under `SERVICES/aria-command/trading/`, but
  they do not contain the specified `open_position(sym, side, usd, lev, stop, target)`
  adapter path.

## Repair artifacts added here

- `core/position_protection_reconciler.py`
  - Lists open positions and resting trigger orders through the live adapter.
  - Places missing stop-loss and take-profit trigger orders.
  - Re-queries open orders after placement and writes `stop_unconfirmed` /
    `target_unconfirmed` audit events if protection is not confirmed resting.
  - Does not open new positions and does not depend on `SWEEP_LIVE`; if the kill
    switch is off, it still protects existing positions.
- `infra/systemd/whaletrack-position-protection.service`
- `infra/systemd/whaletrack-position-protection.timer`
- `tools/whaletrack_verdict.py`

## Live-host verification still required

Run these on `198.54.123.234` before any restart:

```bash
python3 - <<'PY'
import inspect, sys, typing
print(sys.path[:8])
print(typing.__file__)
print(hasattr(inspect, "signature"))
print(hasattr(typing.Callable, "_abc_registry"))
PY
```

If `typing.__file__` points at `/usr/local/lib/python3.10/dist-packages/typing.py`,
remove or isolate the backport so stdlib `typing` wins for the trading process.

Then compile and test from the deployed service directory:

```bash
python3 -m py_compile \
  /opt/fpai/services/whaletrack-magnet/core/position_protection_reconciler.py \
  /opt/fpai/services/whaletrack-magnet/core/live_sweep_executor.py \
  /opt/fpai/services/whaletrack-live/app/hyperliquid_sdk_adapter.py
```

Finally, run the reconciler once with live adapter logging enabled and verify
`frontendOpenOrders` shows one stop and one take-profit trigger for every open
position. Do not restart `whaletrack-magnet` until compile and unit tests pass.

## Acceptance gap

The repo-local reconciler tests pass, but the live acceptance criteria remain
unverified here because the sandbox cannot SSH to the host or call Hyperliquid
with the live account. No manual orders were placed from this build.
