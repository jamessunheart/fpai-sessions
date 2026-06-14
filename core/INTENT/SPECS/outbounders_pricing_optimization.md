# Spec — Outbounders Pricing Optimization (2026)

**Status:** Draft — Growth Architect output. Not deployed.
**Date:** 2026-05-23
**Author:** Growth Architect (Ember-dispatched subagent)
**Target:** `outbounders.com` pricing structure + checkout flow
**Brand frame:** Option A — "Outbounders, now AI-augmented"
**Companion specs:** `outbounders_site_rebuild.md`, `outbounders_signup_friction_reduction.md`

---

## 1. Current Outbounders position (baseline)

| Dimension | Today |
|---|---|
| Model | Self-serve marketplace (clients hire agents hourly) |
| Entry friction | $25 minimum deposit |
| Platform take | $4/agent/payroll-cycle (membership_payroll_fee) — implies ~$3,784/cycle from 946 active pairings |
| Subscription | Membership product exists in schema but **dead** (0 active) |
| Hourly rate setting | Agent-set |
| Take-rate (effective) | <5% on most cycles — well below marketplace norms |
| Revenue last 30d | $13,778 deposits · 8 active payers · 105 new signups (down 23× from Jan-2025 peak) |

**Diagnosis:** Outbounders is a **marketplace** priced like a **payment processor**. Take-rate is so low that growth investment, AI features, and trust infrastructure aren't fundable from unit economics. Membership tier was never marketed. There's no managed-service premium tier to capture high-LTV clients like GNS ($1.33M / 10yr).

---

## 2. Competitor pricing matrix (2026, verified)

| Competitor | Model | Take / Price | Min Commit | What's Included | Target |
|---|---|---|---|---|---|
| **Upwork** | Marketplace + Tiered SaaS | Basic: 3–5% client + ~10% freelancer fee · Business Plus: 8–10% client | None (Basic); annual on Plus | Escrow, payment protection, dispute, contract docs | SMB → mid-market |
| **Fiverr / Pro** | Marketplace, fixed take | 20% seller + 5.5% buyer + $2.50 small-order fee (effective 24–35%) | None | Gig-based templates, Pro-vetted tier | SMB, creators |
| **Toptal** | Curated marketplace | $60–$150+/hr (50% markup undisclosed) · **$500 refundable deposit** · $79/mo subscription | Weekly min hours | Top 3% vetting, replacement guarantee | Mid-market, enterprise |
| **Apollo.io** | SaaS (data + dialer) | $49–$119/user/mo (annual) · Org min 3 users = $4,284/yr | Annual | Data, sequences, US dialer (Pro+), credits | Sales teams |
| **Outreach.io** | SaaS (sales engagement) | $100–$160+/user/mo · $1k–$8k implementation | Annual contracts only | Sequences, workflows, CRM, AI | Mid-market+ enterprise |
| **Callbox** | Managed agency | $4k–$5k/mo entry → 5-figures | Multi-month | Multi-channel managed campaigns | SMB → mid-market |
| **MarketStar** | Managed (enterprise) | $25k+/mo, custom · teams of 5–8 reps min | 6–12mo | Fully-burdened managed sales | Mid-market → enterprise |
| **Belkins** | Managed agency | $5k–$14k/mo · $2k–$5k startup tier | 3–12mo | Appointment setting + email + research | B2B SaaS, SMB |
| **Cleverly** | Managed (LinkedIn) | $397 / $697 / $997/mo | 3mo min | LinkedIn outbound, copy, leads (Sales Nav extra) | SMB |
| **SalesRoads** | Managed | $7k–$15k+/mo | Multi-month | Appointment setting, multi-channel | Mid-market B2B |
| **EBQ** | Managed (fractional team) | Custom (~$5k–$15k/mo bracket) | Multi-month | SDR + manager + marketing support | Mid-market |
| **Artisan (Ava)** | AI-SDR SaaS | $2k–$5k+/mo · Employee tier $600/mo annual | Annual | Autonomous AI SDR (note: market reverting to human-hybrid 2026) | Mid-market |
| **11x.ai** | AI-SDR SaaS | ~$60k/yr | Annual | Autonomous AI SDR | Mid-market |
| **Regie.ai** | AI sales SaaS | $180–$499/user/mo + enterprise | Annual | AI sequences, multiplier rep | SMB → mid |

