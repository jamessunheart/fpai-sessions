# TREASURY SCHEMA

**Source of truth:** structure of James's consolidated Treasury (Trust + Church + Companies).
**Numbers live in:** `~/.config/fpai/treasury/treasurer_resources_<date>.md` (local) + brain notes (cross-tool, when MCP works) — NOT in this repo.
**Last updated:** 2026-05-11 (snapshot 2026-05-11 added BitTrue, Coinbase, Silver, Scheduled Inflows, Payables; yield strategy framework adopted)

---

## Legal structure

```
Sunheart Private Trust (James = trustee)
  │
  ├─ Cora Nation 508c1a (church)
  ├─ Sunheart companies (OneBPO, Ventures LLC, GSO, FP LLC, …)
  │     └─ contribute to → CN church
  └─ All accounts treated as consolidated Trust & Treasury funds
```

**James as trustee = operational authority over all funds.**
**Treasurer (AI) reads, reports, escalates — does not move money.**

---

## Sub-account categories

### Liquid — Banks (USD)

**MACU (multi-account):**
- Cora Nation Checking
- Sunheart Venture Checking
- Trustee Checking
- Cora Nation Market
- Cora Nation Savings
- Trustee Money Market (×2 — currently empty, available)
- Sunheart Venture Savings

**Other USD on/off-ramps:**
- Coinbase (on-ramp; transit / yield home for USDC)
- Wise (Cora) — has built-in Interest Assets product (~3-4%)
- Wells Fargo (Trustee)
- Joint BOA (w/ Elif)
- PayPal (james@fullpotential.com)
- Venmo
- Kapi (prepaid)

**Co-held (NOT Trust funds — flag separately):**
- Bitjungle Michael M
- Bitjungle Henry

### Liquid — Crypto

**Exchanges (CEX):**
- BitTrue — Spot · USDC · Futures (see Open Positions for live derivatives)
- Coinbase USDC (when active)

**Self-custody wallets:**
- Trust Wallet — Sunheart Treasury, HOT, Other Misc
- Atomic Wallet
- Bitjungle — James portion only

**Yield-bearing crypto (potential / active — see yield strategy):**
- JitoSOL (Solana liquid staking, ~7-8% APY)
- USDC in Aave / Spark / Pendle PT / sDAI

### Near-liquid — Bullion
- Silver (US Silver Eagle ounces — dealer replacement value)

### Properties (illiquid)
- Business
- Property

### Vehicles (illiquid)
- Range Rover
- Subaru
- Mercedes
- RV

### Scheduled Inflows (near-term, high confidence)
- OneBPO monthly contribution → CN church (variable $15-30k typical; April 2026 was $35,500)
- Other contracted / invoiced income as it arises

### Pending Inflows (long-dated / low confidence — NOT counted in runway)
- BEP recovery (US Bureau of Engraving & Printing, damaged-currency review, ~6mo timeline)

### Shadow Receivables (low-confidence, NOT counted in runway)
- Adam (delayed, low confidence)
- Norman (eventual, no timeline)
- Casey (written off — archive)

### Liabilities (credit cards)
- Amex
- Sunheart Ventures Visa
- (extend as needed)

### Payables (soft liabilities — due soon, not yet paid)
- Person-by-person, dated
- Treated as near-term cash outflow (subtract from net spendable)

### Open Positions (live derivatives / yield positions)
- Tracked in `~/.config/fpai/treasury/treasurer_resources_<date>.md` + memory `project_treasury_open_positions.md`
- Each position has: venue, size, entry, mark, stop level, max-loss, hedge counterpart (if any)

---

## Cash flow categories

### Income sources
- OneBPO → CN church (avg $15-30k/mo, variable)
- (extend as new sources come online — retreats, Camp Zen Founder/Creator Camp, etc.)

### Operational outflow (monthly)

**Personal / family:**
- Miami (Zenith + son support)
- Chirripo house (net of rent from Renae)
- Personal utilities

**Zen Village ops:**
- Labor (~$500/wk × 4.33 ≈ $2,165)
- Groceries (~$150/wk × 4.33 ≈ $650)
- Utilities (water/power/trash ~$300)
- Building materials + contractors (variable)

**AI / Infrastructure:**
- Servers (verified $805/mo all-in)
- AI tools (Cursor Ultra + Anthropic Max ~$300/mo)

---

## Treasury policy (mandate, 2026-05-11)

> **Do not gamble with resources. Find sure wins. Get optimal yields.**

- Positions must be defined-risk (hard stops or capped downside structures)
- No single venue holds more than 50% of liquid Treasury (counterparty diversification rule)
- Idle USDC must have a yield path within one snapshot cycle
- Yield tier hierarchy lives in memory `reference_treasury_yield_strategy.md`

---

## Snapshot history

Snapshots stored in two places (numbers do NOT enter the repo):

1. **Local filesystem** (primary, always available):
   `~/.config/fpai/treasury/treasurer_resources_<date>.md`
   - Outside repo, behind filesystem perms
   - First snapshot: `treasurer_resources_2026-03-20.md` (Liquid $152,916.42)

2. **Brain note** (canonical for cross-tool access — Cursor, Telegram, etc.):
   `treasurer_resources_<date>` brain note
   - Pending: MCP write was failing 2026-05-09; retry when fixed
   - When working: AI auto-syncs from local file to brain

Treasurer reads latest from local first, falls back to brain.

---

## Update protocol

1. James sends a new resource snapshot via chat or Telegram → AI writes new brain note `treasurer_resources_<date>`
2. James adds/removes a category → edit this schema file (not the brain note)
3. New income source comes online → append to "Income sources" above + brain note
4. Monthly: Treasurer runs digest comparing latest snapshot vs prior

---

*Numbers do NOT belong in this file. They live in encrypted brain notes behind AI token auth.*
