# 🐋 WHALETRACK + MAGNET TRADING STRATEGY — FULL SPEC v3.0

**A complete system architecture for liquidity-driven precision trading**

---

## 1. PURPOSE

Price does not move randomly.

Price moves toward **liquidity rooms** where whales can harvest stops and liquidations with the least energy.

**WhaleTrack** identifies where the whale is positioned and where they are heading.

**Magnets** identify the liquidity targets that will pull price toward them.

**You trade the path between whale position → magnet.**

Nothing else matters.

---

## 2. SYSTEM COMPONENTS

The system is composed of six core modules:

1. **Magnet Scanner** — Detects liquidity clusters and rates their attractiveness
2. **Whale Position Engine** — Shows where the whale is leaning (up, down, or fog)
3. **Flow Map** — Defines the most efficient path to the next magnet
4. **Entry Engine** — Determines optimal entry zones
5. **Exit Engine** — Determines magnet-front-run exits and sweep exits
6. **Reversal Engine** — Identifies high-probability reversals after liquidity sweeps

---

## 3. MAGNET DEFINITIONS

A **Magnet** is a price level that attracts price due to concentrated liquidity.

A magnet can be:
- Stop loss clusters
- Liquidation heatmaps
- Equal highs / equal lows
- Imbalances / FVG
- Unfilled volume gaps
- Volume nodes (HVN/LVN)
- Session extremes
- Wick vacuum zones

**Magnets = liquidity rooms the whale wants to sweep.**

---

## 4. MAGNET SCORING SYSTEM (0–100%)

Each magnet receives a score based on liquidity density and whale alignment.

- **+20%** — Liquidation cluster present
- **+20%** — Equal highs/lows (untapped)
- **+20%** — FVG / imbalance alignment
- **+20%** — Major volume node at level
- **+20%** — Direction matches whale momentum

**Scoring:**
- 80–100% = High probability target
- 60–79% = Medium target (only trade if path is clean)
- 0–59% = Ignore

---

## 5. WHALE POSITION ENGINE

This engine determines the whale's current intention using:
- Last sweep direction
- Displacement strength
- Candle velocity
- Orderflow pressure (delta, imbalance)
- Liquidity taken/not taken
- Structure (HH/HL vs LH/LL)
- Wick aggression

The whale can be in one of three states:

### A. Upward Pressure
- Strong green displacement
- Liquidity swept below
- Magnets above are cheaper

### B. Downward Pressure
- Strong red displacement
- Liquidity swept above
- Magnets below are cheaper

### C. Indecision Fog
- Chop
- Overlapping candles
- No clean sweeps
- Whale is not committed

---

## 6. FLOW MAP

The Flow Map is the heart of the system.

It answers only one question:

**➡️ Which magnet requires the least energy to reach next?**

Flow Map is determined by:
1. Last clean sweep
2. Whale direction
3. Distance to each magnet
4. Magnet probability score
5. Obstructions (support/resistance)
6. Candle velocity (fast = continuation)

The magnet with **highest score + lowest distance + clean path** is selected.

---

## 7. ENTRY ENGINE

You only enter when:
- Whale direction is clear
- Magnet target is high probability
- Path is unobstructed
- Distance-to-target offers enough room

### Entry Types

#### 1. Momentum Entry
Enter with the whale after displacement.

**Valid when:**
- Candle velocity is increasing
- Liquidity breakout just occurred
- Magnet is close but not yet hit

#### 2. Retrace Entry
Enter after a pullback into:
- Breaker blocks
- FVG
- Fair value zones
- Previous consolidation

#### 3. Reversal Entry (highest RR)
Only after:
- Liquidity sweep
- Whale velocity stalls
- Displacement flips
- Structure shifts

---

## 8. EXIT ENGINE

You exit at:

### A. The Magnet Itself
If price hits magnet — **EXIT**.

### B. Front-run the Magnet
Exit **0.1–0.3%** before the level to avoid reversal candles.

### C. After Sweep Snapback
If the magnet is swept violently:
- Exit the position
- Consider reversal setup

---

## 9. REVERSAL ENGINE

**Reversal conditions:**
- Magnet fully swept
- Large wick rejection
- Whale velocity shifts
- Displacement breaks structure
- Candle body closes opposite direction

**Reversal signals:**
- BOS
- CHoCH
- Break of countertrend structure
- Imbalance fill
- Delta reversal

**Reversal trades are low frequency, high precision.**

---

## 10. POSITION SIZING MODEL

Based on clarity of whale direction:

- **Clear direction** → 2–3× size
- **Uncertain** → 0.5× size
- **Reversal** → 1× size
- **High-leverage** → only if magnet is extremely close

---

## 11. RISK MODEL

- Max 1 open position per asset
- Max 2 trades per session
- Always exit before a magnet unless reversal conditions are present
- **Never long into a magnet above**
- **Never short into a magnet below**

---

## 12. DATA MODEL (STRUCTURE)

```python
WhaleState {
  direction: "up" | "down" | "fog",
  velocity: number,
  displacementScore: number,
  sweepDirection: "up" | "down" | "none"
}

Magnet {
  price: number,
  score: number,
  type: "liquidity" | "equal_highs" | "equal_lows" | "volume" | "imbalance",
  distance: number
}

FlowPath {
  selectedMagnet: Magnet,
  efficiencyScore: number,
  obstructions: number
}

Trade {
  entry: number,
  stop: number,
  target: number,
  type: "momentum" | "retrace" | "reversal"
}
```

---

## 13. FULL TRADE LOOP (SUMMARY)

1. Identify whale direction
2. Scan all magnets
3. Score each magnet
4. Determine cheapest path
5. Wait for alignment
6. Enter with whale momentum or on retrace
7. Exit at magnet or front-run
8. After sweep, check reversal
9. If reversal conditions hit → enter opposite
10. Repeat

---

## 14. ONE SENTENCE SUMMARY

**You follow the whale from its current position to the nearest high-probability magnet and ride the liquidity path with precision entries and exits.**

---

## IMPLEMENTATION STATUS

✅ **COMPLETE** — All 6 engines implemented
✅ **COMPLETE** — FastAPI endpoints for real-time signals
✅ **COMPLETE** — UDC compliance
✅ **READY** — Port 8600 deployment

### API Endpoints

- `POST /api/whale/update` — Update system with new candle data
- `GET /api/whale/status` — Get current whale position and system state
- `GET /api/magnets/current` — Get all current magnet levels
- `GET /api/flow/current` — Get flow path to target magnet
- `GET /api/signals/entry` — Get entry signal (if active)
- `GET /api/signals/exit` — Get exit signal (if active)
- `GET /api/signals/reversal` — Get reversal signal (if active)
- `GET /api/position/current` — Get current open position

### Bridge Service

`bridge/bridge_service.py` keeps the engines fed with live data and logs paper trades.

```
pip install -r bridge/requirements.txt
export WHALETRACK_API_BASE=http://localhost:8600
python bridge/bridge_service.py
```

Env overrides:
- `BRIDGE_EXCHANGE` (default `binance`)
- `BRIDGE_SYMBOL` (default `BTC/USDT`)
- `BRIDGE_MODE=paper|live`
- `BRIDGE_INTERVAL` seconds between fetch cycles

---

**Built by:** Full Potential AI Cockpit
**Version:** 2.0.0
**Status:** PRODUCTION READY 🚀