### The landscape map

```
                        HIGH PRICE / HIGH TOUCH
                                  |
        MarketStar  •             |             • Enterprise SaaS
              SalesRoads •        |        • Outreach.io
                  EBQ •           |        • Apollo (top tier)
                  Belkins •       |        • 11x.ai / Artisan
                                  |
   MANAGED  ----  Callbox •       |       • Regie.ai  ----  SAAS
                                  |
                       Cleverly • |  • Apollo (mid)
                                  |
                      Toptal •    |    • Apollo (Basic)
                                  |
                       Upwork (Plus) •
                                  |
                   ★ OUTBOUNDERS (today: deposit + flat $4/cycle)
                          Fiverr •  |  • Upwork (Basic)
                                  |
                          LOW PRICE / SELF-SERVE
```

**Where Outbounders sits today:** ★ bottom-left — cheapest entry in the market, marketplace-mechanics, **zero AI-augmentation premium captured**, no managed-service upside. Underpriced.

---

## 3. Recommended pricing structure (Option A: "now AI-augmented")

### Three-tier model — Self-Serve / Pro / Managed

| Tier | Name | Price | Take-rate | Who | What's included |
|---|---|---|---|---|---|
| **T1** | **Marketplace** (free) | $25 deposit · **10% client fee + 5% agent fee** per hour billed | ~15% effective | Self-serve SMB, DIY | Agent search, hiring, hourly billing, escrow, AI Script Generator (free public), basic dispute, payment rails |
| **T2** | **Pro** (subscription) | **$149/mo** or $1,490/yr (saves 17%) | Reduced to 5% client + 5% agent | Power buyers (>$2k/mo spend); 3+ agents | Everything in T1 + **AI Script Studio Pro** (unlimited scripts, A/B variants, objection libraries) + Call Coach (recording analysis) + priority agent matching + verified-quality badge filter + monthly performance report + cheaper take |
| **T3** | **Managed (Done-For-You)** | **$2,500/mo retainer + 15% mgmt fee on agent hours** (≈ $4k–$8k/mo all-in for mid campaign) | 20% blended | Clients who want results, not tools | Dedicated campaign manager + AI-augmented script + curated agent team (3–5) + weekly reporting + recording QA + replacement guarantee + LinkedIn/email multi-channel add-on optional |

### Why this works on the 3-axis frame

| Axis | T1 Marketplace | T2 Pro | T3 Managed |
|---|---|---|---|
| **Velocity** | Highest — $25 entry preserved for funnel-top | Medium — converts proven users | Low — handhold sales but big tickets |
| **Durability** | Medium — churns without value-add | **High** — subscription + workflow lock-in | **Highest** — retainer + relationship + replacement-clause |
| **Survival** | Clean — fee-for-service, no recruiting bonus | Clean — pure SaaS | Clean — managed-services contract |

### What this captures

- **Top-of-funnel** ($25 deposit preserved): keeps the LuLaRoe-killer line clear (no inventory loads, no minimums).
- **Recurring revenue layer** (T2): revives the dead membership product as **AI-powered Pro** — not generic "membership" but a feature-anchored upgrade. Targeting ~10% of active clients at $149/mo = at scale, this dwarfs the $4/cycle take.
- **High-LTV ceiling** (T3): GNS at $1.33M / 10yr = $11k/mo avg. A T3 retainer captures this segment at proper margins.
- **AI-augmentation monetized**: Script Generator free at T1 (lead-gen + brand signal), **Pro features at T2** (Studio + Call Coach), **embedded in service at T3** (managed AI ops).

---

## 4. Specific question-by-question answers

