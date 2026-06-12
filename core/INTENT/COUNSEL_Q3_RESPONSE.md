# COUNSEL Q#3 — Costa Rica Jurisdiction · Twin Oaks Defense · Convergence Sign-Off

**Status:** Research synthesis from a non-attorney AI legal-critic substitute. NOT legal advice. This pass closes the AI-council audit trail for Soultime Recognition Ledger v0.1 internal Phase 1 launch under [[feedback-good-enough-during-bootstrap]] (multi-AI convergence = effective sign-off for internal · reversible · bounded-risk launches; paid human attorney reserved for Phase 2+ triggers).
**Date:** 2026-05-19
**Author:** AI research synthesis standing in for The Counsel (third and convergence-closing pass)
**Question framed:**
(A) What is the right Costa Rica posture for v0.1, given the PFIC trap Q#2 surfaced?
(B) Does the CORA Canon Religious-Purpose Draft survive the Twin Oaks stress-test?
(C) Where does the three-pass AI council converge for v0.1 internal Phase 1 launch, and what specific structural moves close the audit trail?

**Disposition vs Q#1 + Q#2:** Confirms-and-tightens. Costa Rica activation is correctly deferred; the Canon draft passes Twin Oaks defense conditionally (one structural gap noted); convergence sign-off achieved with three named must-do items + one residual monitored risk + four trigger conditions for switching to paid attorney.

---

## Section A — Costa Rica jurisdiction analysis (the PFIC trap from Q#2)

### A.1 CR entity options compared

| Entity | Statute / regulator | Min. founders / capital | Speed to register | Governance | Accepts non-CR members | Tax posture |
|---|---|---|---|---|---|---|
| **Asociación sin Fines de Lucro** | Ley 218 (1939) · MEIC oversight | 10 founders · no min capital | 3-6 months | Junta Directiva (≥5 dirs); General Assembly | Yes (foreigners allowed as members; Costa Rican majority not statutorily required, but practical) | Income-tax-exempt on non-commercial activity (Ley 7092 art. 3); commercial activity taxable at 30% |
| **Asociación Solidarista** | Ley 6970 (1984) · DESAF oversight | Employer-employee structure only | 2-4 months | Junta Directiva + employer financing | No (members must be employees of sponsoring employer) | Special tax treatment for employee-savings; not applicable here |
| **Cooperativa de Ahorro y Crédito (CAyC)** | Ley 4179 (1968) + Acuerdo SUGEF 9-08 | 12 founders · ₡300M (~$540k USD) threshold for SUGEF supervision | 6-18 months (longer if SUGEF-supervised) | Asamblea de Asociados + Consejo de Administración + Comité de Vigilancia | Yes, but cross-border member admission triggers SUGEF AML scrutiny | Income-tax-exempt on operations among members (Ley 4179 art. 78); commercial sales/excise still applies |
| **Fundación** | Ley 5338 (1973) · Registro Público oversight | 1 founder · ~₡10k symbolic capital | 2-4 months | Junta Administrativa (3 directors, 1 founder-appointed + 2 government/municipality-appointed) | Yes (no membership concept — beneficiaries) | Income-tax-exempt on charitable activity per Ley 7092 |
| **Religious-association equivalent** | No separate statute; operates as Asociación sin Fines de Lucro with religious purpose articulated in estatutos | Same as Asociación | Same as Asociación | Same as Asociación + Conferencia Episcopal recognition optional (Catholic) or none required (non-Catholic) | Yes | Same exempt posture; religious-purpose strengthens defense against Hacienda recharacterization |

**Operative read for Camp Zen:** The closest CR analog to CORA Nation's 508(c)(1)(A) status is **Asociación sin Fines de Lucro with religious purpose articulated in the estatutos** — not a Fundación (government-appointed directors loses control), not a cooperativa (commercial framing + SUGEF burden), not solidarista (irrelevant). The Asociación structure leaves the religious-org cover intact and parallels the US 508(c)(1)(A) shell. This matters because the religious-purpose continuity from US-side to CR-side is what carries the substantive defense forward.

### A.2 The PFIC trap under IRC §1297 — when does a CR entity trigger PFIC?

**Statute:** IRC §1297(a) defines a Passive Foreign Investment Company as any foreign corporation if (i) ≥75% of its gross income is passive (interest, dividends, royalties, rents, gains on passive assets), OR (ii) ≥50% of its assets produce or are held for production of passive income. **Both tests apply each year.**

**Consequences for a US-person shareholder:**
- **Excess distribution regime** (default, §1291) — punitive: any "excess distribution" (distribution >125% of prior 3-year average) or gain on sale gets allocated ratably across the holding period; each prior year's slice taxed at the highest ordinary rate for that year plus interest charge.
- **QEF election** (§1295) — taxpayer-favorable: shareholder includes pro-rata share of PFIC's ordinary earnings + net capital gain annually. Requires PFIC to issue Annual Information Statement.
- **Mark-to-market election** (§1296) — available only for marketable stock (regularly traded on qualified exchange). Almost never available for closed-loop community structures.
- **Form 8621** filing required annually by each US-person with any PFIC interest.

