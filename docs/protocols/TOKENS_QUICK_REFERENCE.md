# Token Strategy Quick Reference

**Version:** 1.0.0  
**Full Document:** `docs/protocols/TOKENS_STRATEGY.md`  
**Print This:** Keep at your desk or in God Mode dashboard  

---

## Token Stack (3 Tokens Only)

| Token | Role | Key Rule |
|-------|------|----------|
| **UC** | Spend / Cash Rail | 1 UC = $1 USD (service credits) |
| **TRUST** | Commons Membership | Earned, not purchased. Needs-support, not yield. |
| **$FI** | FI-Art Domain | Sacred circulation for art. Feeds into commons. |

---

## TRUST Token Rules

### How Members Get TRUST
- **Earn it** through contribution (time, service, donations, art, referrals)
- **NOT purchased** like a security
- **Active participation required** (Proof of Contribution)

### What TRUST Provides
- ✅ Needs-based support (housing, health, education) when commons has abundance
- ✅ Governance voice (weighted by TRUST + participation)
- ✅ Access to ministry programs
- ❌ NOT financial returns
- ❌ NOT passive yield
- ❌ NOT redeemable for cash

---

## Entity Structure

```
Church of Consciousness (508c1a)
    │
    ▼
Sunheart Private Trust
    └── Commons Reserve Fund
            │
            ▼
Cora Nation PMA
    └── Commons Ministry (TRUST)
            │
            └── Members → Needs-support
```

**Revenue Flow:** LLC → Trust → Commons Reserve → Ministry Benefits

**Live Ledger Mapping (Credits Gateway):**
- Commons Reserve: `system:commons`
- Emergency Reserve: `system:reserve`

---

## Trust Index (0-1)

| Component | Weight |
|-----------|--------|
| Solvency (THS) | 40% |
| Commons Health | 30% |
| Participation | 30% |

| Trust Index | Posture | Distribution |
|-------------|---------|--------------|
| < 0.3 | Conservative | Survival only |
| 0.3-0.7 | Balanced | Survival + Stability |
| > 0.7 | Generous | All categories |

---

## Needs Categories

| Category | % | Examples |
|----------|---|----------|
| Survival | 40% | Food, shelter, health |
| Stability | 25% | Debt relief, emergency |
| Growth | 20% | Education, tools |
| Contribution | 10% | Contributor recognition |
| Infrastructure | 5% | Public goods |

---

## Hard Guardrails (AI Cannot Override)

| Guardrail | Value |
|-----------|-------|
| Minimum reserve ratio | 120% |
| Max daily change | 5% |
| Emergency freeze | THS < 0.8 |
| Human override | Always available |

---

## Forbidden Language

| ❌ Forbidden | ✅ Use Instead |
|-------------|----------------|
| Investment | Contribution, participation |
| Profit, returns, yield | Blessings, abundance, ministry benefits |
| Dividend | Gift, needs-support |
| ROI | Service access, blessings received |
| Guaranteed | Intended, designed to |

---

## Required Disclaimers

```
- "TRUST is not an investment. No financial returns are promised."
- "Ministry benefits based on participation and abundance, not guaranteed."
- "Private membership arrangement, not a public offering."
- "Service credits have no cash value."
```

---

## Proof of Contribution (Required for Benefits)

| Activity | Score |
|----------|-------|
| Service to others | 10/hour |
| Governance vote | 5/vote |
| Art creation | Variable |
| Referral | 50/member |
| Financial contribution | 1/UC |

**Minimum for benefits:** 100 per quarter

---

## Key Files

| What | Path |
|------|------|
| Full Strategy | `docs/protocols/TOKENS_STRATEGY.md` |
| UC Protocol | `docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md` |
| $FI Policy | `FI-Art/legal/SACRED_CIRCULATION_POLICY.md` |
| Commons Charter | `docs/legal/commons/COMMONS_MINISTRY_CHARTER.md` |

---

## For AI Agents

```python
# When asked about tokens:
TOKENS_STRATEGY = "docs/protocols/TOKENS_STRATEGY.md"
VERSION = "1.0.0"

# Token stack
UC = "Spend token, 1:1 USD"
TRUST = "Commons token, earned not purchased"
FI = "Domain token, FI-Art ministry"

# Key principle
PRINCIPLE = "Needs-meeting, not investment"
```

---

**Remember:** Language matters. Economics matter. They must match.

🌐⚡💎