### Q: Keep $25 deposit / hourly marketplace? Or tiers?
**KEEP $25 marketplace + ADD T2 and T3 above it.** Marketplace is the funnel; tiers are the monetization.

### Q: SaaS/subscription tier — what's included, what price?
**Revive as "Outbounders Pro" at $149/mo.** Anchor on AI Script Studio Pro + Call Coach + reduced take-rate. The reduced-take is the killer hook: a client spending $2k/mo on agent hours saves $200/mo in fees → Pro pays for itself net-of-zero at $1,500/mo agent spend. Comparable to Upwork Plus model.

### Q: Done-For-You Managed tier? Price?
**Yes. $2,500/mo retainer + 15% management fee on agent hours.** Positions Outbounders against Callbox / Belkins / SalesRoads at **~50–70% lower price** because the agent labor is sourced from the marketplace, not in-house. This is the structural advantage — competitors carry W-2 SDR burden; Outbounders doesn't.

### Q: AI Script Generator — free or gated?
**Free for the basic generator (lead-gen, public tool at outbounders.com/ai-script).** Captures emails, demonstrates AI-augmentation, builds SEO. **Pro version gated at T2** (multi-variant A/B, persona-based, objection libraries, unlimited generation, integration with active campaigns).

### Q: Platform take-rate sweet spot?
**T1 = 15% blended (10% client + 5% agent), T2 = 10% blended, T3 = 20% blended.** Below Upwork Basic (which is effectively ~13% blended), above Outbounders today (~3%). Frame the 15% as "we built the AI tools, the dispute system, the payment rails — and our managed agents close more deals" — not as a tax.

### Q: AI-augmentation in pricing communication?
- **T1**: "AI Script Generator included" badge — free utility hook
- **T2**: "AI-Powered Pro" — the product name carries it; positioned as "your AI sales ops team"
- **T3**: "AI + Human Managed" — frame the AI as the unfair advantage the dedicated team wields
- **No standalone "AI add-on" charge** — bundling > add-on for trust and simplicity

---

## 5. Growth DNA filter check

| Risk | Verdict |
|---|---|
| Pyramid / MLM structure | **CLEAN.** No recruiting bonus, no downline, no commissions tied to bringing other sellers. Pure marketplace + SaaS + managed services. |
| FTC red lines (2024 amendments) | **CLEAN.** No income claims. No "earn $X/mo as an outbounder" promises. Income Disclosure not required for this model. |
| Inventory loading | **N/A** — no products, just labor matchmaking. $25 deposit is escrow, not product purchase. |
| LuLaRoe-style starter pack | **CLEAN** — $25 entry, deposits remain user's, refundable on withdrawal. |
| Race-to-bottom on agent rates | **YELLOW.** Marketplace mechanics tend to compress agent rates. Mitigation: T3 Managed tier creates a premium-quality lane where agents earn 1.3–1.5× marketplace rate. Verified-quality badge in T2 also lifts top-quartile agents. |
| Take-rate optics | **YELLOW** — moving from ~3% to 15% effective will anger long-tail. Mitigation: grandfather existing 8 active clients at old rate for 6mo; new clients enter at new rates; provide AI Script Generator as immediate value-trade. |
| SEC / token / equity exposure | **CLEAN.** No tokens. No equity offers. No financial promises. |

🔴 No red lines triggered. 🟡 Two yellows worth designed mitigations.

---

## 6. Three A/B tests to run post-launch

### Test 1 — Pro tier price point
**Variant A:** Outbounders Pro @ $99/mo (volume play)
**Variant B:** Outbounders Pro @ $149/mo (margin play — recommended baseline)
**Variant C:** Outbounders Pro @ $199/mo (premium positioning)
**Metric:** Pro signups × ARPU × 90-day retention. Cohort by client size (avg monthly agent-hour spend).
**Hypothesis:** $149 will dominate; $99 cannibalizes; $199 fails for SMB but works for power users.