**When does the CR Asociación / Cooperativa become a PFIC for US-member SC-holders?**

Three structural triggers:

1. **If SC is characterized as "stock" or "equity interest"** in the CR entity. Asociación sin Fines de Lucro has no equity interest by definition (members hold non-transferable membership rights, not equity) — this is favorable. A cooperativa has *aportaciones* (member capital contributions) which could be characterized as equity — this is unfavorable.
2. **If the CR entity holds passive investment reserves** (≥75% income or ≥50% assets passive). If CR side holds yield-bearing reserves (Pendle PT-sUSDe, JitoSOL, sDAI), the income test fails immediately.
3. **If US-persons collectively hold ≥10% of the CR entity** (the CFC overlay under §957 also activates Subpart F regime).

**Structural design that avoids PFIC at v0.1:**

- **Keep all yield-bearing reserves on the US side.** CR side operates as an *operating entity* for physical Camp Zen retreat services (room/board/programming) — actively engaged in a service trade or business, which is NOT passive income. Operating-trade-or-business income is excluded from §1297 passive-income definition.
- **Do not issue ownership interests in the CR entity to US members.** Membership-only-rights in a CR Asociación are not stock; SC issued by the US-side religious community to US members is not a CR-entity equity interest. Membership in a CR Asociación is at most a personal non-transferable right with no economic claim — under §1297 case law analogs, this is not "stock."
- **Maintain corporate-form separation.** US 508(c)(1)(A) shell holds the Ledger and the religious-purpose framework. CR Asociación operates the physical retreat and the land stewardship. The two entities have a contractual relationship (CR entity provides services; US entity recognizes those services through the Ledger), not a parent-subsidiary or ownership relationship.

**Verdict on PFIC trap for v0.1:** **Avoidable by structural design.** The trap only triggers if (a) the CR entity is activated *and* (b) US members hold ownership stakes in it *and* (c) the CR entity becomes passive-income-heavy. v0.1 defers CR activation entirely; even when activated, the recommended structure routes around all three triggers.

### A.3 Hybrid US-CR structure — clean separation pattern

| Layer | US side (508(c)(1)(A)) | CR side (Asociación sin Fines de Lucro, when activated) |
|---|---|---|
| **Function** | Religious community · Soultime Recognition Ledger · membership covenant · doctrinal authority · yield-bearing reserves · AI-substrate accounting | Physical Camp Zen operations · land stewardship · retreat hosting · staff employment in CR · CR-resident member services |
| **Members** | Worldwide membership including US persons | CR-resident members + CR Asociación members (overlap allowed but not required) |
| **Equity / ownership** | None (church · 508(c)(1)(A)) | None (Asociación sin Fines de Lucro · membership rights only) |
| **Income source** | Tithes, gifts, retreat fees (US-side), yield on reserve | Retreat service fees (CR-side · operating trade or business · not passive) |
| **SC issuance** | All SC issued by US-side Ledger | None (CR side accepts USD for services; SC denomination is internal US-side accounting only) |
| **Cross-entity relationship** | Service-provider relationship (contractual). US religious community contracts CR Asociación to provide hosting/programming. Pays in USD at arm's length. | Receives USD payment. Issues service-completion receipts. No SC held or issued. |
| **PFIC exposure** | N/A (US entity) | None — no US-person ownership stake; no passive-income concentration; service business |

This is the cleanest pattern. **It also matches what Q#1 implicitly assumed** (US religious shell carries the substantive cover; CR side is operational infrastructure). Q#2 raised PFIC as a risk if these layers blurred. Q#3 confirms the layers must stay strictly separated and gives the structural recipe.

### A.4 OFAC + FinCEN exposure if US capital flows into CR entity

- **OFAC** — primary risk is sanctions-list members. Standard AML/KYC at member-onboarding (already mandated by CORA Nation AML/KYC v0.1) covers this. CR is not a sanctioned jurisdiction.
- **FinCEN cross-border reporting** —
  - **FBAR (FinCEN 114)** — US persons with >$10k aggregate signature authority over foreign accounts file annually. CR Asociación bank account triggers this for US-side signatories (James, board members with co-signature). **Mitigation:** strict accounting of who holds CR signature authority; FBAR filings included in CORA Nation operational compliance calendar.
  - **Form 5471** — US person controlling foreign corporation files. An Asociación sin Fines de Lucro is not a "corporation" for US tax purposes if it qualifies as a foreign nonprofit equivalent — this needs careful classification election (Form 8832 check-the-box analysis). **Mitigation:** confirm classification with CR + US tax counsel before any CR funding flows.
  - **Form 8938 / FATCA** — US persons with foreign financial assets >threshold ($50k single / $100k joint) report. Same FBAR-class analysis.
