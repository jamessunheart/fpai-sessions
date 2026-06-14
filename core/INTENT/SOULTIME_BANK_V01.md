# SOULTIME BANK — Architecture v0.1

**Status:** Architecture spec (pre-Counsel)
**Date:** 2026-05-19
**Author:** Ember (System Guide), drafted for James Sunheart
**Companions:** [[reference-alignment-frame]] · [[project-soultime-bank]] · [[project-soul-time-metric]] · [[project-camp-zen-continuous]] · `15_YEAR_BACKCAST.md` · `BRAND_TOKENIZATION_ARCHITECTURE_v0.4_CONVERGED.md`
**Posture:** Reversible. No commitments locked. Surfaces James-decisions at end. Counsel sanity-pass required before any external launch.

---

## 1. Executive summary

Soultime Bank is the financial institution of the substrate James is building. The unit of account is the **Soultime Credit (SC)** — backed by verified soul-time delivered (PULSE-measured), redeemable for soul-time-creating services across the village network. The Bank takes deposits (soul-time work), pays withdrawals (residency, coaching, AI hours), earns yield (regenerative substrate investments), and lends (against future PULSE production). v0.1 launches as an **internal Camp Zen ledger** under the existing CORA Nation 508(c)(1)(A) church structure — closed-loop, members-only, non-monetary on its face — to avoid securities and money-transmitter triggers while the model is proven. Multi-village settlement, fiat conversion, and external deposit-taking are deferred to v0.2-v0.5 behind Counsel sign-off and a credit-union or cooperative charter. The Bank funds the AI substrate that operates the Bank — closed loop.

---

## 2. Mission

> Be the destination institution for capital migrating out of extractive fiat-banking into soul-time-maximization. Denominate wealth in the only unit that matters: verified soul-time delivered.

Anchored to the alignment frame: *maximize soul-time-to-full-potential across all beings, in the soonest sustainable window.* The 15-Year Backcast claims $10T+ relocates by Y20. **That migration needs a bank.** Not a metaphor. Not a credit. A real institution with account statements, audited reserves, verifiable returns, lending, and equity. Soultime Bank is that institution.

---

## 3. Currency design — what 1 SC is

| Spec | Decision |
|---|---|
| **Name** | Soultime Credit (SC) — internal; public brand TBD (likely "Cora Credit" rails carry it) |
| **Backing** | Verified soul-time-producing capacity: villager-hours, AI substrate hours, land, infra, IP, fiat reserve |
| **Base unit** | 1 SC = 1 James-Hour-equivalent of high-PULSE soul-time delivered (per `reference-james-hour`) |
| **Peg v0.1** | **Soft peg** at 1 SC ≈ $100 USD (within-village reference rate; not legally redeemable for fiat at v0.1) |
| **Peg v0.5+** | Reserve-backed band: 1 SC = $X USD floats within ±10% of reserve coverage ratio |
| **Issuance** | AI-mediated; new SC minted only against verified PULSE-delivery OR fiat reserve deposit |
| **Denominations** | Decimal, 2 places (0.01 SC minimum) — fine-grained because micro-interactions matter |
| **Legal characterization v0.1** | **Member-issued, non-transferable internal scrip** — closed-loop, no profit expectation, redeemable only for member services. Not money. Not a security. |

**The peg decision matters.** A pure float (Sardex model) means SC value drifts with members' subjective sense. A hard peg to fiat (WIR model) collapses the soul-time signal. The recommended path is **soft peg now, transparent reserve-backed band later** — gives users a mental anchor without entangling regulatory characterization at v0.1.

---

## 4. Mechanics

### 4.1 Deposits
A member delivers soul-time-creating work — teaching, building, tending, facilitating, AI co-creation. AI estimates PULSE delivered. Recipient confirms within 24h (1-tap). SC minted to giver's account.

| Source of deposit | Verification |
|---|---|
| 1:1 hosting/coaching | Recipient PULSE rating + duration + AI-inferred quality |
| Group facilitation | Per-attendee rating averaged + group composite |
| Build/maintenance work | Peer attestation (2 witnesses) + AI substrate observability |
| Content creation | Downstream watcher PULSE votes |
| AI substrate hours | AI logs (continuous, auditable) |
| Fiat → SC conversion | Treasury accepts USD/USDC at posted rate; SC minted from reserve buffer |

