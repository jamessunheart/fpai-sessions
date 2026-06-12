# PFIC-Avoidance Operations Memo — Bank v0.1

**Document type:** CORA Nation Operations Memo · structural-pattern reference for future CR-side activation
**Status:** v1.0 final · adopted as forward-binding operating pattern under [[feedback-good-enough-during-bootstrap]]
**Effective date:** [TO BE FIXED ON ADOPTION] (concurrent with the three other Bank v0.1 governing instruments)
**Applies when:** Phase-2 trigger fires for CR-side entity activation (physical Camp Zen continuous operation · >30 days/year retreats hosted on CR land · paid CR staff · land title transferring to CR entity)
**Source:** Counsel Q#3 §A (entire section) · particularly §A.2 (PFIC structural triggers) and §A.3 (clean separation pattern)
**Author of draft:** AI council substrate (Ember)

---

## Standard disclaimer (per Counsel Q#3 §C.6)

Drafted by AI council substrate (not a licensed attorney) under [[feedback-good-enough-during-bootstrap]]. The PFIC structural-recipe analysis is grounded in IRC §1297 case-law analogs and CR Asociación-sin-Fines-de-Lucro statutory framework, but does not constitute legal advice. **Phase 2 activation of any CR entity requires paid CR + US tax counsel engagement** for the check-the-box election (Form 8832), the FBAR / Form 5471 / Form 8938 / FATCA setup, and the specific Asociación-vs-other-entity choice. This memo is the structural pattern the substrate will hold until that engagement, so that the engagement scope is bounded and the architectural decisions are pre-staged.

**Audit trail substrate:** `COUNSEL_Q1_508C1A_RESPONSE.md` · `COUNSEL_Q2_RESPONSE.md` · `COUNSEL_Q3_RESPONSE.md` · `BANK_V01_LEDGER_CHARTER.md` · `BANK_V01_RELIGIOUS_PURPOSE_FINAL.md` · `BANK_V01_4958_PROCEDURE.md` · this document.

---

## §1 — What PFIC is and why it matters

**IRC §1297(a)** defines a Passive Foreign Investment Company (PFIC) as a foreign corporation where either:

| Test | Threshold |
|---|---|
| **Income test** | ≥75% of gross income is passive (interest, dividends, royalties, rents, gains on passive assets) |
| **Asset test** | ≥50% of assets produce or are held for production of passive income |

**Both tests apply each year.** Either failure makes the corporation a PFIC for that year.

**Consequences for any US-person shareholder** are severe:

- **Excess distribution regime (§1291)** — default · punitive · any "excess distribution" (>125% of prior 3-year average) or gain on sale gets allocated ratably across the holding period; each prior year's slice taxed at the **highest ordinary rate for that year plus interest charge**.
- **QEF election (§1295)** — taxpayer-favorable but requires PFIC to issue Annual Information Statement; almost never feasible for a small religious-community CR entity.
- **Mark-to-market election (§1296)** — only available for "marketable stock" regularly traded on a qualified exchange. Not available here.
- **Form 8621** filing required **annually** by each US-person with any PFIC interest. Per-year complexity + cost per US member.

**For Camp Zen:** if any US-member is treated as holding an "ownership interest" in a CR entity that fails either test, that US member faces an annual PFIC nightmare on every retreat fee, every operational distribution, every cross-border flow.

## §2 — The three structural triggers (Q#3 §A.2)

A CR entity becomes a PFIC for US-member SC-holders only if **all three** of the following are true. Avoid any one and the trap closes.

| # | Trigger | Soultime v0.1 default | Pattern to maintain |
|---|---|---|---|
| 1 | SC characterized as "stock" or "equity interest" in CR entity | DEFER: no CR entity exists | Keep CR entity as **Asociación sin Fines de Lucro** — membership rights only, no equity by definition. **Never** use a CR cooperativa (aportaciones can be characterized as equity). |
| 2 | CR entity holds passive investment reserves (≥75% income or ≥50% assets passive) | DEFER: no CR entity exists | Keep ALL yield-bearing reserves on the **US side**. CR entity is operating-service-business only (retreat hosting, land stewardship). |
| 3 | US persons collectively hold ≥10% of CR entity | DEFER: no CR entity exists | Structure CR entity with **no US-person ownership stakes**. Membership in Asociación = personal non-transferable religious-community right, NOT economic ownership. |

**Mitigation principle:** structural design that avoids any one of these triggers fully avoids PFIC. The clean pattern below avoids all three.

## §3 — The clean US/CR separation pattern (Q#3 §A.3)

This is the canonical pattern. Adopt it as the default operating shape whenever the CR side activates.