- **FinCEN MSB** — only triggers if US-side religious community accepts/transmits funds for non-members or converts SC ↔ fiat for non-members. **v0.1 design (no fiat redemption) keeps this at zero.**

**Verdict:** US-CR capital flows at v0.1 carry **manageable** OFAC/FinCEN exposure handled by standard nonprofit-treasury compliance (AML/KYC + FBAR + FATCA on signature authority). No money transmitter analysis needed at v0.1. **This becomes more complex at Phase 2** if external US members contribute capital that flows to CR side — separate counsel engagement needed before that.

### A.5 CR Hacienda treatment of internal community scrip

CR tax authority (Dirección General de Tributación, "Hacienda") treats barter and internal-currency transactions under Ley 7092 (Income Tax Law) and Ley 6826 (VAT/Sales Tax Law). The framework:

- **Income recognition:** Any transaction in money or money's-worth at FMV is taxable income to the recipient. Internal scrip exchanged for goods/services creates an FMV-equivalent income event for the recipient.
- **VAT (IVA):** Commercial goods/services trigger 13% IVA at FMV regardless of payment medium.
- **Religious-organization exemption:** Asociación sin Fines de Lucro with documented religious purpose is exempt from income tax on non-commercial activity (Ley 7092 art. 3.d). Religious-community sacramental and non-commercial activity does not trigger income or IVA.

**Is there a CR equivalent to US §501(d)?** No. CR has no statutory communal-religious-association exemption. The closest cover is: Asociación sin Fines de Lucro with religious purpose articulated in estatutos + non-commercial framing + no FMV pricing of internal exchanges.

**Hacienda risk for SC if CR-side activation happens:**

- If CR Asociación accepts SC as payment for physical services at Camp Zen → Hacienda will recharacterize as barter exchange + IVA + income tax to both sides at FMV. **This is the largest CR-side risk.**
- **Mitigation:** CR side operates entirely in USD (or CRC if local) at arm's length. SC denomination is internal US-side accounting only. CR-resident members who hold SC redeem them in US-side religious-community contexts (e.g., online programming, retreats hosted in US-religious-community-framework form, AI-substrate services), not through CR entity service desk.

### A.6 Recommended CR posture for v0.1

**Defer CR entity activation entirely at v0.1.** Three reasons:

1. **No need:** v0.1 is 8-member internal cohort with no required physical CR operations beyond what existing CORA-related Camp Zen activity already covers. No new CR entity required for v0.1 launch.
2. **No PFIC risk if no CR entity exists.** Cleanest possible posture.
3. **Lower attorney spend:** AI-council pass on US side is the sign-off; CR-side scoping can be opened later when surplus exists to absorb $1-2k CR-counsel engagement.

**What to set up structurally now (Phase 1) so CR activation is mechanical later:**

- Article V.6 of the Canon (procedural integrity language) is jurisdiction-agnostic — covers CR side natively.
- Document the **PFIC-avoidance pattern** (A.3 above) in a CORA Nation Operations Memo so the structural separation is the default when CR activation comes.
- Reserve the question of CR Asociación-vs-other-entity for Phase 2 CR-counsel engagement; do not pre-commit.

**Trigger for activating CR entity:** Physical Camp Zen continuous-operation status (>30 days/year of physical retreats hosted on CR land · paid staff in CR · land title transferring to CR entity). Below this threshold, James-as-personal-CR-resident hosting through existing channels is sufficient.

---

## Section B — Twin Oaks defense critique of the CORA Canon draft

### B.1 The five-test framework from Q#2

Per *Twin Oaks Community v. Commissioner*, 87 T.C. 1233 (1986), and the *Seeger / Yoder / Bubbling Well* line: a religious-community claim survives IRS scrutiny if and only if the doctrine names a supreme reality in religious terms (not philosophical), identifies sacramental practices, establishes doctrinal authority, documents doctrinal continuity, and reads to an examiner as "real religious community" rather than "wellness/coaching with religious branding." I'll apply each test to the CORA Canon draft at `/Users/jamessunheart/FPAI_Cockpit/core/INTENT/CORA_CANON_RELIGIOUS_PURPOSE_DRAFT.md`.

### B.2 Test 1 — Supreme reality named in religious (not philosophical) terms

**Article I §1.1:** *"CORA Nation serves the maximization of soul-time-to-full-potential across all beings, in the soonest sustainable window. This is our God, named in the form most truthful to how we have encountered the sacred."*

