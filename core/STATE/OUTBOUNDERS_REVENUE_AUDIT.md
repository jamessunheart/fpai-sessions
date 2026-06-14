# Outbounders.com Revenue Audit — 2026-05-23 (CORRECTED)

**First-time wiring of outbounders revenue into cockpit.** Source: direct SQL read against `obapp_outbounders` DB on server 209.74.93.72. Marketing site `outbounders.com` and live app `app.outbounders.com` audited; production untouched.

## ⚠️ Correction: 2026-05-23 (same day)

The initial version of this audit claimed **$2.24M floating client balance**. **That was wrong.** Re-query scoped to clients with activity in the last 12 months returned **$0.00 across 32 active clients**. The $2.24M figure summed STALE ledger rows from 2013-2018 (top "client" #37712 shows $368K untouched since July 2018). Real active float = $0. Money flows through and is consumed within the cycle; nothing pools. The "yield on float" lever is removed from the recommendations below.

## The numbers (live read 2026-05-23, corrected)

| Metric | Value | Notes |
|--------|-------|-------|
| **REAL active float** (clients w/ 12mo activity) | **$0** | All 32 active clients show $0.00 balance — platform settles to zero |
| Stale ledger balance (2013-2018 ghosts) | ~$2.24M | Accounting cruft from long-dead accounts · not real money |
| Negative ledger balances (overdraft cruft) | −$243K across 55 accounts | More cruft to clean up |
| Deposits in (last 30 days) | $13,778 | Real money flow · clients adding funds |
| Deposits in (avg 18mo trailing) | ~$15-18K/mo | Stable |
| Agent payouts (last 30 days) | $13,182 | Money flowing OUT to outbounders/agents |
| Active paying clients per month | **6-12** | Across $15K+ in deposits |
| Active payroll-fee relationships | 946 | Platform's per-agent take · $3,784/cycle |
| Active "silver membership" subs | **0** | Dead product · 1 holdout was last $99/mo |
| Total registered users (lifetime) | **118,344** | 99%+ dormant |
| New signups (Jan 2025) | 1,756 | Healthy top-of-funnel |
| New signups (May 2026) | **75** | **23× decline** correlates with broken pages |

## The thesis (revised)

**Outbounders is a marketplace running on 6-12 monthly active clients with ~$15K/mo deposit flow that is fully consumed each cycle.** No float, no passive yield. The platform infrastructure works. The conversion funnel doesn't. Two cheap fixes (pricing page + /app redirect) shipped 2026-05-23; the strategic lever is BUILDING A BETTER PRODUCT before re-engaging the 118K dormant pool (per James 2026-05-23: "don't direct people back to the site until we have substantial improvements").

### Critical findings

1. **Signups crashed 23×** between Jan 2025 (1,756/mo) and May 2026 (75/mo). Strongly correlates with broken-funnel state of the marketing site. Today's fixes should be measured against this baseline.

2. **Membership product is dead.** `membership` table shows 0 active subscribers. Only one $99/mo "silver" was charged for most of 2025-2026, and even that lapsed. There's a built-out product layer collecting $0 right now.

3. **118K dormant user pool — DO NOT EMAIL YET.** James's direction: build substantial AI-augmentation first, re-engage with a real story, not a "we fixed our pricing page" story.

4. **No float to yield.** Earlier claim of $2.24M was wrong (see correction above). Money in = money out per cycle.

## Today's fixes (shipped 2026-05-23)

- ✅ Replaced `/pricing` Lorem Ipsum + fake $99-$250 tiers with real pricing (Clients $25 / Outbounders Free + How-It-Works + FAQ). Elementor JSON disabled, backed up to `_BACKUP_2026-05-23_*` postmeta keys.
- ✅ Redirected `/app` (StartIt theme placeholder w/ fake testimonials) → `https://app.outbounders.com/` via `.htaccess` rewrite rule.
- ✅ Backups of old state in `/tmp/wp_posts_pricing_app_backup_*.sql` + `/tmp/htaccess.outbndrs.bak-*` on server.

## Re-weighted bottleneck map (corrected · still 100%)

| Wt | Bottleneck | Why |
|---:|------------|-----|
| **27%** | Dormant 118K user pool unactivated | Largest pool — but don't fire yet; re-engage *after* substantial improvements |
| **22%** | Brand/SEO collapse + 23× signup decline | Gates every other lever |
| **18%** | **No AI-augmentation = no 2026 reason to choose Outbounders over Upwork** | The wedge that makes the platform actually better, not just functional |
| **13%** | Signup-flow friction | Multiplier on every traffic gain |
| **10%** | No recurring-revenue product (membership tier dead) | $0/mo subscription revenue today |
| **6%** | Pricing/fee opacity | Floor-fix today; deeper work pending |
| **3%** | Ops cost stack (labor unknown) | Diagnostic before optimization |
| **1%** | Payment method narrowness | Real but small |
| **100%** | | |

## Proposed build sequence — "substantial improvements before re-engagement"

| Phase | Build | Wks | Why |
|-------|-------|----:|-----|
| **P1** | AI script generator + objection handler | 1-2 | Differentiates immediately · visible value in 30 sec |
| **P2** | AI post-call coaching (transcripts → quality score) | 2-3 | Better agent output · client-side retention story |
| **P3** | Modern site rebuild (kill StartIt theme entirely) | 1-2 | "This is 2026 software, not 2013" · trust + SEO foundation |
| **P4** | Transparent pricing + ROI calculator | 1 | Conversion gate at moment-of-decision |

Then re-engage 118K dormant pool with: *"Your old account still works. Here's what's new."*

## Data access pattern

For ongoing monitoring, query `obapp_outbounders` DB on 209.74.93.72 as root. Key tables:
- `main_transaction` — deposit/spend ledger (THE source of truth, not main_invoice which is dead since 2014)
- `agent_payment` — payouts to agents · ~140 records/mo
- `membership` + `membership_payroll_fee` — subscription state + per-agent platform fee
- `main_users` — full user table · 118K rows

Live query script: `tools/outbounders_revenue_pull.sh` (wired 2026-05-23).

---

**Audit performed by AI (Ember) 2026-05-23. SSH + DB access via root@209.74.93.72. CORRECTED 2026-05-23 after James caught $2.24M float as error.**
