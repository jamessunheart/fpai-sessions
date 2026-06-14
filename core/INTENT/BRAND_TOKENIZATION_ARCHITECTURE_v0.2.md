# Brand Tokenization Architecture v0.2 (post-Counsel-v0.1 revision)

**Status:** DRAFT — incorporates v0.1 Counsel critique fixes. Three CRITICAL issues addressed.
**Drafted:** 2026-05-11
**Prior pass:** v0.1 critique by The Counsel — 3 CRITICAL, 3 HIGH, 3 MEDIUM issues identified
**Resolves from v0.1:**
- Issue 1 (Howey investment-contract) → utility-only tokens, no revenue distribution, no NAV redemption
- Issue 2 (Private inurement) → community-provision compensation; commercial activity moves to arm's-length for-profit LLC subsidiaries
- Issue 3 (Mockumentary demand-gen) → mockumentary recharacterized as religious-community documentary work; severed from token sales mechanics
- Issue 4 (ICA exposure) → cross-redemption mechanic removed; resolves automatically
- Issue 5 (FinCEN/MTL stored-value) → Coherent Credit is closed-loop service access, not stored value
- Issue 6 (Reves note test) → resolved by Issue 1 fix (no debt-like features)
- Issue 7 (PMA doctrine misframed) → member-gating reframed as substantive religious-community requirements, not securities exemption
- Issue 8 (UBIT exposure) → each commercial Brand operates via for-profit LLC subsidiary; 508(c)(1)(A) receives charitable contributions
- Issue 9 (Steward trust undefined) → resolved by Issue 2 fix (Stewards don't hold equity-style instruments from church-side activity)

---

## Revised architecture

```
┌────────────────────────────────────────────────────────────┐
│  RELIGIOUS / NONPROFIT TIER                                │
│  CORA Nation 508(c)(1)(A) church                           │
│  + Sunheart Private Trust                                  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Communal Treasury (Trust+Church consolidated funds) │  │
│  │  - Cash + crypto + bullion + property                │  │
│  │  - Receives charitable contributions from Brand LLCs │  │
│  │  - DOES NOT issue investment instruments             │  │
│  │  - DOES NOT hold equity stakes in Brand LLCs         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Coherent Credit (mutual-credit ledger)              │  │
│  │  - Issued for substantive religious-community        │  │
│  │    participation (WPA sign +50 to inviter, Proof     │  │
│  │    file +5/+20, DW witness +30, Mirror pair +100)    │  │
│  │  - Redeemable for religious-community services       │  │
│  │    (mirror witnessing, coaching, retreat access)     │  │
│  │  - NO pro-rata revenue distribution                  │  │
│  │  - NO NAV-based redemption                           │  │
│  │  - NO market value claim                             │  │
│  │  - Closed-loop: issued by + redeemable at CORA only  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  COMMERCIAL TIER (arm's-length, separate)                  │
│                                                            │
│  Each Brand = its own for-profit LLC                       │
│  - Sapphire LLC (Cheyenne) — psychic readings              │
│  - Camp Zen LLC — CR retreat operations                    │
│  - Halley's Brand LLC — TBD service offering               │
│  - (etc., one LLC per Brand)                               │
│                                                            │
│  Each Brand LLC:                                           │
│  - Owned by Steward + outside investors as appropriate     │
│  - Issues no tokens to public                              │
│  - Operates standard commercial activity                   │
│  - At arm's length from CORA Nation                        │
│  - Voluntarily contributes a % of profit to CORA Nation    │
│    as charitable contribution (deductible, documented)     │
│  - Standard tax + securities treatment for any equity      │
│    raised at the LLC level (Reg D, accredited investors,   │
│    proper disclosures)                                     │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  STEWARD COMPENSATION (community-provision + arm's-length) │
│                                                            │
│  From CORA Nation (religious-community side):              │
│  - Housing (Costa Rica village residency)                  │
│  - Meals from communal kitchen                             │
│  - Ceremonial participation                                │
│  - Pastoral support / community provision                  │
│  - DOCUMENTED with intermediate-sanctions-style            │
│    reasonableness analysis                                 │
│                                                            │
│  From Brand LLC (commercial side):                         │
│  - Salary / W-2 or 1099 compensation                       │
│  - Equity in their own Brand LLC                           │
│  - Standard commercial tax treatment                       │
│  - Compensation set by independent board / advisors        │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  MEMBER PARTICIPATION (substantive religious-community)    │
│                                                            │
│  - Sign World Peace Agreement (covenant entry)             │
│  - Complete Character Card (religious community vetting)   │
│  - Pair Mirror (Distance-Weighted Witness per Constitution)│
│                                                            │
│  These are GENUINE religious-community participation       │
│  requirements. They are NOT being used as a workaround     │
│  for securities qualification. The religious activities    │
│  must be substantive — actual practice, ceremony, witness, │
│  documented religious worship.                             │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  THE VILLAGE (mockumentary)                                │
│                                                            │
│  Recharacterized as CORA Nation Media Ministry             │
│  - Documents religious community life                      │
│  - Educational + inspirational content                     │
│  - Does NOT promote economic instruments                   │
│  - Does NOT solicit investment in Brand LLCs               │
│  - Does NOT promote token sales                            │
│  - Brand LLCs handle their own commercial marketing        │
│    through standard channels, separate from CORA media     │
└────────────────────────────────────────────────────────────┘
```

## Token mechanics (v0.2 revised)

**Coherent Credit (one credit type, issued by CORA Nation):**
- Earned through substantive religious-community participation (covenant + proofs + witnessing)
- Demurrage-based (per Coherent Treasury v0.10 architecture; not appreciation-seeking)
- Redeemable only for religious-community services (mirror witnessing, coaching, retreat access at member rates)
- Closed-loop: CORA Nation is the sole issuer AND the sole redeemer
- No transfer to outsiders. Member-to-member transfer allowed within community.
- Holds value via service utility, not market appreciation

**Brand-specific access tokens (optional, deferred for v0.3 if needed):**
- If individual Brands want substrate-level access tokens, they live entirely inside the for-profit LLC tier
- Treated as ordinary commercial loyalty / access tokens (e.g., closed-loop gift cards)
- Subject to standard FinCEN closed-loop exemption analysis
- Not connected to CORA Nation Coherent Credit
- DEFERRED — not in v0.2 scope; v0.2 ships without Brand tokens at all

## What the Communal Treasury holds (v0.2 revised)

- Cash + crypto + bullion (operating treasury, religious community provision)
- Property (Costa Rica land, Village physical operations)
- Donated assets from Stewards / members per CORA Nation declaration
- **NOT** equity in Brand LLCs (resolves private inurement)
- **NOT** investment-vehicle-style holdings designed for redemption (resolves ICA)

## Brand LLC ↔ CORA Nation relationship (arm's-length)

- Brand LLCs operate independently as commercial entities
- Stewards typically founders/owners of their respective Brand LLCs
- Brand LLCs may voluntarily contribute a percentage of net profit to CORA Nation as charitable contributions (US deductible, documented)
- CORA Nation does NOT own or control Brand LLC operations
- CORA Nation does NOT receive pro-rata revenue share from Brand LLCs (no inurement vector)
- Members can be customers of Brand LLCs (Sapphire readings, Camp Zen retreats) using either cash OR Coherent Credit at the Brand's discretion
- If a Brand accepts Coherent Credit, it settles via CORA Nation crediting the Brand LLC at agreed rates (effectively bartering for religious-community labor / outputs)

## Camp Zen operationalization

- **Camp Zen LLC** (for-profit) — owns retreat operations, charges retreat fees
- Owned by Steward (Atlás) + investors as appropriate
- Operates the physical retreat business
- Voluntarily contributes profit % to CORA Nation
- CORA Nation receives charitable funding, runs religious-community programs separately
- Members can attend Camp Zen retreats; member rates may differ from non-member rates (a service discount, not an investment return)

## Mockumentary recharacterization

- CORA Nation Media Ministry produces "The Village"
- Documents religious-community life, ceremony, character, ordinary daily living
- Does NOT promote Brand LLC commercial offerings (Brand LLCs market through standard commercial channels)
- Does NOT solicit investment, donation, or token purchase
- May invite viewers to engage with CORA Nation religious community (WPA, Character Card, ceremony attendance)
- Distinguished media-ministry framing — similar to Bruderhof public-facing media

---

## Open questions (for v0.3 council passes)

1. **Coherent Credit demurrage rate** — what specific rate is set? Per the corpus, demurrage prevents hoarding and forces circulation. v0.3 should specify.
2. **Steward "community-provision" valuation** — even with community-provision compensation, IRS may impute fair-market value of housing/meals/services. Need intermediate-sanctions-style reasonableness analysis per Brand LLC and per Steward.
3. **Brand LLC contribution percentages** — what range is reasonable? Too high → inurement risk through quid pro quo argument. Too low → no funding for religious community.
4. **Costa Rica entity** — Camp Zen LLC needs CR S.A. or equivalent for physical operations. Where does charitable contribution flow legally?
5. **Coherent Credit + Brand-LLC settlement** — when CORA Nation credits Brand LLC for accepting member Coherent Credits, that's an interesting transaction. Tax treatment? Member-rate-vs-public-rate fairness analysis?
6. **Member-to-member Coherent Credit transfer** — does this trigger any AML/MTL analysis even closed-loop? Counsel pass should verify closed-loop exemption holds with member-transfer.

---

## What this v0.2 explicitly does NOT do (and why)

- **Does not tokenize Brands** — defers token-mechanic complexity until structure is solid. v0.3 may reintroduce if useful and Counsel-cleared.
- **Does not promise revenue distribution** — central Howey-violation eliminated.
- **Does not redeem at NAV** — ICA exposure eliminated.
- **Does not equity-split Brands inside CORA** — inurement eliminated.
- **Does not use mockumentary to drive demand for instruments** — public-offering signal eliminated.
- **Does not rely on PMA as securities exemption** — member-gating reframed as substantive.

The architecture is simpler than v0.1. Less novel. More defensible. v0.3+ may reintroduce specific mechanisms ONE AT A TIME with Counsel analysis on each.