### Test 2 — Pricing page narrative frame
**Variant A:** "AI-Augmented Outbound Marketplace" (technology-forward)
**Variant B:** "Hire Outbounders — Now With AI Scripts Built-In" (utility-forward)
**Variant C:** "From Hire-an-Outbounder to Run-a-Campaign" (transformation-forward, anchors T3)
**Metric:** Pricing-page → signup conversion, % choosing each tier, dwell time.
**Hypothesis:** B wins for T1/T2 conversion; C wins for T3 lead capture.

### Test 3 — Take-rate communication
**Variant A:** Show take-rate explicitly in checkout ("Platform fee: 10% client, 5% agent")
**Variant B:** Bundle into displayed agent rate ("This agent costs $X/hr all-in" — fee included)
**Variant C:** Hide fee entirely, show only deposit + agent rate; fee appears on first invoice
**Metric:** Signup → first-deposit conversion. Track post-first-invoice churn vs each variant.
**Hypothesis:** B wins conversion but hurts trust over time; A wins LTV; C wins short-term but produces refund requests.

---

## 7. Sequencing — what ships when

1. **Week 1–2:** Build T2 (Pro) signup, Stripe subscription wiring, AI Script Studio Pro behind feature flag. Keep current T1 unchanged.
2. **Week 3:** Launch free AI Script Generator at `outbounders.com/ai-script` — public, email-gated, viral hook.
3. **Week 4:** Soft-launch T2 to existing 8 active payers + top-100 dormant clients (email campaign). Grandfather T1 take-rate.
4. **Week 5–6:** Build T3 (Managed) landing page + intake form. Sales call → manual onboarding for first 3 customers (validate price + scope).
5. **Week 7:** Roll out new public pricing page (Test 2 variants). Begin A/B tests 1 and 3.
6. **Week 8+:** Optimize based on data. Decide GA on T3.

---

## 8. Camp Zen / FP synergy notes

Outbounders revenue feeds the **Treasury Sales basket** (one of 3 baskets). Pro + Managed tiers convert Outbounders from a fee-skim into a real recurring-revenue stream — exactly what the Burn↔Green Ledger needs to hit crossover. T3 managed-services model is also a **template for the Concierge product** (`project_concierge.md` — same playbook: marketplace agents + AI ops + managed-services premium).

🟢 Show-frame: "We turned a $4/cycle skim into a tiered $149/$2,500 stack — same labor, 10× the take-rate per Pro client. AI was the wedge."

---

## Sources

- [Upwork Pricing — Clients](https://www.upwork.com/pricing/client)
- [Upwork Freelancer Service Fee](https://support.upwork.com/hc/en-us/articles/211062538-Learn-about-the-Freelancer-Service-Fee)
- [Fiverr Fees 2026 — FreelanceCompare](https://freelancecompare.com/blog/fiverr-fees-explained)
- [Toptal Pricing 2026 — HireInSouth](https://www.hireinsouth.com/post/how-much-does-toptal-cost)
- [Apollo.io Pricing 2026 — Landbase](https://www.landbase.com/blog/apollo-pricing)
- [Outreach.io Pricing 2026 — MarketBetter](https://www.marketbetter.ai/blog/outreach-pricing-breakdown-2026/)
- [Callbox Pricing 2026 — LeadHaste](https://leadhaste.com/blog/callbox-review-2026)
- [Belkins Pricing — Belkins.io](https://belkins.io/pricing)
- [Cleverly LinkedIn Pricing — ConnectSafely](https://connectsafely.ai/articles/cleverly-review-linkedin-lead-generation-alternative-2026)
- [SalesRoads Pricing Models](https://salesroads.com/outsourcing/appointment-setting-pricing-models/)
- [MarketStar Pricing](https://www.marketstar.com/pricing)
- [Artisan Pricing 2026 — 11x](https://www.11x.ai/guides/artisan-pricing)
- [Regie.ai Pricing 2026 — Landbase](https://www.landbase.com/blog/regie-ai-pricing)
- [Best AI Sales Agents 2026 — Amplemarket](https://www.amplemarket.com/blog/best-ai-sales-agents)