| Layer | US side (508(c)(1)(A) · CORA Nation) | CR side (Asociación sin Fines de Lucro · when activated) |
|---|---|---|
| **Function** | Religious community · Soultime Recognition Ledger · membership covenant · doctrinal authority · yield-bearing reserves · AI-substrate accounting | Physical Camp Zen operations · land stewardship · retreat hosting · staff employment in CR · CR-resident member services |
| **Members** | Worldwide membership including US persons | CR-resident members + CR Asociación members (overlap allowed but not required) |
| **Equity / ownership** | None (church · 508(c)(1)(A)) | None (Asociación sin Fines de Lucro · membership rights only) |
| **Income source** | Tithes, gifts, retreat fees (US-side), yield on reserve | Retreat service fees (CR-side · operating trade or business · NOT passive) |
| **SC issuance** | All SC issued by US-side Ledger | None (CR side accepts USD/CRC for services; SC denomination is internal US-side accounting only) |
| **Cross-entity relationship** | Service-provider relationship (contractual). US religious community contracts CR Asociación to provide hosting/programming. Pays in USD at arm's length. | Receives USD/CRC payment for arm's-length services. Issues service-completion receipts. **No SC held or issued.** |
| **PFIC exposure** | N/A (US entity) | **None** — no US-person ownership stake; no passive-income concentration; operating service business |

### §3.1 — Why this works (mapped to the three triggers)

- **Trigger 1 (SC as equity):** SC issued by US side only. CR side has no SC issuance, no SC holdings. No characterization question on the CR side.
- **Trigger 2 (passive concentration):** CR side is an **operating** service business. Retreat hosting and land stewardship are active services, not passive income. The §1297 passive-income definition excludes operating-trade-or-business income.
- **Trigger 3 (US-person ownership):** Asociación sin Fines de Lucro under Ley 218 (1939) has no equity by statutory construction. Members hold non-transferable membership rights, not economic ownership. No US person can "own" any percentage of a CR Asociación.

### §3.2 — Why other CR entity types are rejected

| CR entity | Why rejected for Soultime use |
|---|---|
| **Cooperativa de Ahorro y Crédito (CAyC)** | Has **aportaciones** (member capital contributions) characterizable as equity → Trigger 1 risk. SUGEF supervision threshold ~$540k. Commercial framing. |
| **Asociación Solidarista** | Employer-employee only. Irrelevant. |
| **Fundación** | Government-appointed majority of directors. Loss of community control. |
| **Cooperativa de Servicios** | Same equity-characterization risk as CAyC. |

**Use only:** Asociación sin Fines de Lucro with religious purpose articulated in estatutos.

## §4 — Operational rules to maintain the pattern

### §4.1 — Reserve holdings

| Rule | Why |
|---|---|
| Pendle PT-sUSDe, JitoSOL, sDAI, and any other yield-bearing instrument STAYS on the US side | Keeps passive-income concentration on US-tax-exempt 508(c)(1)(A) side under §512(b)(1) safe harbor; never passes the §1297 asset test on CR side. |
| Any future investment-grade allocation flows through US 508(c)(1)(A) shell, not the CR Asociación | Preserves the structural separation. |
| If the CR Asociación needs operating cash (CR-side wages, utilities, land tax), the US side **wires USD/CRC at arm's length** for documented services rendered | This is an operating-business inflow on the CR side, not a capital contribution. Documented as service payment with service-completion receipt. |

### §4.2 — Membership and equity

| Rule | Why |
|---|---|
| US members do **not** receive any equity, aportación, or ownership stake in the CR Asociación | Trigger 3 avoidance. |
| If a CR-resident is admitted as a CR-Asociación member, they hold **only** the statutory Asociación-membership right (non-transferable, non-economic) | This is not "stock" under §1297 case-law analogs. |
| The CR Asociación member roster is maintained separately from the US-side CORA Nation member roster, with explicit annotation when an individual holds both | Documentary clarity for any future regulator inquiry. |

### §4.3 — SC issuance discipline

