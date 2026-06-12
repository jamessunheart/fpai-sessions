# CORA Nation Allocation Platform — v0.1 Proposal (pre-spec)

**Status:** Pre-spec proposal for Counsel pressure-test before drafting platform spec
**Drafted:** 2026-05-12
**Builds on:** Brand Tokenization Architecture v0.4 CONVERGED (`BRAND_TOKENIZATION_ARCHITECTURE_v0.4_CONVERGED.md`)
**Purpose:** Add a "Layer 3 — Governance" platform to the converged architecture that lets CORA Nation members hold weighted allocation voice over future church treasury flows + steward provisions, with maximum freedom up to the legal line.

---

## Why this layer

v0.4 converged architecture has three operational layers:
1. **CORA Nation 508(c)(1)(A)** — religious-community tier (membership, ceremony, doctrine)
2. **Coherent Credit closed-loop** — service-access currency (earn by contribution, redeem for CORA services, demurrage, no transfer, no purchase)
3. **Brand LLC tier** — independent commercial entities; arm's-length from CORA; raise actual capital via Reg D / Reg CF

This proposal adds:

4. **CORA Allocation Platform** — non-economic governance layer letting members hold and exercise weighted voice over future treasury allocations + Steward-provision flows + community-level decisions, with structural guardrails enforced at the protocol layer (not policy).

The goal is to give members the **functional experience** of participating in community wealth-creation — earning visible status, sharing voice, shaping where resources go — WITHOUT crossing into:
- Securities (Howey investment contract)
- Money transmission (MTL)
- Inurement (§4958)
- Disguised commerce inside PMA wrapper

---

## Core design principles

| Principle | Mechanism |
|---|---|
| **Allocation Weight is governance, not equity** | Holder receives no money, no services from holding; only votes |
| **Earned, never sold** | No purchase path exists in the platform; no "investment of money" prong satisfied |
| **Structurally enforced guardrails** | API design prevents unsafe states (no transfer endpoint, no purchase endpoint, etc.); not "policy compliance" but "system cannot do X" |
| **§4958 auto-documentation** | Platform generates rebuttable-presumption docs from system data for any community-provision flow |
| **Recusal enforced** | Steward cannot vote on flows benefiting their own Brand LLC; system queries conflict matrix and auto-blocks |
| **Decay over time** | Weight decays if inactive — keeps governance current, prevents accumulation into property-like asset |
| **Religious-community governance frame** | Operates under CORA Nation bylaws + 1st Amendment church-governance protections |
| **PMA wall preserved** | All activity intra-member; no outside-PMA holders or trading venues |

---

## Proposed freedom tiers

### Tier A — MAX freedom (built in from v0.1)

1. **Unlimited earning by witnessed contribution** — multiple earning paths, no individual cap
2. **Pure gift transfer member-to-member** — no price, no consideration, public log with stated reason
3. **Public recognition gifting** — member mints "gratitude" weight from community pool (not own balance) to publicly attest another member's contribution
4. **Vote delegation** — revocable proxy on specific votes; ownership retained
5. **Pool-and-vote** — members pool weight on a temporary campaign vote
6. **Spend-down for CORA services** — use weight to redeem retreat seats, ceremony access, witnessing services
7. **Tier-graduated rights** — Apprentice / Steward / Elder tiers vote on different scopes per bylaws
8. **Sub-Circles** (Working Circles) — Camp Zen Circle, Brain Circle, Land Circle have allocation authority within their domain; mirrors deaconry/ministry polity
9. **Inheritance / bequest within PMA** — designate beneficiary members on exit/death; lapses to community pool if no eligible recipient
10. **Stewardship succession** — role transitions transfer accumulated weight
11. **Public visibility** — leaderboards, ceremony, status display
12. **Witnessed cross-platform earning** — donating land, running retreats free, building infra all mint weight
13. **Co-witnessed earning** — multiple members earn weight together for joint work
14. **Bylaw meta-vote** — members can vote to amend bylaws themselves per documented member-process
15. **Public ceremony for high-weight events** — big allocation votes ceremonialized; reinforces religious-community character
16. **Sabbatical pause** — declared sabbatical pauses decay clock without preserving economic value

### Tier B — CONTROLLED freedom (allowed with structural guardrails)

1. **Gift transfer between members** — allowed; **structural guardrail:** no price field; reason required; pattern detection on reciprocal gift loops auto-flags for review
2. **Steward influence over Brand-charity flows** — recusal where own Brand benefits; supermajority + documented member-process required for any flow to single Brand above threshold
3. **Allocation to community-provision (Steward stipends)** — §4958 rebuttable-presumption auto-doc generated; recused approval enforced
4. **Cross-Circle weight portability** — allowed but audit-logged to prevent shell-circle dodge
5. **Bequest beyond immediate family** — allowed but recipient must be PMA member; lapses to community pool if no eligible recipient
6. **Decay pause for documented reasons** — requires recorded justification, max duration cap

### Tier C — GREY ZONE (flagged for Counsel)

These are features that *might* hold legally but require Counsel's judgment. Proposing to spec them as DEFERRED in v0.1 platform, with explicit Counsel-pass before activation.

