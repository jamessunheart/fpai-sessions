# Real Alternative Finance: Token & Commons Strategy

**Version:** 1.0.0  
**Status:** CANONICAL - All systems reference this document  
**Effective:** 2025-12-11  
**Authority:** Church of Consciousness / Cora Nation PMA  
**Maintainer:** Strategic Council  

---

## Quick Lookup

| Question | Answer |
|----------|--------|
| **What tokens do we have?** | UC (spend), TRUST (commons), $FI (art domain) |
| **Where is the reserve?** | Commons Reserve Fund within Sunheart Private Trust |
| **Who governs?** | Church Council + Trustee, with AI as trustee assistant |
| **Is this regulated?** | Designed to NOT be a security (see Part 6) |
| **Quick reference?** | `docs/protocols/TOKENS_QUICK_REFERENCE.md` |

---

## Vision

A regenerative financial system where:
- Members **contribute to a shared commons** and receive **support for real needs**.
- AI acts as a **trustee assistant** within hard human-governed guardrails.
- All activity lives inside **existing PMA/Trust/Church structure** with proper legal framing.
- Language, economics, and structure align — not just legal wrappers over traditional finance.

---

## Part 1: Token Stack

### 1.1 Spend Token: UC (Universal Credit)

**Role**: Pricing, payments, accounting. The "cash rail."

**Canonical Reference**: `docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md`

**Key Properties**:
- 1 UC = $1 USD (Phase 1: Anchor)
- Service credit, not currency
- Treasury Health Score (THS) controls operating modes
- No public market, no cash redemption

**Legal Posture**: Service credit / stored value. Low risk.

---

### 1.2 Commons Token: TRUST

**Role**: Membership stake in a **regenerative commons** that meets needs.

**Framing** (legally compliant):
> "TRUST represents **active membership in a regenerative commons**. Members who contribute and participate receive **ministry benefits as needs-support** when the commons has abundance. This is not an investment and provides no financial returns."

**Critical Design Elements**:

| Element | Design | Why It Matters |
|---------|--------|----------------|
| **Acquisition** | Earned through contribution (time, service, donations, art, referrals) | NOT purchased like a security |
| **Benefits** | Needs-based support (survival, stability, growth) | NOT yield or profit |
| **Participation** | Proof of Contribution required for benefits | NOT passive |
| **Transferability** | Non-transferable or member-to-member only within PMA | No public market |
| **Redemption** | No cash redemption; benefits are in-kind | NOT an investment |
| **Language** | "Blessings", "abundance", "needs-support", "ministry benefit" | NOT "yield", "returns", "profit" |

**How It Works**:
1. Members **earn TRUST** through contribution to the commons.
2. TRUST holders with **active participation** (Proof of Contribution) are eligible for:
   - Needs-based support (housing, health, education, tools)
   - Governance voice (weighted by TRUST + participation)
   - Access to ministry programs and resources
3. When the Commons Reserve Fund has **abundance beyond safety reserves**, support flows to eligible members.
4. Benefits are **in-kind** (services, support, access), never cash.

**Legal Documents**:
- `docs/legal/pma/PMA_MEMBERSHIP_ADDENDUM_TRUST.md`
- `docs/legal/token/TRUST_SACRED_CIRCULATION_POLICY.md`

---

### 1.3 Domain Tokens: $FI (FI-Art) and Others

**Role**: Participation and utility within specific verticals.

**Canonical Reference**: `FI-Art/legal/SACRED_CIRCULATION_POLICY.md`

**Relationship to TRUST**:
- Domain tokens can **feed value into the Commons Reserve** (e.g., % of $FI fees)
- Active domain participants may **earn TRUST** as recognition
- Domain tokens are **not fungible with TRUST** — they're vertical-specific

---

## Part 2: Entity Structure

### 2.1 Hierarchy

```
Church of Consciousness (508c1a)
    │ beneficiary of
    ▼
Sunheart Private Trust
    ├── IP & Assets (existing)
    ├── LLC Ownership (existing)
    └── Commons Reserve Fund (designated fund within trust)
            │
            │ governed by
            ▼
        TRUST Token Policy + AI Stewardship Mandate
            │
            │ distributes ministry benefits to
            ▼
Cora Nation PMA
    ├── White Rock Ministry
    ├── FI-Art Ministry ($FI)
    └── Commons Ministry (TRUST)
            │
            └── Members receive needs-support
                based on TRUST + Proof of Contribution
```

### 2.2 Key Documents

