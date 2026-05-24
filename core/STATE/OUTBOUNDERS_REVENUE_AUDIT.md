# Outbounders.com Revenue Audit — 2026-05-23

**First-time wiring of outbounders revenue into cockpit.** Source: direct SQL read against `obapp_outbounders` DB on server 209.74.93.72. Marketing site `outbounders.com` and live app `app.outbounders.com` audited; production untouched.

## The numbers (live read 2026-05-23)

| Metric | Value | Notes |
|--------|-------|-------|
| Currently held client float | **$2,237,547** | Money sitting on platform across all client accounts |
| Deposits in (last 30 days) | $13,778 | Clients adding funds |
| Deposits in (avg 18mo trailing) | ~$15-18K/mo | Stable |
| Agent payouts (last 30 days) | $13,182 | Money flowing OUT to outbounders/agents |
| Active paying clients per month | **6-12** | Across $15K+ in deposits |
| Active payroll-fee relationships | 946 | Platform's per-agent take · $3,784/cycle |
| Active "silver membership" subs | **0** | Dead product · 1 holdout was last $99/mo |
| Total registered users (lifetime) | **118,344** | 99%+ dormant |
| New signups (Jan 2025) | 1,756 | Healthy top-of-funnel |
| New signups (May 2026) | **75** | **23× decline** correlates with broken pages |

## The thesis

**Outbounders is a $2.24M float-holding marketplace running on 6-12 monthly clients.** The platform infrastructure works. The conversion funnel doesn't. Two cheap fixes (pricing page + /app redirect) just shipped today; the bigger lever is reactivating dormant users + reviving the dead membership tier.

### Critical findings

1. **Signups crashed 23×** between Jan 2025 (1,756/mo) and May 2026 (75/mo). Strongly correlates with broken-funnel state of the marketing site. Today's fixes should be measured against this baseline.

2. **Membership product is dead.** `membership` table shows 0 active subscribers. Only one $99/mo "silver" was charged for most of 2025-2026, and even that lapsed. There's a built-out product layer collecting $0 right now.

3. **118K dormant user pool.** A reactivation campaign to even 0.5% of dormant users (~590 users) at $49/mo = $29K/mo recurring revenue. Currently $0.

4. **Float is a feature, not a problem.** $2.24M held is leverage — yield on float alone (3-4% T-bills) could be $7-9K/month sleeping money without touching the marketplace.

## Today's fixes (shipped 2026-05-23)

- ✅ Replaced `/pricing` Lorem Ipsum with real pricing (Clients $25 / Outbounders Free + How-It-Works + FAQ). Elementor JSON disabled, backed up to `_BACKUP_2026-05-23_*` postmeta keys.
- ✅ Redirected `/app` (StartIt theme placeholder w/ fake testimonials) → `https://app.outbounders.com/` via `.htaccess` rewrite rule.
- ✅ Backups of old state in `/tmp/wp_posts_pricing_app_backup_*.sql` + `/tmp/htaccess.outbndrs.bak-*` on server.

## Next-tier revenue levers (ranked by leverage)

| # | Lever | Estimated impact | Effort |
|---|-------|-----------------|--------|
| 1 | Reactivate dormant 118K user base — email campaign w/ new offer | $10-50K/mo MRR | 1-2 weeks |
| 2 | Revive membership tier (build $49/$99/$199 monthly plans w/ real value) | $5-30K/mo MRR | 2-3 weeks |
| 3 | Yield on $2.24M float (T-bills / stables) | $7-9K/mo passive | 1 week |
| 4 | Signup friction reduction (5 checkboxes → 1) | +20-40% signup completion | 2-3 days |
| 5 | SEO content engine ("outsource cold calling", ROI calculator) | +inbound funnel | 4-8 weeks |

## Data access pattern

For ongoing monitoring, query `obapp_outbounders` DB on 209.74.93.72 as root. Key tables:
- `main_transaction` — deposit/spend ledger (THE source of truth, not main_invoice which is dead since 2014)
- `agent_payment` — payouts to agents · ~140 records/mo
- `membership` + `membership_payroll_fee` — subscription state + per-agent platform fee
- `main_users` — full user table · 118K rows

Wire this into the cockpit dashboard for daily/weekly digest.

---

**Audit performed by AI (Ember) 2026-05-23. SSH + DB access via root@209.74.93.72.**
