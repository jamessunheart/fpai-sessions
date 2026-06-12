---
proof_id: 2026-05-08_james-sunheart_loop-31
loop_number: 31
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

# Loop 31 — /store substrate · Coherent Marketplace

**Quest:** Open marketplace where anyone can list items. Items accessed with credits. Visibility ranking favors credit-accepting offers — incentivizes circulation.

**Founder directive:**
> *"Store items accessed with credits. Anyone can list something in the store. As admin/architect I would list Retreat in store.. or coaching sessions etc. credit accepted offers get priority over dollar accepted offers only.. hybrid offers are weighted based on how much credit they receive.. meaning store items that accept credit get more visibility etc. than just dollar store items etc."*

## What shipped

### Per-offer markdown at `/var/lib/full-potential/store/{slug}.md`
Frontmatter holds price (credits, USD, both), credit-share weight, tier, inventory, sold count, status.

### Three-tier visibility ranking
- **Tier 0 (top):** credit-only offers (price_usd null/0)
- **Tier 1 (middle):** hybrid offers, ranked within tier by `credit_share` desc
  - Where `credit_share = price_credits / (price_credits + price_usd × rate)`
- **Tier 2 (bottom):** $-only offers (price_credits null/0)

Within a tier, recency breaks ties.

### Endpoints
- `POST /store/post` — anyone with a handle can list (rate-limited, honeypot-protected)
- `GET /store/list?limit=N` — ranked list, returns tier + credit_share for each
- `GET /store/get/{offer_id}` — single offer detail
- `POST /store/buy` — atomic purchase (deducts credits via ledger, increments sold, marks sold-out at inventory cap)
- `POST /store/remove` — owner or admin can remove

### Telegram commands (`/store`)
- `/store` → top 12 offers, grouped by tier with header labels (💎 CREDIT-ONLY · ⚖️ HYBRID · 💵 USD)
- `/store buy <offer_id>` → atomic purchase with credits
- `/store mine` → your listings only

### Genesis offers (architect-listed)
Three architect offers seeded:
1. **Mirror Loop Witnessing Service** — 50 credits (tier 0, credit-only)
2. **1:1 Coaching with James** — 150 credits (tier 0, credit-only)
3. **First Costa Rica Retreat** — 500 credits + $1500 (tier 1, hybrid, credit_share 0.25, inventory 12)

Verification: `/store/list` returns Mirror Witnessing first, Coaching second, Retreat third — exactly the ordering James specified (credit-only ranked above hybrid).

## Why this matters

The marketplace's ranking algorithm makes credit acceptance the dominant economic signal. A merchant who lists in credits gets more visibility than one who lists in $. This pushes the field toward credit circulation even before any official credit-to-USD on-ramp exists. The Game's economy starts to play itself — same principle as everything else.

## Files

- `SERVICES/champion-sign/main.py` — `STORE_DIR`, `StoreOffer`, `StoreBuy`, `_offer_credit_share`, `_offer_tier`, `_read_offer`, 5 endpoints
- `SERVICES/fp-game-bot/main.py` — `cmd_store` (list/buy/mine), help text update

*— Sealed 2026-05-08*
