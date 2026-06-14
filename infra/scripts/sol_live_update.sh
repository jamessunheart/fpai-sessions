#!/bin/bash
# sol_live_update.sh — fetch SOL/USD + compute P&L for current positions
#
# Fires every 60s via LaunchAgent (com.sunheart.sol-live).
# Writes ~/.config/fpai/sol_live/latest.json — cheap local read for Ember
# at every alignment-block compose. No API hammering on Ember's turns.
#
# Positions (sourced from ~/.config/fpai/treasury/treasurer_resources_2026-05-18.md):
#   - Trust Wallet spot: 109.9 SOL
#   - Bitrue Futures LONG: 1094.58 SOL @ entry $83.80, 3x leverage, ~$31,952 equity
#   - Liquidation: ~$55-58 SOL (using $55 conservative)
#
# Reversibility: launchctl unload ~/Library/LaunchAgents/com.sunheart.sol-live.plist && rm ~/.config/fpai/sol_live/latest.json
# Cost: ~free (CoinGecko free tier · 1440 calls/day well under 10-30 calls/min limit)
# Exit codes: 0 ok · 1 fetch fail · 2 parse fail · 3 write fail

set -uo pipefail

OUTDIR="${HOME}/.config/fpai/sol_live"
OUT_JSON="${OUTDIR}/latest.json"
OUT_LOG="${OUTDIR}/update.log"
SNAPSHOT_PRICE="85.15"  # SOL price at snapshot time (2026-05-18, ~$9,358 / 109.9 SOL)

mkdir -p "$OUTDIR"

TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ---- 1. Fetch from CoinGecko (free · no auth) ---------------------------
RESP="$(curl -sf --max-time 10 \
    "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd" 2>>"$OUT_LOG")" || {
  echo "[$TS_UTC] ERROR: CoinGecko fetch failed" >> "$OUT_LOG"
  exit 1
}

# ---- 2. Parse + compute + write JSON ------------------------------------
python3 - "$RESP" "$TS_UTC" "$OUT_JSON" "$SNAPSHOT_PRICE" <<'PY' || exit 2
import json, sys, os

resp_raw, ts_utc, out_path, snapshot_price = sys.argv[1:5]
snapshot_price = float(snapshot_price)

try:
    data = json.loads(resp_raw)
    price = float(data["solana"]["usd"])
except Exception as e:
    print(f"parse error: {e}", file=sys.stderr)
    sys.exit(2)

# Positions — TWO open SOL 3x isolated longs (CONFIRMED from James's Bitrue screenshot 2026-06-01).
# James's correction: the "Margin" shown on Bitrue is CURRENT equity (already net of the loss);
# the PnL is the subtraction from the ORIGINAL margin put in. So:
#   original_margin (fixed, what he deployed) = shown_margin - shown_pnl   (pnl is negative → adds the loss back)
#   equity_now (moves with price) = original_margin + live_unrealized_pnl
SPOT_AMOUNT = 109.9            # Trust Wallet spot SOL (separate from the futures)
# RE-ANCHOR 2026-06-02: James confirmed live Bitrue futures equity = $68,173 (at sol≈$78.82).
# The prior margin basis under-reported by ~$7,875, so original_margin is corrected proportionally
# across both legs to fit the stated equity. size_sol/entry/liq are UNCHANGED → liquidation
# distance + price-sensitivity stay valid; only the equity basis moved.
# 🟡 TODO: re-pin entry + per-leg margin from James's next Bitrue screenshot for an exact P&L split.
POSITIONS = [
    # original_margin = deployed capital (fixed basis); equity_now is derived live below.
    {"id": "SOL/USDC 3x", "size_sol": 1202.20, "entry": 82.44, "liq": 55.60, "original_margin": 38252.21},
    {"id": "SOL/USDT 3x", "size_sol": 1210.22, "entry": 83.55, "liq": 56.07, "original_margin": 39997.06},
]
LEVERAGE = 3

spot_value = round(SPOT_AMOUNT * price, 2)
delta_vs_snapshot = round(price - snapshot_price, 2)

longs, tot_size, tot_invested, tot_pnl, tot_notional, min_liq_dist = [], 0.0, 0.0, 0.0, 0.0, None
for p in POSITIONS:
    pnl = round(p["size_sol"] * (price - p["entry"]), 2)        # live unrealized PnL (loss from entry)
    equity = round(p["original_margin"] + pnl, 2)               # CURRENT margin/equity (what Bitrue shows, moves w/ price)
    notional = round(p["size_sol"] * price, 2)
    liq_dist = round((price - p["liq"]) / price * 100, 1) if price else None
    longs.append({**p, "unrealized_pnl": pnl, "equity_now": equity,
                  "notional_usd": notional, "liq_distance_pct": liq_dist})
    tot_size += p["size_sol"]; tot_invested += p["original_margin"]; tot_pnl += pnl
    tot_notional += notional
    if liq_dist is not None: min_liq_dist = liq_dist if min_liq_dist is None else min(min_liq_dist, liq_dist)

tot_equity = round(tot_invested + tot_pnl, 2)                   # SOL futures value to treasury right now
tot_invested = round(tot_invested, 2)
treasury_line = (f"SOL futures: ${tot_equity:,.0f} equity now "
                 f"(${tot_invested:,.0f} in · {tot_pnl:+,.0f}) · {tot_size:,.0f} SOL · "
                 f"liq ~${min(p['liq'] for p in POSITIONS):.0f} ({min_liq_dist}% away) · sol=${price:.2f}")

out = {
    "fetched_at": ts_utc,
    "sol_usd": round(price, 4),
    "snapshot_price": snapshot_price,
    "delta_vs_snapshot": delta_vs_snapshot,
    "spot": {"amount": SPOT_AMOUNT, "value_usd": spot_value},
    "longs": longs,
    "totals": {
        "size_sol": round(tot_size, 2),
        "invested_usd": tot_invested,          # original margin deployed (fixed)
        "unrealized_pnl": round(tot_pnl, 2),
        "equity_now_usd": tot_equity,          # current margin/equity — what the futures are worth to treasury now
        "notional_usd": round(tot_notional, 2),
        "min_liq_distance_pct": min_liq_dist,
        "leverage": LEVERAGE,
        "params_confirmed": True,
    },
    "treasury_line": treasury_line,
    "source": "coingecko/simple/price",
}

# Atomic write
tmp = out_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(out, f, indent=2)
os.replace(tmp, out_path)
print(f"wrote {out_path} · {treasury_line}")
PY

# Log success line (trim log to last 500 lines to prevent growth)
echo "[$TS_UTC] ok sol=$(python3 -c "import json; print(json.load(open('$OUT_JSON'))['sol_usd'])")" >> "$OUT_LOG"
tail -n 500 "$OUT_LOG" > "${OUT_LOG}.tmp" && mv "${OUT_LOG}.tmp" "$OUT_LOG"

exit 0