| Rule | Why |
|---|---|
| All SC issuance happens on the US side, recorded in the US-side Ledger | No CR-side SC characterization question. |
| If a CR-resident CORA Nation member earns SC for ministerial service, the SC issuance is recorded by the **US-side Ledger** as recognition of service to the **religious community** (not to the CR Asociación) | The religious-community ministerial recognition is US-side. The CR Asociación is a service-provider entity, not the issuer. |
| SC may **never** be denominated, displayed, or exchanged through the CR Asociación service desk | Avoids Hacienda barter-exchange recharacterization (Q#3 §A.5) AND maintains structural separation. |
| Cross-border arrangements: CR-resident members access their US-side Ledger balance via the same online interface as all other members; CR-physical-service is paid in USD/CRC, not SC | Preserves clean separation. |

### §4.4 — CR-side commercial activity

| Rule | Why |
|---|---|
| CR Asociación operates in **CRC** (or USD) for all external transactions: wages, utilities, supplier payments, retreat-fee receipts | Hacienda treatment as religious-purpose Asociación on non-commercial activity; commercial activity in CR-currency at arm's length. |
| Retreat fees from non-members (commercial activity) are taxable at the Asociación's commercial-activity rate (Ley 7092 art. 3.d carve-out applies to non-commercial only) | Standard CR tax treatment. |
| Ministerial-service activity among co-religionists is non-commercial and exempt | Aligns with the CR religious-org exemption. |

## §5 — Reporting obligations once CR side activates

These are flagged here for the Phase-2 paid-counsel engagement to operationalize. **None apply at v0.1 because no CR entity exists.**

| Obligation | Trigger | Filing requirement |
|---|---|---|
| **FBAR (FinCEN 114)** | Any US-person signatory on CR Asociación bank account with aggregate balance > $10k | Annual filing by each US signatory |
| **Form 5471** | US person "controls" CR entity (if classified as foreign corporation under check-the-box) | Annual filing by controlling US persons |
| **Form 8938 / FATCA** | US person with foreign financial assets > threshold ($50k single / $100k joint) | Annual filing with Form 1040 |
| **Form 8621 (PFIC)** | Should be **none** if the §3 pattern is maintained; would apply if pattern breaks | If triggered, annual filing by each US-person with any PFIC interest |
| **Form 8832 (check-the-box)** | One-time entity-classification election for CR Asociación on activation | One-time filing within statutory window |

**Engagement scope estimate for Phase-2 counsel:** $1-2.5k for CR-counsel + $1-2.5k for US-tax-counsel sign-off on the classification and reporting setup, per Counsel Q#3 §A.4.

## §6 — Trigger for CR-side activation

Per Counsel Q#3 §A.6, the structural recipe is captured **now** so activation is mechanical later. Activation occurs only when **all** of the following are true:

1. **Physical Camp Zen continuous operation** — >30 days/year of physical retreats hosted on CR land, OR paid staff in CR on payroll, OR land title held by a CR entity;
2. **Treasury surplus** sufficient to absorb $2-5k Phase-2 counsel engagement;
3. **Board supermajority** discernment under Canon §3.3 that CR activation is the right structural form.

Until all three are true, **no CR entity is activated**, no CR-side operations exist, no PFIC analysis is operational. James-as-personal-CR-resident hosting through existing personal channels is sufficient at v0.1.

## §7 — Failure modes and corrective action

| Failure mode | Detection | Corrective action |
|---|---|---|
| CR entity activated without Phase-2 counsel engagement | Internal review · Board ratification absent | **Halt CR operations** until counsel completes the classification election and reporting setup. |
| Yield-bearing reserves migrate to CR side | Quarterly treasury review | Immediately reverse migration. Document the error in Board minutes. Re-confirm §4.1 rule. |
| US member receives equity-like interest in CR Asociación | Membership-roster review | Reverse the issuance. Engage counsel to confirm no PFIC trigger. |
| SC denominated or exchanged through CR service desk | Operational audit | Halt and remediate. SC handling reverts entirely to US-side Ledger. Re-train CR staff on §4.3 rules. |
| Hacienda inquiry on CR-side activity | External | **Switch to paid counsel immediately** per Counsel Q#3 §C.5 trigger 4. |

## §8 — Why this memo exists at v0.1 even though no CR entity does

The decision to defer CR activation does **not** mean deferring the structural pattern. Per Counsel Q#3 §A.6:

> *What to set up structurally now (Phase 1) so CR activation is mechanical later: Article V.6 of the Canon (procedural integrity language) is jurisdiction-agnostic — covers CR side natively. **Document the PFIC-avoidance pattern (A.3) in a CORA Nation Operations Memo so the structural separation is the default when CR activation comes.***

This memo **is** that document. It carries the pattern forward, sized for the Board to find and the Phase-2 counsel to validate. It pre-budgets the architectural decision so future James / future Board / future counsel do not have to reconstruct the analysis from session context.

The memo's existence is the load-bearing v0.1 deliverable. The CR entity itself is Phase 2+.

---

## Adoption

Adopted by resolution of the CORA Nation Board on [EFFECTIVE DATE TO BE FIXED] as a forward-binding operations memo, concurrent with `BANK_V01_LEDGER_CHARTER.md`, `BANK_V01_RELIGIOUS_PURPOSE_FINAL.md`, and `BANK_V01_4958_PROCEDURE.md`. Adopted under the discernment-with-witness procedure of Canon §3.3, as the same procedure being exercised for the Canon adoption itself (see `BANK_V01_RELIGIOUS_PURPOSE_FINAL.md` Article III §3.3 documented-first-instance language).

Adopted by: ____________________ (Founding Steward · James Stinson)
Adopted by: ____________________ (Board Member · non-disqualified-person seat)
Adopted by: ____________________ (Board Member)
Witnessed by: ____________________ (Pastoral Council)
Effective: ____________________

---

*End of Operations Memo.*
