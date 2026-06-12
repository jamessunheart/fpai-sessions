# Brand Tokenization Architecture v0.3 (post-Counsel-v0.2 revision)

**Status:** DRAFT — incorporates v0.2 Counsel critique fixes. Addresses 2 new CRITICAL + 3 HIGH + 3 MEDIUM issues from v0.2.
**Drafted:** 2026-05-11
**Prior pass:** v0.2 critique — 2 CRITICAL (Credit↔LLC settlement, intermediate-sanctions doc), 4 HIGH (arm's-length docs, member-transfer MTL, CR entity, etc.)
**Goal:** converge to a Counsel-clearable architecture (no CRITICAL/HIGH remaining) ready for human counsel 1-2hr sign-off

## Changes from v0.2

1. **REMOVED Credit ↔ Brand LLC settlement mechanic.** Coherent Credits redeemable ONLY at CORA Nation for CORA Nation-provided services. Brand LLCs cannot redeem Credits. (Resolves v0.2 Critical #1 — Howey + MTL re-opening)
2. **REMOVED member-to-member Credit transfer.** Credits earned by and redeemable by same member only. Closed-loop preserved. (Resolves v0.2 High — FinCEN closed-loop exemption holds)
3. **ADDED hard precondition for community-provision compensation.** §4958 intermediate-sanctions documentation required BEFORE any Steward receives provision. Specifies the documentation framework. (Resolves v0.2 Critical #2)
4. **ADDED arm's-length documentation requirements** — operating agreement, charitable contribution agreement, conflict-of-interest policy. Templates deferred to v0.4 if substantive issues remain. (Resolves v0.2 High — arm's-length asserted-not-documented)
5. **ELEVATED Costa Rica entity to blocking precondition** for Camp Zen operations. Specifies CR S.A. or S.R.L. with US-CR contribution flow defined by CR + US international tax counsel. (Resolves v0.2 High — CR absent)
6. **ADDED religious doctrine codification timeline** and membership-documentation protocol. (Resolves v0.2 Medium — substantive religious community operationalization)
7. **REPLACED "Brand LLC voluntary contribution %"** with: each Brand LLC's contribution is set independently by that LLC's board, documented as genuinely voluntary, with no contractual obligation tied to CORA Nation member access. (Resolves v0.2 Medium — contribution % bounds)

---

## Architecture (v0.3)

```
┌─────────────────────────────────────────────────────────────────┐
│  RELIGIOUS / NONPROFIT TIER                                     │
│                                                                 │
│  CORA Nation 508(c)(1)(A) church  +  Sunheart Private Trust     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Communal Treasury (Trust+Church consolidated)          │    │
│  │  - Cash + crypto + bullion + property                   │    │
│  │  - Receives ARM'S-LENGTH charitable contributions only  │    │
│  │  - DOES NOT issue investment instruments                │    │
│  │  - DOES NOT hold equity stakes in Brand LLCs            │    │
│  │  - DOES NOT settle Credit↔LLC transactions              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Coherent Credit (mutual-credit, CLOSED-LOOP)           │    │
│  │  Earned: substantive religious-community participation  │    │
│  │    (WPA, Proofs, DW witness, Mirror pair, ceremony)     │    │
│  │  Redeemable: ONLY at CORA Nation for CORA-PROVIDED      │    │
│  │    religious-community services:                        │    │
│  │      - Mirror witnessing sessions (CORA-led)            │    │
│  │      - Pastoral coaching (CORA chaplains)               │    │
│  │      - Retreat access at CORA-organized retreats        │    │
│  │      - Ceremony participation                           │    │
│  │  ❌ NOT redeemable at Brand LLCs                        │    │
│  │  ❌ NOT transferable member-to-member                   │    │
│  │  ❌ NOT redeemable for cash or cash-equivalent          │    │
│  │  ❌ NO NAV-based valuation                              │    │
│  │  ❌ NO secondary market                                 │    │
│  │  Demurrage: per Coherent Treasury v0.10 (TBD: rate)     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘

                       ⫶ ARM'S-LENGTH ⫶
                       ⫶ (documented) ⫶

┌─────────────────────────────────────────────────────────────────┐
│  COMMERCIAL TIER (separate, independent)                        │
│                                                                 │
│  Each Brand operates as its own for-profit LLC                  │
│  - Sapphire LLC (Cheyenne), Camp Zen LLC (Atlás), etc.          │
│                                                                 │
│  Each Brand LLC:                                                │
│  - Owned by Steward + outside investors as appropriate          │
│  - Standard commercial activity, standard tax/securities        │
│  - Sets pricing and terms independently                         │
│  - May offer optional member-rate discounts (commercial         │
│    decision, funded by the LLC itself, NOT settled              │
│    through CORA Nation)                                         │
│  - Verifies CORA membership via Coherent Credit balance         │
│    (membership-verification only, NOT payment)                  │
│  - Voluntarily may contribute net profit % to CORA Nation       │
│    as charitable contribution (rate set by LLC board,           │
│    documented as voluntary, no quid pro quo)                    │
│  - At arm's length per documented operating agreement +         │
│    contribution agreement + conflict-of-interest policy         │
│  - Any equity raises follow standard securities procedures      │
│    (Reg D, accredited investor, Form D, subscription, etc.      │
│    with licensed securities counsel review)                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  COSTA RICA OPERATIONS LAYER                                    │
│                                                                 │
│  Camp Zen operations in CR run through a Costa Rica entity      │
│  (S.A. or S.R.L. per CR counsel)                                │
│                                                                 │
│  - CR entity owns or operates the physical land + retreat       │
│  - CR labor law applied to on-site workers                      │
│  - CR tax treatment for income generated in CR                  │
│  - Charitable contribution flow from CR entity to CORA Nation   │
│    structured per CR + US international tax counsel             │
│  - Camp Zen LLC (US) may be the parent of the CR entity, or     │
│    may license the brand to a separately-owned CR entity —      │
│    decision pending CR counsel + US tax counsel pass            │
│                                                                 │
│  HARD PRECONDITION: No Camp Zen physical operations begin       │
│  until CR entity is established and CR counsel sign-off         │
│  is obtained.                                                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STEWARD COMPENSATION (two-layer, with §4958 documentation)     │
│                                                                 │
│  From CORA Nation (religious community-provision):              │
│  - Housing (CR village residency, valued at fair rental rate)   │
│  - Meals (valued at fair cost per person-day)                   │
│  - Pastoral support / community provision                       │
│  - Ceremonial role                                              │
│  HARD PRECONDITION: Before community-provision begins for       │
│  any Steward, CORA Nation completes IRC §4958 rebuttable-       │
│  presumption documentation:                                     │
│    1. Comparable-compensation data (BLS, religious-community    │
│       benchmarks, peer-organization data)                       │
│    2. Independent approval (CORA Nation board members who are   │
│       not Stewards-of-other-Brands and not personal friends     │
│       of the Steward in question)                               │
│    3. Contemporaneous written documentation of the              │
│       compensation determination and its basis                  │
│  Without these three: no provision activates.                   │
│                                                                 │
│  From Brand LLC (commercial side):                              │
│  - Salary (W-2) or contractor (1099) compensation               │
│  - Equity in their own Brand LLC                                │
│  - Set by Brand LLC's independent board (or by Steward's        │
│    own decision if sole owner) at fair-market commercial rate   │
│  - Documented separately from CORA Nation provision             │
│  - Standard worker-classification analysis (IRS 20-factor,      │
│    CR labor code) before treating as contractor vs employee     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MEMBER PARTICIPATION (substantive religious-community)         │
│                                                                 │
│  - World Peace Agreement (covenant entry)                       │
│  - Character Card (religious-community vetting)                 │
│  - Mirror Pairing (Distance-Weighted Witness, per Constitution) │
│                                                                 │
│  Substantive operationalization (documented):                   │
│  - Ceremony schedules (CORA Nation maintains record)            │
│  - Teaching records (sermons, gatherings, teachings)            │
│  - Community decisions (governance minutes)                     │
│  - Pastoral care records (counseling, support, witness)         │
│  - Member participation logs (attendance, contribution)         │
│                                                                 │
│  These records are auditable internally and produced to         │
│  examiners if requested. Without them, "substantive" is an      │
│  assertion. With them, the religious-community defense holds.   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  THE VILLAGE (CORA Nation Media Ministry)                       │
│                                                                 │
│  - Documents religious community life, ceremony, character      │
│  - Educational + inspirational content (Bruderhof analog)       │
│  - Does NOT promote economic instruments of any kind            │
│  - Does NOT solicit investment in Brand LLCs                    │
│  - Does NOT promote Brand LLC commercial offerings              │
│  - Brand LLCs market through their own commercial channels      │
│  - Participants sign media release before appearing on camera   │
└─────────────────────────────────────────────────────────────────┘
```

## Religious doctrine codification (v0.3 timeline)

CORA Nation religious doctrine, currently practiced but not formally codified, is the legal foundation of the entire 508(c)(1)(A) defense. Codification timeline:

- **30 days:** Compile existing canonical sources (Coherent Champions Manifesto, World Peace Agreement, Mirror Constitution, Character Card framework, Coherent Treasury v0.10 §Covenant Layer) into a single "CORA Nation Canon v0.1" document.
- **60 days:** Add narrative theology / doctrinal statement (core beliefs, ceremony purposes, role of stewardship, position on resources/exchange/community).
- **90 days:** Documented community-process ratification (members vote or witness assent under documented procedure).
- **120 days:** Counsel-reviewed canon, available for IRS examination if requested.

This timeline is non-negotiable — without codified doctrine, every other legal defense becomes weaker.

## Arm's-length documentation requirements (v0.4 deliverables)

The following templates must be drafted (deferred to v0.4 if v0.3 converges first):

1. **Brand LLC Operating Agreement** (provision: CORA Nation does not direct Brand LLC operations, governance, pricing, or staffing)
2. **Brand LLC ↔ CORA Nation Charitable Contribution Agreement** (provision: contributions are voluntary, not contractual; no quid pro quo; no obligation tied to member access)
3. **Conflict-of-Interest Policy for Stewards** (handles dual CORA-member-and-Brand-LLC-owner relationship; recusal from CORA Nation decisions affecting their own Brand LLC)
4. **CORA Nation Substantive Religious-Community Documentation Protocol** (ceremony schedules, teaching records, pastoral care, member participation logs — recordkeeping standards)
5. **CORA Nation §4958 Rebuttable-Presumption Documentation Template** (for community-provision compensation determinations)

---

## What v0.3 explicitly does NOT do

- **Does not introduce Brand-specific tokens.** Same as v0.2 — deferred.
- **Does not specify Coherent Credit demurrage rate.** Open question; not blocking.
- **Does not address state charitable registration.** Open question; relevant when soliciting from multiple states.
- **Does not resolve IRC §501(d) apostolic association question.** Requires licensed counsel; flagged as open question.
- **Does not finalize CR entity structure.** Specifies that CR counsel must establish — does not assert a specific structure.

---

## Open questions for human counsel (after v0.3 convergence)

These remain for the 1-2 hour licensed-counsel sign-off pass:

1. Does community-provision compensation, even with §4958 documentation, constitute employment under either US or CR law for any Steward?
2. Does the Coherent Credit closed-loop structure (CORA-only redemption, no transfer) hold under all applicable state MTL regimes?
3. Does the overall Brand LLC ↔ CORA relationship (Stewards as both LLC owners and CORA members; voluntary charitable contributions; arm's-length documentation) create private benefit endangering 508(c)(1)(A)?
4. Does the Covenant Layer structure trigger IRC §501(d) apostolic association classification?
5. What is the proper CR legal entity structure for Camp Zen, and how does the contribution flow legally between CR and US jurisdictions?
6. Are there state-level charitable solicitation registration requirements triggered by CORA Nation's national online membership intake?

---

## What changed structurally between v0.1 → v0.2 → v0.3

| Issue | v0.1 | v0.2 | v0.3 |
|---|---|---|---|
| Brand tokens | revenue distribution + NAV redemption + equity splits | deferred entirely | deferred entirely |
| Coherent Credit | not central | redeemable at CORA + Brand LLCs (via barter settlement) | redeemable at CORA ONLY |
| Member-to-member transfer | implied | allowed within community | NOT ALLOWED |
| Steward compensation | 70/30 equity split (inurement) | community-provision (asserted) | community-provision (with hard §4958 precondition) |
| Brand LLC equity | held by Communal Treasury | independent + voluntary contributions | independent + voluntary contributions, arm's-length DOCUMENTED |
| Mockumentary | demand-gen for tokens | severed (recharacterized media ministry) | severed (with media releases required) |
| Costa Rica entity | unaddressed | flagged as open question | HARD PRECONDITION for Camp Zen ops |
| Religious doctrine | assumed | acknowledged as gap | 30/60/90/120-day codification timeline |
| §4958 documentation | unaddressed | acknowledged as open question | HARD PRECONDITION for community-provision |
| Arm's-length docs | implied | asserted | deliverables specified (v0.4 templates) |

The architecture is increasingly modest in claims and increasingly explicit in operational preconditions. This is the right trajectory.