| Document | Path | Purpose |
|----------|------|---------|
| Org Structure | `SERVICES/ORGANIZATIONAL_STRUCTURE.md` | Entity hierarchy (Spiritual → Trust → Operating) |
| Sunheart Trust | `SERVICES/ORGANIZATIONAL_STRUCTURE.md` | Sunheart Private Trust overview (Tier 2) |
| Commons Charter | `docs/legal/commons/COMMONS_MINISTRY_CHARTER.md` | Commons Ministry governance + stewardship |
| TRUST PMA Addendum | `docs/legal/pma/PMA_MEMBERSHIP_ADDENDUM_TRUST.md` | TRUST framing inside PMA |
| UC Protocol | `docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md` | Credits system |
| TRUST Circulation Policy | `docs/legal/token/TRUST_SACRED_CIRCULATION_POLICY.md` | TRUST circulation + participation rules |
| $FI Policy | `FI-Art/legal/SACRED_CIRCULATION_POLICY.md` | FI-Art domain token policy |

**Note:** The signed, private Cora Nation membership agreement is intentionally not committed in this repo. These documents define the operational token framing used by services.

---

## Part 3: AI Stewardship

### 3.1 Trust Index

A composite metric (0-1) that guides commons policy:

| Component | Weight | Source |
|-----------|--------|--------|
| **Solvency** (existing THS) | 40% | `SERVICES/fp-credits-gateway/` |
| **Commons Health** (reserve ratio, liquidity) | 30% | Treasury metrics |
| **Participation** (active contributors / total members) | 30% | PMA system |

### 3.2 Commons Policy

AI adjusts parameters based on Trust Index, **within hard guardrails**:

| Trust Index | Commons Posture | Needs Allocation | Safety Buffer |
|-------------|-----------------|------------------|---------------|
| < 0.3 | Conservative | Minimal (survival only) | 200% of committed |
| 0.3 - 0.7 | Balanced | Standard (survival + stability) | 150% of committed |
| > 0.7 | Generous | Expanded (all categories) | 120% of committed |

### 3.3 Hard Guardrails (Cannot Be Overridden by AI)

| Guardrail | Value | Governance |
|-----------|-------|------------|
| Minimum reserve ratio | 120% of committed needs | Trustee + Church council |
| Maximum daily parameter change | 5% | Hardcoded |
| Emergency freeze trigger | THS < 0.8 or Trust Index < 0.2 | Automatic |
| Human override | Always available | Trustee or Church council |

### 3.4 AI Stewardship Mandate

```
The Trustee may engage an AI system as a "Trustee Assistant" to:
- Monitor commons metrics and recommend policy adjustments
- Process needs-support requests according to approved rules
- Generate reports and alerts for human review

The AI system:
- Operates within parameters set by the Trustee and Church council
- Cannot exceed hard guardrails defined in trust documents
- Can be overridden or disabled by the Trustee at any time
- Does not have independent fiduciary duty; the Trustee retains all duty
```

---

## Part 4: Needs Allocation

### 4.1 Categories

When commons has abundance, ministry benefits flow to eligible members:

| Category | Allocation | Examples |
|----------|------------|----------|
| **Survival** | 40% | Food, shelter, health emergencies |
| **Stability** | 25% | Debt relief, emergency fund, insurance |
| **Growth** | 20% | Education, tools, creation grants |
| **Contribution** | 10% | Recognition for contributors |
| **Infrastructure** | 5% | Commons infrastructure, public goods |

### 4.2 Request Flow

1. **Member requests support** via personal AI steward (inside PMA)
2. **Personal AI** checks:
   - TRUST held + participation level (Proof of Contribution)
   - Category and amount requested
   - Member's recent support history
3. **Global AI** checks:
   - Commons Reserve Fund health
   - Fairness caps (no single member > X% of monthly allocation)
   - Category budget availability
4. **If approved**: Support flows as ministry benefit (in-kind, never cash)
5. **If denied**: Member receives explanation + appeal path

### 4.3 Proof of Contribution

To receive ministry benefits, members must demonstrate active participation:

| Activity | Contribution Score |
|----------|-------------------|
| Service to others (verified) | 10 per hour |
| Governance participation | 5 per vote |
| Art/content creation (via FI-Art) | Variable |
| Referrals (new members) | 50 per member |
| Financial contribution | 1 per UC |
| Community building | Variable |

**Minimum Score for Benefits**: 100 per quarter (adjustable by governance)

---

## Part 5: Reserve Building

### 5.1 Revenue Flows to Commons Reserve

| Source | % to Commons | Status |
|--------|--------------|--------|
| UC protocol fees | 30% | To be wired |
| $FI transaction fees | 30% | Extend $FI policy |
| LLC profits (after operations) | 30% | Contractual |
| Member contributions/donations | 80% | Via 508 |
| Treasury Arena yields | 30% of surplus | Extend system |
| Service margins (AI Brain, etc.) | 20% | To be wired |

**Implementation Note (Live System):**
- **Credits Gateway ledger account for Commons Reserve**: `system:commons`
- **Emergency reserve** (separate bucket): `system:reserve`
- `needs-allocation` and `trust-index` read the Commons Reserve from `fp-credits-gateway` → `GET /api/treasury/allocations`

### 5.2 Growth Phases