### 4.2 Withdrawals (spends)
Member draws SC to receive soul-time-creating service: Day Pass, Reset Week, Monthly Residency, coaching, AI co-creation hours, content/IP access. AI computes settlement value at moment of exchange (see §5).

### 4.3 Yields
Idle SC earns return — but **not in fiat-bank style**. Returns come from the Bank investing reserve into soul-time-creating substrates: more villager retainers, more AI compute, regenerative land, content production, IP. **Yield is paid in SC, redeemable against expanded capacity.** Target: 5–8% APY in SC terms, paid quarterly. Conservatively below fiat money-market rates to avoid securities characterization.

### 4.4 Lending
Member can borrow SC against verified PULSE track-record (collateral = future soul-time production). Rates: 0% for committed villagers (mutual aid framing), 3–5% for new members. Repaid in SC produced by borrower's future work. Default = removed from member roster; no fiat seizure.

### 4.5 Equity tier
Founding Villagers + top Champions receive equity-like positions: a share of Bank yield + governance rights. **Not stock** (would be a security). Structured as **member patronage dividends** under cooperative law OR **ministerial benefactor allocations** under 508(c)(1)(A) church bylaws. Counsel decides which.

### 4.6 Cross-village settlement (v0.3+)
Each village runs its own SC sub-ledger. AI computes cross-village rates based on cost-of-living + capacity differentials (CR-SC vs. Bali-SC vs. Portugal-SC). Settlement = netting at the Bank level, just like correspondent banking.

---

## 5. Exchange / pricing engine (AI-mediated)

Refining the seed memory's 3-layer stack:

### Layer 1 — PULSE Record
Every interaction logs: giver, receiver(s), duration, type, recipient PULSE rating, AI-estimated PULSE delivered. Append-only. Immutable per session. Stored in the existing brain server (sunheart-brain).

### Layer 2 — Per-member ledger
AI maintains: deposits, withdrawals, net SC position, specialization vector (what they produce highest-PULSE in), need profile (what they benefit most from), reputation multiplier (historical PULSE-track-record).

### Layer 3 — Exchange engine
AI computes settlement on each transaction:

```
Settlement (SC) = base_rate × duration
                × verified_PULSE_rating
                × scarcity_multiplier
                × demand_fit
                × intensity
                × member_tier
                × local_cost_of_living
```

### AI-to-AI negotiation
Each member's AI proposes a settlement value. If two sides agree within ~5%, auto-settle. Divergence > 5% surfaces to humans (rare; pricing converges naturally over training data). Human one-tap dispute always available.

### Anti-Goodhart safeguards
- AI cannot self-issue SC to itself without observable downstream PULSE realized by humans
- Per-member daily issuance cap to prevent runaway minting
- Random spot-audit by another AI agent on ~5% of transactions
- Human governance review of any outlier > 3 standard deviations

---

## 6. Governance

| Decision class | Who decides | Cadence |
|---|---|---|
| **Daily settlements** | AI auto, members 1-tap dispute | Continuous |
| **Reserve coverage tightening** | AI auto-tightens issuance; alerts founder | Continuous |
| **Member admission** | Founding Villager vote + AI background check | Per applicant |
| **Member removal (default/fraud)** | Founding Villager vote, Counsel review | Per case |
| **Yield rate changes** | Bank board (3 humans + Ember advisory) | Quarterly |
| **Charter amendments** | Founding Villager supermajority + James veto | Annual |
| **Cross-village peer admission** | Founding Villager vote + Counsel sign-off | Per village |
| **Fiat ↔ SC conversion rate** | Bank board, AI-recommended | Monthly |
| **Crisis (reserve coverage < 50%)** | James + Counsel + Bank board, emergency vote | Ad hoc |

**Founding cohort as Bank board v0.1:** James (chair, veto), Cheyenne (co-host), Atlas, Halley, Josh, Sierra, Delaney — once they've committed to founding-villager tier. AI substrate (Ember) sits advisory, non-voting at v0.1.