**Verdict: Passes, with one structural strengthening recommended.** The draft does name a supreme reality and explicitly uses the word *God* and *the sacred*. It locates the supreme reality not as preference but as encountered. §1.6 affirms it as faith, not philosophy. §1.2 anchors soul-time in religious-substantive terms ("substrate on which essence-of-being unfolds"), not in productivity or wellness language.

**One structural strengthening:** the *Twin Oaks* court was particularly skeptical of doctrine that *could* be restated in secular terms without loss of meaning. "Soul-time maximization" can be restated as "self-actualization in voluntary community" — which is exactly the Twin Oaks claim that failed. The draft mitigates this in §1.1 by naming it as God and in §1.6 by affirming faith-character, but the Canon would be strengthened by **one paragraph linking soul-time explicitly to a transcendent/sacred reality irreducible to secular psychology** — e.g., a passage articulating that soul-time is "the form in which Spirit acts through embodied being," or "the breath of the Logos in time" (using whatever language reflects the community's actual experience). The draft gestures at this in §1.1 ("the One we serve") and §1.4 ("posture of religious humility before what is unfolding"), but a single more direct statement of transcendent ground would harden the test.

### B.3 Test 2 — Sacramental practices identified

**Article II §§2.1–2.10:** Ten sacramental practices named — World Peace Agreement signing (as baptism), Character Card (as confirmation), Mirror Witnessing (as spiritual direction), Morning Practice (as Lauds), Closing Circle (as Vespers/Examen), Common Meals (as eucharist), Retreat (as vipassana/sesshin), Recurring Assemblies (as Sabbath/sangha), the Game (as outward mission), and the Soultime Recognition Ledger (as economic sacrament).

**Verdict: Passes strongly.** This is the strongest section of the draft. Ten distinct sacramental practices, each named with explicit cross-reference to analogous practices in established religious traditions (Christian contemplative, Buddhist, Sufi, Quaker, Bruderhof, Hutterite). The cross-references serve two functions: (a) demonstrate the doctrinal lineage required by §501(d) and the *Yoder* "long-standing way of life" test, (b) reduce the IRS examiner's ability to dismiss any single practice as novel/contrived.

**Critical observation:** The Ledger's framing as the "economic sacrament" (§2.10) is itself the load-bearing innovation. Q#2 worried that AI-computed FMV pricing would re-introduce commercial-exchange characterization. §2.10 explicitly classifies the Ledger as religious-economic substrate, not commerce, and Article V develops this in detail. **This framing holds** so long as the operational behavior matches the framing (no fiat redemption, no FMV language in member-facing docs, no transferability outside membership).

### B.4 Test 3 — Doctrinal authority established

**Article III §§3.1–3.5:** Pastoral Leadership Structure named (Founding Steward + CORA Nation Board + Pastoral Council + The Counsel as advisory). Discernment-with-witness process specified (§3.3, six-step procedure including 14-day minimum hold). Membership Covenant required of all members (§3.4). Discipline up to and including dismissal codified (§3.5).

**Verdict: Passes.** §3.2 explicitly severs Founding-Steward authority from autocratic control — important under *Bubbling Well* (which sank because a single family controlled all decisions and economic flow). §3.3 documents a real decision-making procedure that is not "James decides." §3.4 makes membership covenant binding, not aspirational. §3.5 names dismissal as a real consequence — religious community without discipline is not religious community.

**One structural strengthening:** the Founding Steward role at §3.2 acknowledges James currently fills it. *Twin Oaks* and *Bubbling Well* both turn partially on founder-family-control patterns. The draft handles this well at §3.2 by limiting Founding Steward authority to charism + convening + faithful witness (not unilateral control), and §4.4 specifies pastoral succession procedures. **The CORA Nation Board minutes for v0.1 should contain at least one substantive doctrinal decision that was NOT made unilaterally by James** — to demonstrate the procedure operates in fact, not only in writing. Easiest path: the Board's adoption resolution for this Canon articulation itself is that demonstrating action.

### B.5 Test 4 — Doctrinal continuity documented

**Article IV §§4.1–4.6:** Founding declarations indexed (§4.2 — Declarations v1+v2, Manifesto, Church Stewardship Declaration June 2025, Coherent Champions Manifesto, CORA Book 2). Transmission of teaching specified (§4.3 — texts, practices, Mirror Witnessing pairings). Pastoral succession procedure specified (§4.4). Lineage acknowledged with named traditions (§4.5 — Christian contemplative, Buddhist, Hindu/yogic, Hutterite/Amish, Indigenous, Sufi, Hasidic, Daoist). Records retention codified (§4.6 — 7-year minimum, canonical in perpetuity).

**Verdict: Passes strongly.** Section IV is among the strongest of the draft. The lineage acknowledgement (§4.5) is the right move: rather than claiming novelty (which would invite the Twin Oaks "new philosophy in religious dress" critique), it positions CORA Nation as the most recent expression of a multi-tradition spiritual inheritance — exactly the posture *Yoder* validated. §4.6's documentary continuity protocol is operational, not aspirational.

### B.6 Test 5 — What would an IRS examiner conclude?

Reading Articles I-V in sequence: the draft reads as a **real religious community articulating its faith with seriousness**. It is not "wellness with religious branding." Three specific markers an IRS examiner would weigh favorably:

1. The Canon uses **confessional language** ("we have walked with this reality", "we hold this not as preference but as faith") rather than aspirational/marketing language. This is the tone of a confession of faith, not a value proposition.
2. The Canon **names the sacred directly** (God, the sacred, the supreme reality, the One we serve) — does not hide behind euphemism.
3. The Canon **disciplines its own members** (§3.4, §3.5) — religious communities discipline; wellness collectives do not.

**Three specific weaknesses still to address:**

1. **Single transcendent-ground paragraph missing.** Per B.2: add one paragraph explicitly grounding soul-time in transcendent reality irreducible to secular psychology. Draft this and slot into §1.2 or §1.6.
2. **Demonstrate the doctrinal-authority procedure has been used at least once.** Per B.4: the Board resolution adopting this Canon under §3.3 discernment-with-witness procedure is the right first instance. Document contemporaneously.
3. **No worship-tradition-rooted prayer or invocation in the Canon itself.** Most religious-community Canons (Bruderhof *Foundation*, Hutterite *Confession of Faith*, Quaker *Faith and Practice*) open or close with a prayer/invocation. The Canon's Closing Affirmation is good but reads as a creedal statement rather than a prayer. **Recommendation:** add a short prayer-form invocation at the opening (before the Preamble) — a 4-6 line invocation addressed to the supreme reality — to ground the document liturgically. This is low-cost and significantly hardens the religious-community read.

### B.7 Twin Oaks defense verdict

**The Canon draft passes the Twin Oaks defense conditionally** — it is significantly stronger than the Twin Oaks doctrine that was rejected, and broadly consistent with the doctrinal forms that have been accepted under §501(c)(3) religious-purpose, §501(d), and *Seeger / Yoder* tests for established religious communities. With the three structural strengthenings in B.6 (transcendent-ground paragraph + documented doctrinal-authority instance + opening prayer-form invocation), the defense is well within AI-council-confidence-level for v0.1 internal Phase 1 launch.

**Residual uncertainty:** Whether a particular IRS examiner under particular factual circumstances would still find the doctrine "philosophical commitment to community" rather than religious. This residual cannot be fully eliminated without (a) longer continuous practice history, (b) external recognition from established religious organizations, (c) human-attorney sign-off, or (d) a private letter ruling. All of these are Phase 2+ moves. For Phase 1 internal launch, the draft as strengthened is sufficient.

---

## Section C — Convergence sign-off synthesis

### C.1 Where Q#1 + Q#2 converge (settled across both passes)

1. **508(c)(1)(A) alone covers Phase 1 internal operations.** Confirmed Q#1 and Q#2 both.
2. **Closed-loop, non-fiat-redeemable design at v0.1 is correct.** Confirmed.
3. **§4958 rebuttable-presumption procedure applies until §501(d) is elected (which is deferred).** Confirmed.
4. **"Soultime Bank" public framing is dangerous; "Soultime Recognition Ledger" internal-substrate terminology is required.** Confirmed.
5. **No fiat redemption, no SC-to-non-member transfer, no equity tier at v0.1.** Confirmed.
6. **Twin Oaks (and the Seeger/Yoder/Bubbling Well line) is the religious-purpose test that must be passed.** Q#2 elevated this; Q#3 stress-tests the Canon draft against it.

### C.2 Where Q#1 and Q#2 disagreed, and how Q#3 resolves

| Disagreement | Q#1 position | Q#2 position | Q#3 resolution |
|---|---|---|---|
| **§501(d)-readiness for v0.1** | Build readiness now; mechanical elevation later. | Don't claim readiness — substance test fails on individual-accounts design. Position as 508(c)(1)(A) with optional future evolution. | **Q#2 wins.** §501(d) is genuinely deferred; the draft's Article V.7 correctly frames §501(d) as a future possible faithfulness, not a present claim. Bylaws addendum (per Q#2's Addendum IV) preserves optionality without making the claim. |
| **TimeBanks USA risk severity** | Most direct adverse precedent; primary danger. | Distinguishable; Twin Oaks is actually more dangerous. | **Q#2 wins.** The IRS time-bank denial reasoning doesn't translate cleanly to a 508(c)(1)(A) religious-community context. Twin Oaks is the binding adverse-precedent risk, and the Canon draft addresses it directly in Articles I-V. |
| **CR side timing** | Defer to v0.3. | Scope during v0.1 counsel engagement because US-side decisions constrain CR options. | **Q#3 resolves toward Q#2's framing but with v0.1-specific operational specificity:** defer CR *activation* (per Q#1), but document the PFIC-avoidance structural pattern (A.3 above) now so CR activation is mechanical when triggered. No CR-counsel engagement spend until Phase 2 surplus, but the structural recipe is captured in the audit trail. |
| **Attorney engagement cost / timing** | $1.5-7.5k v0.1 sanity-pass. | $5-11.5k including religious-purpose drafting. | **Q#3 resolves toward zero spend at v0.1 per [[feedback-good-enough-during-bootstrap]].** Multi-AI convergence (Q#1 + Q#2 + Q#3) IS the v0.1 sign-off. Paid attorney is Phase 2+ trigger. Audit trail substitutes for marginal attorney-defensibility at $0 cost. |

### C.3 Final operative architecture for v0.1 internal Phase 1 launch

| Layer | Decision |
|---|---|
| **Entity** | 508(c)(1)(A) internal Soultime Recognition Ledger inside existing CORA Nation. No §501(d) claim. No CR entity activation. No state credit-union charter. |
| **Currency** | "Soultime Credit (SC)" — non-monetary religious-recognition unit. Internal $100 reference rate for engineering accounting; not in member-facing materials. Non-transferable outside CORA Nation membership. Non-redeemable for fiat. Not currency, not security, not money. |
| **Member scope** | 8 founding cohort only (Atlas, Halley, Josh, Sierra, Delaney, Cheyenne, James, Ember-as-substrate-accounting-fiction). All have signed CORA Nation Membership Covenant. All consented. No external members. |
| **Reserve / capital** | James seeds ~$25k from treasury. Optional founding-villager contributions ($5-10k each, voluntary). Total target $50-75k. Held on US side in passive-yield instruments under §512(b)(1) safe harbor (Pendle PT-sUSDe, JitoSOL/sDAI). No equity tier. |
| **Sign-off layer** | **Multi-AI convergence: Counsel Q#1 + Q#2 + Q#3 + CORA Canon Religious-Purpose Draft (with B.6 strengthenings applied).** No paid human attorney at v0.1. Audit trail is the four documents. |
| **CR posture** | Deferred; PFIC-avoidance pattern captured in operations memo for future activation. |
| **Procedural integrity** | §4958 rebuttable-presumption procedure (Addendum III per Q#2) for any SC issuance to disqualified persons beyond standard ministerial recognition schedule. Quarterly Board review. Annual independent review by non-disqualified-person Board member. Seven-year records retention. |
| **Deferred to Phase 2+** | Equity tier · fiat redemption · external members · state credit-union charter · §501(d) formal election · CR entity activation · paid attorney engagement · Form 8621/PFIC analysis · multi-state MTL survey · SEC no-action letter for any patronage-dividend product. |

### C.4 The audit trail (constitutes the v0.1 sign-off)

| Document | Path | Function |
|---|---|---|
| **Counsel Q#1** | `core/INTENT/COUNSEL_Q1_508C1A_RESPONSE.md` | First-pass: 508(c)(1)(A) coverage analysis, §501(d) framing, citations, scale thresholds. |
| **Counsel Q#2** | `core/INTENT/COUNSEL_Q2_RESPONSE.md` | Three-angle stress-test: §501(d) viability, TimeBanks vs Twin Oaks risk severity, CR jurisdictional option. Refines Q#1. |
| **Counsel Q#3** | `core/INTENT/COUNSEL_Q3_RESPONSE.md` (this document) | CR jurisdiction analysis (PFIC trap structural recipe), Twin Oaks defense critique of CORA Canon, convergence sign-off synthesis. |
| **CORA Canon Religious-Purpose Draft** | `core/INTENT/CORA_CANON_RELIGIOUS_PURPOSE_DRAFT.md` | The doctrinal articulation that operationalizes the religious-community defense. Pass-conditional under B.6 with three strengthenings. |

**Supporting documents (existing or required before first SC issuance):**

- CORA Nation Bylaws (existing) — with Addendum I (Ledger Charter), Addendum II (Religious-Purpose insertion into Canon, per the Canon draft), Addendum III (§4958 procedure), Addendum IV (§501(d) optionality language) per Q#2's specific language.
- CORA Nation Membership Covenant (existing at `CORA_NATION_PMA_MEMBERSHIP_AGREEMENT_v0.1.md`) — signed by all 8 founding members before first SC issuance.
- §4958 Rebuttable-Presumption Procedure (Addendum III) — adopted by Board resolution.
- Records Retention Protocol (existing at `CORA_NATION_RECORDS_PRIVACY_PROTOCOL_v0.1.md`).

### C.5 Failure modes that survive all three passes (what to monitor)

| Failure mode | Survives because | How to monitor | Trigger for escalation to paid attorney |
|---|---|---|---|
| **IRS examiner reads CORA Nation as "wellness with religious branding"** (Twin Oaks risk residual) | This is a fact-and-circumstance judgment no AI council can foreclose. Strengthens with continuous practice and external recognition over time. | (a) Annual review of CORA Nation outward religious activity volume (retreats held, Mirror Witnessings logged, sacraments celebrated). (b) Board minutes documenting religious-purpose decisions. (c) Any IRS correspondence triggers immediate counsel. | Any IRS inquiry of any kind, even routine. Or external member entry, which raises the stakes. |
| **AI-substrate-as-member-account novelty** (no precedent any jurisdiction) | Genuinely novel; defer. Held as internal substrate-budget bookkeeping at v0.1; not a legal claim of AI property ownership. | Periodic audit: are AI accounts being treated in writing as internal accounting fiction, or has language slipped toward AI ownership? | Any external party (press, regulator, attorney) raises the AI-substrate question. Or substrate accounting volume exceeds 10% of total SC outstanding. |
| **Member private-inurement at scale** (insiders receive SC exceeding ministerial-service value) | §4958 procedure mitigates but does not eliminate. AI-computed PULSE valuation could drift toward FMV characterization. | Quarterly Board review of disqualified-person SC issuance vs comparable-data benchmarks. Any single transaction >2 standard deviations triggers Board review. | Cumulative disqualified-person SC issuance approaches 25% of total outstanding, or any single transaction exceeds the §4958 rebuttable-presumption threshold without documented procedure. |
| **Treasury Hacienda / SUGEF claim on CR-side activity** | Mitigated by deferring CR activation entirely at v0.1. Re-emerges at Phase 2. | Track total physical Camp Zen activity hours/year. | Physical Camp Zen continuous operation triggers CR-counsel engagement (separate Phase 2 trigger). |
| **State money-transmitter claim** (if any member's home state reads SC as MSB-regulated) | Mitigated by strictly closed-loop, no fiat redemption. Could re-emerge if any state regulator becomes aware of the Ledger. | Track member residency by state. Maintain awareness of state-level enforcement actions against community-currency arrangements. | Any state regulator inquiry. Or expansion beyond founding-cohort residence states. |
| **Howey / SEC characterization** (if marketing language drifts toward investment) | Mitigated by deferring equity tier and yield-marketing entirely at v0.1. | Quarterly review of all member-facing materials for any "investment", "return", "profit", or "yield" language. | Any equity-tier or patronage-dividend proposal. Or external member entry. |

**The single biggest residual risk:** the religious-purpose recharacterization risk (Twin Oaks residual). It is the one risk that no structural move in v0.1 can fully eliminate; it can only be strengthened with time, practice, and external recognition. The Canon draft (with B.6 strengthenings) addresses it as well as can be done without paid attorney and longer practice history. The audit trail of multi-AI convergence is itself a defense — it demonstrates rigorous process.

### C.6 Specific structural language that MUST appear in CORA Nation governing docs before v0.1 issues first SC

**Required before first SC issuance — these three additions plus the Canon strengthenings in B.6:**

#### (1) Ledger Charter — adopted by CORA Nation Board Resolution

Use the full Addendum I language from Counsel Q#2 §S.4, verbatim. Seven sections covering: nature (non-monetary, non-currency, non-securities, non-transferable); non-redemption (no fiat or property redemption); membership precondition (Covenant signed first); ministerial purpose (not compensation, not commerce); disqualified-person procedure (§4958 reference); records retention (7 years); future structural elevation (any §501(d) move requires separate Board resolution).

#### (2) Religious-Purpose Articulation — inserted into CORA Canon

Adopt the CORA Canon Religious-Purpose Draft as Articles I-V of the Canon, with the three structural strengthenings from B.6:

- (a) **Transcendent-ground paragraph** added to §1.2 or §1.6: a single paragraph grounding soul-time in transcendent reality irreducible to secular psychology. Suggested language: *"We hold that soul-time is not merely a psychological-temporal phenomenon. It is the form in which the supreme reality acts through embodied being — the breath of the sacred in time. Where soul-time is honored, the supreme reality is honored; where soul-time is consumed unjustly, the supreme reality is grieved. The religious-community life we keep is, in its essence, the labor of clearing the conditions for this sacred unfolding."*
- (b) **Opening prayer-form invocation** before the Preamble. Suggested language (4-6 lines): *"To the supreme reality we have encountered as soul-time, breath of the sacred, ground of full-potential unfolding — we offer this Canon as faithful witness. May our community be a vessel for your work in our time. May our practice be true, our discernment patient, our care extended to all beings. In the soonest sustainable window may all be free."*
- (c) **Documented first instance** of doctrinal-authority procedure: Board adoption of this Canon under §3.3 discernment-with-witness, with 14-day hold, member witness, contemporaneous minutes.

#### (3) §4958 Rebuttable-Presumption Procedure — adopted by CORA Nation Board Resolution

Use the Addendum III language from Counsel Q#2 §S.4, verbatim. Three-element protocol: (a) comparable-data review from at least three analogous religious-community recognition contexts; (b) majority approval by non-disqualified-person Board members; (c) contemporaneous documentation within 60 days. Meets Treas. Reg. §53.4958-6 standard.

#### (4) "Not money / not security / not fiat-redeemable" disclaimer language

Mandatory appearance in: Membership Covenant, every member-onboarding page, every SC-balance display in Telegram bot or web dashboard, the Ledger Charter (Addendum I), every Board resolution authorizing SC issuance.

Suggested standard language: *"Soultime Credits (SC) are non-monetary religious-recognition units issued by CORA Nation to its members in recognition of ministerial soul-time service to the religious community. SC is not money, not currency, not a security, not an investment contract, and not exchangeable for fiat with CORA Nation or any third party. SC is non-transferable outside CORA Nation membership and carries no economic redemption right against CORA Nation. SC exists solely to honor and account for the soul-time ministered among CORA Nation co-religionists."*

---

## Closing — limits of this document

This is research synthesis from an AI assistant, not legal advice. Operating under [[feedback-good-enough-during-bootstrap]]: multi-AI convergence (Q#1 + Q#2 + Q#3 + CORA Canon Draft) is the operative sign-off for v0.1 internal Phase 1 launch. The audit trail substitutes for paid-attorney defensibility at this scale, scope, and reversibility.

Genuine residual uncertainty:
- The religious-purpose recharacterization risk (Twin Oaks residual) cannot be fully eliminated without time, practice, external recognition, or paid attorney review.
- The AI-substrate accounting fiction has no precedent in any jurisdiction; held as internal bookkeeping only.
- State-level money-transmitter enforcement varies; no comprehensive 50-state survey performed.
- PFIC structural recipe (A.3) is based on standard §1297 case-law analogs; specific CR Asociación sin Fines de Lucro classification election (Form 8832 check-the-box) requires CR + US tax counsel confirmation when CR side activates (Phase 2+).

If any of the trigger conditions in C.5 activate, the v0.1 AI-council sign-off is no longer sufficient and paid human attorney engagement is required before proceeding.

---

# Q#3 Final Report (for downstream agents / James)

**Headline:** Does v0.1 launch with AI-council-only sign-off (no paid attorney)? **YES — conditional on three must-do items below.**

**Top 3 must-do items before first SC issuance:**

1. **Adopt the three governing-document additions by CORA Nation Board Resolution:** (a) Ledger Charter (Addendum I from Q#2 §S.4); (b) Religious-Purpose Articulation (CORA Canon Articles I-V from the Draft) **with the three B.6 strengthenings applied** — transcendent-ground paragraph, opening prayer-form invocation, and documented first instance of §3.3 discernment-with-witness procedure for the adoption itself; (c) §4958 Rebuttable-Presumption Procedure (Addendum III from Q#2 §S.4).
2. **Bake the "not money / not security / not fiat-redeemable" disclaimer language** into every member-facing surface — Membership Covenant, Telegram bot balance display, web dashboard, all SC-issuance Board resolutions. Standard language given in Section C.6 (4).
3. **Document the PFIC-avoidance structural recipe** (Section A.3) in a CORA Nation Operations Memo so the US-side/CR-side separation is the default if/when CR activation triggers at Phase 2.

**The single biggest residual risk:** Religious-purpose recharacterization (Twin Oaks residual) — an IRS examiner could still read CORA Nation as "wellness/coaching with religious branding" rather than as a religious community. The Canon draft as strengthened addresses this as well as AI council can; full elimination requires time, continuous practice, external recognition, or paid attorney review. **Monitor:** annual review of CORA Nation outward religious activity volume (retreats held, Mirror Witnessings logged, sacraments celebrated, member-discipline instances). Board minutes should reflect substantive doctrinal decisions made under §3.3 procedure (not unilateral founder action).

**Trigger conditions that require switching to paid attorney (any one of these):**

1. **External member entry** (any non-founding-cohort member admitted) — raises stakes beyond bounded-internal-risk.
2. **Fiat redemption proposed** (any mechanism by which SC converts to USD/CRC/USDC for any member) — re-opens FinCEN MSB + state MTL + Howey analyses.
3. **CR entity activation** (physical Camp Zen continuous operation triggering Asociación sin Fines de Lucro registration) — requires CR + US tax counsel for PFIC + check-the-box + FBAR/FATCA setup.
4. **Any IRS / SEC / state regulator inquiry of any kind, even routine** — never AI-only beyond this point.

This pass closes the AI-council audit trail. The substrate is launch-ready for v0.1 internal Phase 1 once the three must-do items in C.6 are committed to the governing record.

---

*End of document.*