1. **Tradeable inside PMA at member-set rates for CORA services** — does this become MTL even if denominated in services not cash?
2. **"Stewardship bond" tokens** — earn now, redeem deferred service later, tradable inside PMA — does deferred-redemption + transferability create a note-security under Reves?
3. **Brand LLC member-rate priced in weight** — does weight-as-discount currency create secondary economic value?
4. **Auction-style allocation** — members bid weight on allocation options — does auction = market = security characterization?
5. **Cross-CORA interoperability** — if other religious communities adopt similar protocol, can weight move between communities?
6. **Liquidity pool for service-providers** — Stewards pre-fund services with weight, draw upon delivery — does this create floating instrument?

### Tier D — HARD-NO (explicitly excluded from spec)

1. Sell tokens for money (Howey "investment of money")
2. Member-set price exchange for cash/crypto (MTL + secondary market)
3. Token = pro-rata share of treasury value (beneficial interest = security)
4. Transfer to outside-PMA parties (breaks the wall)
5. Reciprocal exchange ("I gift X if you gift Y") (quid pro quo barter)
6. Unlimited inheritance to non-PMA members (removes religious-community character)
7. Implied "weight will grow in value" marketing (Reves family-resemblance)

---

## Platform enforcement architecture (sketch)

```
Hard-rules (no override paths in API):
  - No /transfer endpoint accepting price field
  - No /purchase endpoint (any payment-in path)
  - No /weight/grant manual endpoint (only via /witness/log)
  - No /audit/delete endpoint
  - Self-conflict → 403, logged
  - Pattern detection on reciprocal gift loops → auto-flag for review

Cron-driven (not human-discretionary):
  - daily decay job (% per day on idle weight)
  - weekly §4958 doc generation per active provision
  - monthly compliance check (state registration, etc.)

Audit:
  - Immutable append-only log
  - Indefinite retention
  - Examiner-exportable
  - Public visibility on aggregate, member-protected on individual detail
```

---

## Specific questions for Counsel

This is what we want pressure-tested before drafting the platform spec:

### Q1 — Is the architecture itself viable?

Does the Allocation Platform, designed as pure governance voice (no economic benefit to holder, no price, no purchase path), survive Howey analysis when operated inside a 508(c)(1)(A) church + PMA frame?

### Q2 — Is gift transfer with public-witnessed reason defensible?

Member-to-member gift of weight, with no consideration, no implied return, public log with stated reason — does this survive securities analysis? Or does any transferability create characterization risk?

### Q3 — How tight must recusal mechanics be?

For Stewards voting on flows that *might* indirectly benefit them (e.g. CORA chooses to host a retreat that happens to use a Steward's Brand LLC for catering at market rate) — what's the threshold beyond which recusal must be enforced?

### Q4 — Where is the line for grey-zone features?

Specifically:
- Pricing CORA service redemption in weight (a retreat costs N weight) — okay?
- "Stewardship bonds" — earn weight now, redeem for service in 12 months — note-security risk?
- Auction-style allocation votes — does auction characterization re-open securities analysis?

### Q5 — §501(d) integration

Does the platform's existence as a member-governance layer trigger §501(d) classification? If we want to claim §501(d) apostolic association tax treatment, does the platform's structure support or undermine that claim?

### Q6 — MTL exposure

Does service-redemption denominated in weight (rather than cash) create money-transmission exposure even though no cash flows? Are we functionally operating an internal currency that requires state licensing?

### Q7 — Cross-PMA weight portability

If other religious communities adopt similar protocols, can weight transfer between them inside a federation? Does that re-open MTL / interstate-securities analysis?

### Q8 — Steward provision pattern

§4958 rebuttable-presumption with auto-doc — is auto-generation of comparable-comp data + independent-approval records + contemporaneous documentation sufficient if the system produces them, or must humans participate in each determination?

### Q9 — Hard exclusions completeness

Are there other known traps (Hutterite-pattern violations, fraternal-society pitfalls, religious-organization-specific securities issues) that should be added to the HARD-NO list before spec'ing v0.1?

### Q10 — Counsel-engagement scope

Does this platform layer change the human-counsel engagement scope already proposed in v0.4 Addendum C? Should any of the 7 deliverables be modified or added to?

---

## Pre-counsel posture

This proposal is built to show Counsel that:
1. The freedoms in Tier A are documented and defensible per the legal corpus
2. The Tier B controlled-freedoms have **structural** guardrails (system-enforced), not policy-dependent
3. The Tier C grey zone is **explicitly flagged** for their judgment — no claim of pre-determination
4. The Tier D hard-no zone is **preemptively excluded** — discipline shown
5. The architecture is intentionally narrow on day-one; expansion requires fresh review

Compatible with v0.4 CONVERGED architecture's preconditions (Trust amendment, Canon v0.1, §4958 docs, CR entity, state registration, etc.).

---

## What we want back from Counsel

A ranked critique (CRITICAL / HIGH / MEDIUM / LOW) addressing:
- Is the core architecture defensible?
- Which Tier A freedoms should move to Tier B or out entirely?
- Which Tier B guardrails need tightening?
- Which Tier C grey items can move to Tier A vs which must stay deferred or move to Tier D?
- Are there missing Tier D exclusions?
- Counsel engagement scope changes
- Open questions remaining for human counsel