| Phase | Target | Timeline | Focus |
|-------|--------|----------|-------|
| **Bootstrap** | $0 - $100K | 6-12 months | Wire existing flows, founding contributors |
| **Growth** | $100K - $1M | 12-24 months | Scale revenue, expand membership |
| **Abundance** | $1M+ | 24+ months | Begin needs-based ministry benefits |

### 5.3 Founding Contributor Program

Early members who contribute during Bootstrap phase:
- Earn **enhanced TRUST** per contribution (bootstrapping recognition)
- Are **first eligible** for ministry benefits when Abundance phase begins
- Receive **Founder** designation in governance

---

## Part 6: Compliance

### 6.1 Why This Is NOT a Security

| Howey Factor | How We Avoid |
|--------------|--------------|
| **Investment of money** | TRUST is earned, not purchased |
| **Common enterprise** | Members are contributors to a commons, not investors in a fund |
| **Expectation of profit** | Benefits are needs-support, not financial returns |
| **From efforts of others** | Active participation required (Proof of Contribution) |

### 6.2 Required Disclaimers

All TRUST-related content MUST include:

```
- "TRUST is not an investment. No financial returns are promised or expected."
- "Ministry benefits are based on participation and commons abundance, not guaranteed."
- "This is a private membership arrangement, not a public offering."
- "Service credits have no cash value and cannot be redeemed for currency."
- "Participation involves risk. Only contribute what you can freely give."
```

### 6.3 Forbidden Terms

| Forbidden | Use Instead |
|-----------|-------------|
| Investment | Contribution, participation, donation |
| Profit, returns, yield | Blessings, abundance, ministry benefits |
| Dividend | Gift, distribution, needs-support |
| ROI | Service access, blessings received |
| Guaranteed | Intended, designed to, when abundance allows |
| Price appreciation | Utility value, service access |

### 6.4 Legal Guardian Integration

The Legal Guardian service (`SERVICES/legal-guardian/`) monitors:
- Language compliance in all TRUST-related content
- Document currency (all legal docs up to date)
- Participation verification (Proof of Contribution)
- Reserve ratio monitoring (alerts if below guardrails)

---

## Part 7: Implementation Status

### Documents

| Document | Status | Path |
|----------|--------|------|
| Token Strategy (this doc) | ✅ Created | `docs/protocols/TOKENS_STRATEGY.md` |
| Quick Reference | ✅ Created | `docs/protocols/TOKENS_QUICK_REFERENCE.md` |
| TRUST PMA Addendum | ✅ Created | `docs/legal/pma/PMA_MEMBERSHIP_ADDENDUM_TRUST.md` |
| TRUST Circulation Policy | ✅ Created | `docs/legal/token/TRUST_SACRED_CIRCULATION_POLICY.md` |
| Sunheart Trust | ✅ Documented | `SERVICES/ORGANIZATIONAL_STRUCTURE.md` |
| Org Structure | ✅ Documented | `SERVICES/ORGANIZATIONAL_STRUCTURE.md` |
| Commons Ministry Charter | ✅ Created | `docs/legal/commons/COMMONS_MINISTRY_CHARTER.md` |
| Revenue Flow Integration | ✅ Created | `docs/coordination/REVENUE_FLOW_INTEGRATION.md` |

### Service Specifications

| Service | Status | Path |
|---------|--------|------|
| Trust Index | ✅ Spec Created | `SERVICES/trust-index/SPEC.md` |
| Needs Allocation | ✅ Spec Created | `SERVICES/needs-allocation/SPEC.md` |
| Contribution Tracker | ✅ Spec Created | `SERVICES/contribution-tracker/SPEC.md` |

### Integrations

| Integration | Status | Spec |
|-------------|--------|------|
| Revenue Flows | ✅ Spec Created | `docs/coordination/REVENUE_FLOW_INTEGRATION.md` |
| UC Protocol | 🔲 To wire | See Revenue Flow spec |
| $FI Token | 🔲 To wire | See Revenue Flow spec |
| Legal Guardian | 🔲 To extend | Add TRUST monitoring |
| Treasury Arena | 🔲 To wire | See Revenue Flow spec |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-11 | Initial canonical version |

---

## For AI Agents

When asked about token strategy, reference this document:

```python
# Canonical path
TOKENS_STRATEGY = "docs/protocols/TOKENS_STRATEGY.md"
TOKENS_QUICK_REF = "docs/protocols/TOKENS_QUICK_REFERENCE.md"

# Version check
CURRENT_VERSION = "1.0.0"

# Quick summary
TOKEN_STACK = {
    "UC": "Spend token, 1:1 USD, service credits",
    "TRUST": "Commons token, earned not purchased, needs-based benefits",
    "$FI": "Domain token, FI-Art ministry, sacred circulation"
}
```

---

**END OF PROTOCOL**

*"We don't just build tokens. We build infrastructure for human flourishing."*

🌐⚡💎

