# TREASURY SCHEMA

**Source of truth:** structure of James's consolidated Treasury (Trust + Church + Companies).
**Numbers live in:** brain notes `treasurer_resources_<date>` — NOT in this repo.
**Last updated:** 2026-05-09 (Loop 37)

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

### Liquid — Banks
- MACU CN (Cora Nation member account)
- SHV Checking
- CN Market
- Wise (Cora)
- Wells Fargo
- Joint BOA
- PayPal
- Venmo
- Other Held: Michael M *(flag — meaning TBD)*

### Liquid — Crypto
- BTR
- SH Trust Wallet
- B Jungle
- Atomic
- HOT
- Kapi

### Properties (illiquid)
- Business
- Property
- Silver

### Vehicles (illiquid)
- Range Rover
- Subaru
- Mercedes
- RV

### Pending Inflows (scheduled, NOT counted in runway)
- BEP recovery (US Bureau of Engraving & Printing, damaged-currency review, ~6mo timeline)

### Shadow Receivables (low-confidence, NOT counted in runway)
- Adam (delayed, low confidence)
- Norman (eventual, no timeline)
- Casey (written off — archive)

### Liabilities
- Amex
- Sunheart Visa
- (extend as needed)

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