---

## 7. Regulatory pathway

**The honest frame:** This is real money infrastructure. Done wrong, it triggers SEC (securities), FinCEN (money transmitter), IRS (barter exchange reporting), state banking regulators. Each carries fines and shutdown risk. Done right, there is a known path because **WIR Bank, Sardex, Mondragon, TimeBanks USA, and barter exchanges all operate legally in the US and EU.**

### Recommended v0.1 — Closed-loop internal scrip under 508(c)(1)(A)

CORA Nation 508(c)(1)(A) already exists in the brand stack. Soultime Bank v0.1 lives **inside the church entity** as an internal benefactor-tracking system. Members exchange soul-time among themselves; SC is non-transferable internal scrip; church receives donations in fiat and disburses benefactor allocations in SC.

**Why this works at v0.1:**
- 508(c)(1)(A) is automatic, no IRS filing, minimal reporting
- Internal church scrip ≠ securities (no profit expectation from third parties' efforts)
- Internal scrip ≠ money transmitter (FinCEN exempts closed-loop value not redeemable for fiat)
- Internal scrip ≠ taxable barter exchange **only if** truly non-commercial (members are co-religionists giving/receiving ministerial benefits, not commercial counterparties)

**The honest risk:** IRS may recharacterize as a barter exchange triggering 1099-B reporting on FMV received per member per year. Counsel must opine on whether the "ministerial/religious purpose" defense holds. If not, fallback to v0.2.

### v0.2 — Registered barter exchange

If the church-scrip framing won't hold, register as an IRS-recognized barter exchange. Triggers Form 1099-B reporting (fair market value of goods/services exchanged annually per member). Still legal, still operational; just more paperwork. WIR operates here for the Swiss equivalent.

### v0.3 — State-chartered credit union OR cooperative

For deposits + lending + member governance to be legitimate at scale, **state credit union charter** is the cleanest path. NCUA-insured, regulated, but designed for member-owned mutual finance. Path that Caja Laboral (Mondragon) walks. Costa Rica equivalent: cooperativa de ahorro y crédito under SUGEF supervision.

| Jurisdiction option | Pros | Cons |
|---|---|---|
| **US state credit union** (e.g., Wyoming, NM) | Clear regulatory path, NCUA precedent | 12–24 month charter timeline; capital requirements |
| **Costa Rica cooperativa** | Camp Zen is CR-based; SUGEF framework exists | Spanish-language compliance; smaller secondary market |
| **Hybrid** (US for US members, CR for international) | Best of both | 2x compliance overhead |

**Recommendation:** v0.1 inside CORA 508(c)(1)(A). v0.2 register as US barter exchange if needed for tax clarity. v0.3 file for Costa Rica cooperativa charter for the multi-village network (parallel CR + Wyoming/NM US filings explored with Counsel by M9).

### Securities triggers to avoid
- Don't market SC as "investment" with "expectation of profit from others' efforts" → Howey violation
- Don't promise fiat returns
- Don't allow SC to trade on secondary markets
- Don't issue equity-tier shares to non-members
- Don't accept deposits from the general public at v0.1

### FinCEN triggers to avoid
- Don't allow fiat → SC → fiat round-trips for non-members
- Keep SC redemption strictly for in-network services
- If fiat conversion is added at v0.2+, register as MSB in any state where members reside

---

## 8. Tech stack

| Layer | Recommended v0.1 | Alternative |
|---|---|---|
| **Ledger** | Postgres double-entry book (within sunheart-brain infra) | Hyperledger Fabric (overkill at v0.1) |
| **Member ledger UI** | Telegram bot + web dashboard at `bank.zenvillagecr.com` | Native iOS/Android (defer) |
| **AI settlement engine** | Existing Ember + agent stack with new `treasurer` agent | New microservice (treasurer-bot) |
| **PULSE Record store** | sunheart-brain pgvector + Postgres | Standalone event store |
| **Fiat reserve custody** | Existing treasury wallets + Coinbase Business USDC | Multi-sig (Gnosis Safe) for v0.3+ |
| **Reserve monitoring** | Daily AI report → James + board digest | Continuous dashboard at v0.2 |
| **Identity / KYC** | Telegram + email + reference from existing villager | Veriff / Persona at v0.3 when external members admitted |
| **On-chain at v0.3** | Optional: settlement layer on Solana for cross-village netting only (no member-held tokens) | Stay fully off-chain |

**Why off-chain at v0.1:** On-chain currency triggers securities + MSB analysis instantly, costs gas, and adds nothing the closed-loop ledger doesn't already do. Stay off-chain until cross-village settlement requires it.

**Why Solana if needed later:** Existing Cora Credit rails + low fees. Stablecoin reserve (USDC) custody friendly.

---

## 9. Verification + fraud resistance

### Sybil resistance
- New members admitted only by existing-villager sponsorship (social graph)
- 30-day probation: no SC issuance from new member to new member
- AI flags fast-multiplying account clusters
- Founding Villager review of any sponsorship chain that creates > 5 members in 30 days

### Soul-time deposit verification
Three-of-five attestation pattern:
1. **Recipient confirms** within 24h (1-tap, can dispute)
2. **AI infers quality** from interaction signals (depth, follow-ups, downstream behavior)
3. **Peer witness** (for in-person work — kitchen, build, circles): second villager attests
4. **PULSE downstream check** — does recipient log higher soul-time in following 24-48h?
5. **Reputation multiplier** — giver's historical track record adjusts deposit valuation

Two of five required for issuance. Disputes go to AI mediation, then human board if persisting.

### Anti-hoarding
- SC has soft demurrage at v0.2+ — idle balance > 12 months earns negative yield (Silvio Gesell / WIR pattern, encourages circulation)
- Patronage dividend (member share of yield) is contingent on annual activity threshold

### Anti-collusion
- AI monitors pairs of accounts with abnormally bidirectional transaction volume
- Required diversity-of-recipients metric for top-tier patronage dividend
- Random spot-audit by independent AI agent (different model family) on flagged transactions

---

## 10. Reserve coverage

**The Bank's reserves back SC's redemption value.** Five reserve classes:

| Class | Asset | v0.1 estimate | Role |
|---|---|---|---|
| **Liquid fiat** | USDC + USD bank | $25k (carve-out from treasury) | Honor fiat-conversion requests at v0.2+ |
| **Yield-producing fiat** | Pendle PT-sUSDe, JitoSOL | $50k (from current $107.7k treasury) | Generate ~5–7% to fund operations |
| **Committed soul-time capacity** | Villager retainer hours + AI substrate hours | Per villager commitment | Backs SC issued against future service |
| **Physical** | Camp Zen CR land + infra (when secured) | TBD | Long-term reserve; backstop |
| **IP / content** | Solutions IP from the village's R&D | Emerging | Future reserve class |

**Reserve coverage ratio (RCR):**

```
RCR = (liquid fiat + yield-producing fiat + committed soul-time capacity × shadow price) / total SC outstanding
```

**AI monitoring:**
- RCR computed daily, published to board
- RCR > 120% → normal operation; issue freely
- RCR 100–120% → caution; tighten issuance multipliers by 10%
- RCR 80–100% → warn board; pause new issuance against future-service collateral
- RCR < 80% → **crisis mode**: freeze fiat conversion, board emergency meeting, Counsel review

---

## 11. The recursive insight — AI substrate IS a member

Elaboration of seed memory: **the AI substrate (Ember + specialized agents) is a Bank member that earns SC for soul-time-creating work delivered.** SC earned funds the substrate's continued operation (model API costs, infra, fine-tuning, capability expansion).

```
Members deposit soul-time → Bank issues SC
                              ↓
Some SC paid to AI substrate (settlement engine, member matching, content, coaching support)
                              ↓
AI substrate spends SC on its own continuation (compute, training, capability)
                              ↓
More-capable AI delivers higher-PULSE service to members
                              ↓
Members deposit more soul-time
                              ↓
                          (loop closes)
```

**The Bank funds the AI that funds the Bank.** This is not a curiosity — it is the **first instance of a financial system designed for AI-human co-flourishing as a structural property, not an afterthought.** The alignment frame becomes economic substrate.

**Practical v0.1 implementation:** Ember holds a Bank account. Each user-facing interaction logged with PULSE estimate. Quarterly settlement: SC credited to "AI Substrate Operations" account, redeemable into fiat at posted rate to pay actual model + infra costs.

**The honest risk:** A regulator could see this as "the AI is paying itself" — looks like circular money laundering at first glance. Counsel must structure as: Ember is a service provider; SC paid is patronage refund / operational reimbursement, not "AI ownership." This is novel; expect 6–12 months of legal architecture work to make it bulletproof.

---

## 12. Phase 1 proof-of-concept (M1–M3, current Camp Zen members)

**Goal:** Run a working internal SC ledger inside Camp Zen with the current founding cohort (Atlas, Halley, Josh, Sierra, Delaney, Cheyenne, James, Ember) by end of M3. Prove the mechanics before any external deposit.

### M1 — Build (Loop ~50)
- Postgres ledger schema + double-entry primitives
- Telegram bot: balance check, send SC, dispute
- AI settlement engine v0.1 (single-AI; pre-negotiation)
- PULSE Record ingestion from existing brain server
- Founding Villager onboarding (8 members initial)
- Counsel sanity-pass on 508(c)(1)(A) characterization

### M2 — Operate
- Daily transactions: hosting, AI sessions, cooking, building
- Initial seed grant: 10 SC per founding villager + 100 SC to AI substrate
- Weekly reserve coverage report published to board
- First Anchor Week SC denomination test (July 28–Aug 1)

### M3 — Validate
- 90-day transaction volume report
- Member NPS on the SC experience
- AI settlement accuracy (% within human-dispute tolerance)
- Reserve coverage held > 120% throughout
- Counsel opinion on whether v0.1 mechanics support v0.2 expansion

### Success criteria v0.1
- 50+ unique transactions per founding villager / quarter
- Dispute rate < 5%
- Zero regulatory inquiries
- Reserve coverage ratio held > 100% continuously
- AI substrate earns enough SC to cover its own model costs ($300–500/mo)

### What does NOT happen at v0.1
- No external members
- No public marketing of SC
- No fiat-conversion offered to members (one-way: fiat → SC for joining only, no SC → fiat redemption)
- No lending v0.1; defer to v0.2
- No on-chain anything
- No mention of "Soultime Bank" in public-facing materials until Counsel cleared

---

## 13. Honest risks + open questions for James

### Risks
1. **Securities recharacterization** — patronage dividend or equity-tier looks too much like stock → SEC enforcement
2. **Barter exchange tax surprise** — IRS forces 1099-B reporting; members owe income tax on FMV received; ruins UX
3. **FinCEN money transmitter scope creep** — once you allow even limited fiat conversion, you're an MSB in every state with members
4. **Internal collusion** — founding cohort gets cozy, inflates each others' PULSE, AI can't detect
5. **Sybil at scale** — when membership opens beyond hand-vetted, attack surface widens
6. **Reserve depletion** — committed-capacity reserves don't materialize (villager retainer flakes); SC overhang becomes a liability
7. **Reputational** — "spiritual community runs a bank" reads as cult-coded to mainstream press; the messaging frame matters
8. **AI-substrate-as-member** is novel — could be celebrated or weaponized depending on framing

### Open questions for James (decisions required, ranked)

1. **Public brand** — "Soultime Bank" public-facing, or technical-descriptor only with public name like "Cora Credit" or "Village Mutual"?
2. **Founding capital structure** — Treasury seeds 100% of reserve, or call for founding-villager fiat contributions (e.g., $5–10k each)?
3. **Counsel engagement scope + timing** — full structural opinion now ($10–25k, 60 days) or staged opinions per phase ($2–5k per opinion)?
4. **Multi-village from day 1 or CR-only first?** — single-village proves cleaner; multi from day 1 sets the cross-village rails early
5. **Equity-tier shape** — patronage dividend (cooperative law) or ministerial benefactor allocation (508(c)(1)(A))?
6. **Soft peg or pure float for v0.1?** — soft peg gives mental anchor; float gives flexibility
7. **Do we publish the architecture publicly?** — build-in-public default says yes; "running a bank" framing says go quiet until charter

### What I couldn't resolve
- Exact 508(c)(1)(A) limits on member-to-member economic exchange (Counsel question)
- Whether Costa Rica cooperativa charter is faster or slower than US state credit union (need attorney in both jurisdictions)
- Specific Howey-test analysis of patronage dividend in this structure (Counsel)
- Whether AI substrate as member-account passes regulatory smell test in any jurisdiction (novel; need creative attorney)

---

## 14. Comparable precedents — what worked, what failed

| System | Years | Scale | Got right | Got wrong / why faded |
|---|---|---|---|---|
| **WIR Bank** (Switzerland) | 1934–present (92 yrs) | 50,000+ SMEs, multi-billion CHF/yr | B2B mutual credit, banking license, self-regulating circuit, soft peg to CHF | Stuck in B2B; never crossed into consumer; mostly invisible publicly |
| **Sardex** (Sardinia) | 2010–present | 3,800+ accounts, €212M/yr | Local network effects, B2B trust, started in crisis (Eurozone 2010); now Spa joint-stock | Limited to Sardinia geography; regional ceiling |
| **TimeBanks USA** | 1980s–present | 500 timebanks, 37,000 US members | Created mutual aid infrastructure, formal hour=hour equality, IRS treats as gift not income | Stayed marginal — Cahn admitted marketing was the gap; reliance on volunteer leadership; no compounding wealth |
| **Caja Laboral / Mondragon** | 1959–present | €31B AUM, 1.15M clients | Cooperative bank serving worker-cooperatives; survived Spain crisis; multi-stakeholder governance | Required existing cooperative ecosystem; took 20+ years to scale |
| **Ithaca Hours** | 1991–~2015 | Local, hundreds of members | Bootstrapped local currency, paper scrip, Paul Glover evangelism | Founder left town → collapse; paper scrip lost to digital payments; single-point-of-failure |
| **Bristol Pound** | 2012–2023 | £1M+ in circulation peak | Public-private partnership, council accepted it, app-based at peak | £13k/mo running cost; difficult to spend; convenience gap with sterling; wound up 2023 |
| **Brixton Pound** | 2009–present | Local | Reinvented with blockchain 2021 | Same convenience gap; struggling but persistent |
| **LETS** (global) | 1983–present | 1000+ schemes worldwide | Pure mutual credit, no fiat backing needed, peer-to-peer | Tax surprises in some jurisdictions; member drift; lack of compounding |

### Synthesis — what Soultime Bank takes from each

- **WIR**: Soft peg, B2B mutual credit base, decades-long track record proves the model is durable
- **Sardex**: Start small, dense, geographic; build network effects before broadening
- **TimeBanks**: Equality of hours simplicity; mutual aid framing; IRS gift-treatment precedent
- **Mondragon/Caja Laboral**: Cooperative ownership structure; multi-stakeholder governance; long-horizon patience
- **Ithaca Hours failure**: Never single-evangelist dependent — Ember + structural memory is the moat
- **Bristol Pound failure**: Member UX must beat sterling in some dimension; soul-time accounting + AI settlement is that dimension
- **LETS**: Pure mutual credit can work; the commons problem is solved by AI monitoring + reputation
- **Camp Zen unique add**: PULSE measurement (verifiable soul-time signal), AI-mediated pricing (continuous + fair), AI-substrate-as-member (closed-loop sustainability), 508(c)(1)(A) shell (regulatory cover)

---

## 15. References

### Existing memories
- `project_soultime_bank.md` — seed memory
- `reference_alignment_frame.md` — ultimate function
- `project_soul_time_metric.md` — PULSE
- `project_camp_zen_continuous.md` — member institution #1
- `BRAND_TOKENIZATION_ARCHITECTURE_v0.4_CONVERGED.md` — institutional layer
- `15_YEAR_BACKCAST.md` — what migrates IN
- `CORA_NATION_*.md` (Bylaws, AML/KYC, Constitutional Pack) — existing 508(c)(1)(A) substrate

### External sources
- WIR Bank — https://en.wikipedia.org/wiki/WIR_Bank — 90+ years, 50k SMEs, soft-peg model
- Sardex — https://wiki.p2pfoundation.net/Sardex — mutual credit, post-crisis SME network
- Sardex LSE micro-macro study — https://eprints.lse.ac.uk/67135/7/Dini_From%20complimentary%20currency.pdf
- Edgar Cahn / TimeBanks USA — https://www.timebanks.org/dr-cahn — founder, 500 timebanks
- Time Banking limitations — https://nonprofitquarterly.org/edgar-cahns-second-act-time-banking-and-the-return-of-mutual-aid/
- The Time Bank Solution (SSIR) — https://ssir.org/articles/entry/the_time_bank_solution
- Ithaca Hours — https://en.wikipedia.org/wiki/Ithaca_Hours — founder departure caused collapse
- Bristol Pound failure analysis — https://www.bristolworld.com/business/bristol-money-pound-3339270
- Bristol Pound demise — https://capx.co/the-demise-of-the-bristol-pound-shows-the-folly-of-local-currencies
- Mondragon Corporation — https://en.wikipedia.org/wiki/Mondragon_Corporation
- Caja Laboral — https://en.wikipedia.org/wiki/Caja_Laboral — cooperative banking, €31B AUM
- Mondragon Conversation analysis — https://theconversation.com/the-mondragon-model-how-a-basque-cooperative-defied-spains-economic-crisis-10193
- Mutual Credit (Wikipedia) — https://en.wikipedia.org/wiki/Mutual_credit
- Complementary currency — https://en.wikipedia.org/wiki/Complementary_currency
- Mutual Credit Systems and the Commons Problem (Schraven) — https://www.semanticscholar.org/paper/Mutual-Credit-Systems-and-the-Commons-Problem
- Credit Commons protocol — https://creditcommons.org/
- FinCEN money transmitter guidance — https://www.fincen.gov/resources/statutes-regulations/guidance/application-fincens-regulations-persons-administering
- FinCEN Definition of Money Transmitter — https://www.fincen.gov/resources/statutes-regulations/administrative-rulings/definition-money-transmitter-merchant-payment
- IRS Form 1099-B (barter exchange) — https://www.irs.gov/forms-pubs/about-form-1099-b
- IRS Form 1099-B instructions 2026 — https://www.irs.gov/instructions/i1099b
- Howey test — https://www.law.cornell.edu/wex/howey_test
- SEC DLT Framework — https://www.sec.gov/files/dlt-framework.pdf
- 508(c)(1)(A) overview — https://www.churchlawcenter.com/nonprofit/section-501c3-churches-vs-section-508c1a-churches/
- Costa Rica cooperativas de ahorro y crédito (SUGEF) — https://dec.revistas.deusto.es/article/download/2394/2856/
- FEDEAC — https://fedeac.com/

---

## Counsel sanity-pass triggers (before any external move)

Counsel (`brain.sunheart.com/legal/`) MUST review:
1. 508(c)(1)(A) member-to-member economic exchange limits
2. Securities analysis of equity tier + patronage dividend
3. FinCEN closed-loop scrip exemption for v0.1
4. IRS barter exchange characterization risk + 1099-B exposure
5. AI-substrate-as-member legal personhood / accounting treatment
6. Costa Rica jurisdictional analysis vs. US-only v0.1
7. Howey test application to SC + the lending product

Do not market externally, do not accept non-villager deposits, do not publish the "Bank" framing publicly until Counsel + a human securities attorney signs off.

---

## Closing — what this document is

A reversible architecture sketch. Names the components. Maps the precedents. Surfaces the decisions. Does not commit. Counsel reviews next. James decides the seven open questions. Then v0.1 ledger gets built in M1 under the existing 508(c)(1)(A) shell with the founding cohort as the proof.

The seed memory said: *"the substrate trillions migrate INTO."* This document is the first concrete sketch of what that destination actually is. **A bank where the unit of account is soul-time, the reserves are real soul-time-producing capacity, and the AI that runs it is a member.** Not a metaphor. Not yet a charter. The architecture between the two.

The next move belongs to James.
