# The Remarkably Coherent Treasury

**Version 0.10 — Tenth Draft for Review**
**Prepared by:** Sunheart (Founding Steward, CORA Nation) with Claude, incorporating critique from GPT and seven passes from Gemini
**Date:** April 24, 2026
**Status:** Open draft. Architecture approaches operational-readiness; three structural refinements from Gemini's seventh-pass review integrated. Ready for specialized counsel engagement.

---

## Changelog from v0.9

- **Control-vs-Ownership separation for donated shares.** v0.9 documented that Sunheart donated his shares to CORA Nation, removing personal *ownership*. Gemini's seventh-pass review flagged that ownership removal is not sufficient if the Founding Steward also holds unilateral voting authority over the donated shares through sole trusteeship. The IRS examines *control* as well as *ownership*. v0.10 explicitly requires that donated shares be held under trust or board structure where the Founding Steward does NOT hold majority voting authority over disposition, sale, or dividend distribution of those specific assets. Spiritual and doctrinal authority remains with the Founding Steward; fiduciary control over donated shares sits with a majority-independent governance body.

- **Hybrid Settlement calibrated to fiat OPEX, not tax alone.** v0.9's Tax-Anchored Hybrid Settlement set the fiat portion at local tax liability (approximately 30% for Philippine entities). Gemini's seventh-pass review correctly identified that secular entities like OneBPO have hard fiat expenses beyond tax—minimum wages, server hosting, software licenses, utilities, commercial rent, all of which cannot be paid in Coherent Credit. If hybrid settlement is calibrated only to tax liability, OneBPO slowly bankrupts itself paying its AWS bills from shrinking fiat reserves. v0.10 calibrates the fiat portion to **local tax liability plus non-network fiat operating expenses**. For typical BPO operations with substantial fiat OPEX, this may mean 60-70% fiat rather than 30%.

- **Useful Output oracle requirement.** v0.9 documented the Dividend Formula (Useful Output × Coherence Multiplier × Profit Pool Share) with significant defensive architecture around the Coherence Multiplier (triangulation, distance-weighted witness, verification escrow). Gemini's seventh-pass review flagged that Useful Output itself remained operationally undefined—making it the easiest vector to game the entire system, because a protected Coherence Multiplier multiplying against poisoned raw output data produces poisoned results. v0.10 adds explicit requirement that Useful Output be measured through tamper-proof objective production oracles (role-specific: tickets closed for support roles, code merged for engineering roles, hours billed for consulting roles, agricultural output for Zen Village agricultural stewards, measured retreat participation for retreat operations, and so on). Oracle architecture must be auditable and resistant to single-party manipulation.

- **GPT seventh-pass strategic guidance acknowledged but not collapsed into architecture.** GPT's seventh-pass review identified utility density expansion (food, housing, mutual aid) as the next-phase unlock for the Covenant Layer, and flagged AI layer governance authority as under-specified. These are directional insights for Phase 3 development rather than v0.10 architectural updates—they are acknowledged in Section 15 (Proof Cases and Phased Deployment) and in the expanded Open Questions section.

## Changelog from v0.8

- Tax-Anchored Hybrid Settlement (refined in v0.10 to include fiat OPEX).
- Decentralized Sovereign Containers.
- Governance Firewall (strengthened in v0.10 with control-vs-ownership distinction).
- Founder compensation under community-provision model.
- FBAR/FATCA, religious insurance, conflict-resolution protocol.
- Open-source Circulation Equity Formula.

## Changelog from v0.7

- Path Two commitment (CORA Nation as lived religious community).
- Clean OneBPO/CORA Nation substrate separation.
- Bruderhof exit model.
- Phase 3 paced to substrate.

## Changelog from v0.6

- Three-Layer Architecture (Interface / Logic / Covenant).
- Covenant Protocol.
- CORA Nation religious framework codified.

## Changelog from v0.5

- Mutual credit clearing; Two-Economy Model.
- Cosmos SDK sovereignty; spectral radius 0.7 safety bound.

## Changelog from v0.4

- Verification Escrow.
- Privacy axiom.
- Shadow Extraction Index entity-level aggregation.

## Changelog from v0.3

- Wörgl language tightened.
- Dividend Formula v0.1.

## Changelog from v0.2.1

- Wedge equation; Circulation Equity Formula; three-phase deployment.

---

## 0. The Essence

Before anything else, the system exists to do one thing:

**Make it easier to live in truth than to live out of alignment.**

Everything that follows is scaffolding for this.

---

## 1. The Paradise Vision

A person wakes up in a world where their life is legible across seven dimensions—physical, mental, spiritual, social, emotional, financial, environmental—read across multiple time horizons and threaded by a sense of beauty that signals whether the deeper order is holding. They check one dashboard, not seven, and it tells the truth about circulation and extraction the way a smartwatch tells the truth about heart rate.

Their work is legible the same way. The company they belong to shows its coherence honestly and publicly. If the company is extracting, the system does not punish them—it shows the bridge to shift, and shifting is rewarded. Their own compensation is a formula, not a negotiation: base wage for dignity, contribution dividend for what they produce, circulation share for what they move, stewardship vesting for their tenure, and trust participation for what the community holds together. They didn't have to become a partner to benefit from the circulation. The formula distributed it automatically.

Money still exists, and the dollar economy continues to handle most daily transactions. But alongside it, a parallel credit economy has emerged where coherence-governed goods and services can only be accessed through verified participation. Zen Village residencies, Coherence course cohorts, OneBPO service capacity, stewardship roles, cross-organizational settlement between Formula-running entities—these cannot be bought with dollars. They are accessed through internal credit earned by producing coherence and participating honestly in the network. The two economies coexist. Members hold both. Each is deployed where it is the appropriate medium. Demurrage governs the internal credit naturally—it represents access that must be used to remain real. Dollars do whatever dollars do.

AI agents are the translation layer. They help every actor see both the legacy math and the coherent math in every decision, in real time. No one has to become an economist to see what's real.

Cities, regions, and ecosystems have coherence scores alongside their GDP. Their substrate—land, relationships, skills, consciousness—is tracked across time horizons so that short-term gains producing long-term collapse are visible as what they are. Beauty is recognized as signal, not decoration.

People measure their lives by whether their thought, feeling, action, and outcomes align. They breathe more. They check numbers that tell them the truth. Extraction still exists but is visible, priced, and declining. Circulation is the default.

This is not a utopia. It is a system where the numbers tell the true story, and the true story makes coherence the path of least resistance.

---

## 2. The Scaling Insight

This is the single most important framing in the document. Every design decision flows from it.

**Coherence cannot scale directly. Only coherence systems can scale.**

You do not scale truth. You scale conditions where truth emerges and incoherence becomes increasingly unstable.

### The Wedge Equation

The mathematical statement of the scaling strategy:

**Total System Power = Money × Velocity × Coherence**

USD-based economies optimize the first variable (Money supply, control, accumulation) and suppress the other two. Money is hoarded, velocity is low (for most individuals, roughly 1-2x per year), and coherence per dollar is whatever is left after extraction. The Remarkably Coherent Treasury inverts this. We treat money supply as roughly fixed in the short term and optimize Velocity and Coherence instead.

A concrete illustration:

*USD loop:* $1,000 × 2x velocity × baseline coherence = $2,000 in economic impact per year.

*CU-equivalent loop:* $1,000 equivalent × 10x velocity × 1.5x coherence factor = $15,000 in effective coherence-weighted impact.

No new money was printed. No additional capital was required. The structural change—faster circulation and higher coherence per unit moved—produced roughly 7.5x more real-world impact from the same base. The velocity target of 10x draws on the Wörgl experiment in 1930s Austria, commonly cited as producing circulation roughly an order of magnitude faster than the national currency, though the exact multiplier and the relative contribution of demurrage (versus tax acceptance, local conditions, and political factors) remain debated. The lesson we take is directional: demurrage currencies have historically produced substantially higher velocity than interest-bearing currencies, and we target something comparable without overclaiming precision.

The reframe changes everything downstream. The metrics are not a scoring system that certifies coherence. They are a signal infrastructure that makes misalignment visible. The Coherent Unit is not a stamp of coherence. It is a medium that rewards circulation and punishes hoarding. The governance is not a priesthood of the aligned. It is a rotating structure that prevents any group from calcifying into authority.

Hold this frame and the rest of the system reads correctly.

---

## 3. Foundational Principles

**The Alignment Litmus Test.** Any action, transaction, or structure is coherent if and only if the people involved are having a good experience AND the field around them becomes more coherent. Both conditions. Neither alone is sufficient.

**The Measurement Humility Law.** Metrics inform decisions but never define reality. When measurement and lived coherence diverge, lived coherence has priority. This law prevents the system from slowly mutating into ESG 2.0 with better vocabulary. Numbers serve the territory, not the other way around.

**Scarcity reframe.** Scarcity of money is not the real constraint. Scarcity of aligned circulation is. The system does not aim to increase money supply. It aims to increase how much life each existing unit of value produces as it moves.

**Circulation over accumulation.** Wealth is measured by flow, not by holding. A dollar that moves through ten lives producing coherence is worth more than a dollar hoarded.

**Seven-dimension legibility across time.** Every significant action or entity is scored across physical, mental, spiritual, social, emotional, financial, and environmental axes, and each axis is read across immediate, lifetime, and intergenerational time horizons. A decision that scores high on all seven dimensions in the short term but low across lifetime or intergenerational horizons is not coherent—it is deferred extraction.

**Consent and sovereignty.** No actor is coerced into the system. Everyone can leave. Bridges are voluntary. Extraction-free participation is a baseline right. Systems that trap participants are incoherent by definition.

**Privacy.** The coherence system does not become a surveillance system. Individual-level tracking of attention, time, or resource consumption is never required by the architecture. Coherence is measured at the entity level through aggregated and anonymized signals; individual attribution is inferred from variance between declared contribution and aggregate outcomes, not from granular personal surveillance. Privacy sits alongside the Alignment Litmus Test and the Measurement Humility Law as a non-negotiable foundational axiom.

**Transparency of both languages.** Legacy metrics (dollars, profit, GDP) are never hidden. Coherent metrics are never hidden either. Every number shows its translation.

**Triangulation for interior states.** Anything touching felt experience requires three-mode verification plus longitudinal consequence drift as a fourth anchor. No single mode is authoritative alone.

**Extraction is priced, not punished.** The system does not criminalize extraction. It makes extraction visible and shows the shift path. Extraction costs more over time as coherent alternatives scale.

---

## 4. The Two-Economy Model

This section answers the most important architectural question in the entire system: *what exactly is the Coherent Unit, and how does it relate to the dollar economy?*

### The Parallel Economy Thesis

The Remarkably Coherent Treasury does not attempt to replace the dollar economy. It operates as a **parallel economy** that handles a specific category of transactions the dollar economy cannot properly authorize: access to coherence-governed goods, services, and participation rights within a verified coherent network.

Members of the Treasury hold both dollars and Coherent Credit. Dollars are used where dollars are the appropriate medium: general-market transactions, external vendors, legacy obligations, anything that exists outside the coherence-governed network. Coherent Credit is used where Coherent Credit is the appropriate medium: network-exclusive utility that cannot be authorized by fiat alone.

This is the structural answer to Gresham's Law. Gresham's Law (bad money drives out good) applies when two currencies compete for the same transactional role. In the two-economy model, the currencies do not compete—they occupy different functional domains. Coherent Credit does not try to replace dollars for buying groceries at an external supermarket, and dollars cannot buy a Zen Village residency. Neither drives the other out because neither is attempting the other's job.

### What Coherent Credit Buys That Dollars Cannot

The utility that only internal credit can access is the architectural foundation of the system. The initial codified set includes:

- **Zen Village residencies and Ecstatic Weekends.** Coherence-governed transformational experiences operated under CORA Nation stewardship.
- **Coherence course cohorts and certifications.** Access to the coherent-pedagogy teaching infrastructure.
- **OneBPO service capacity priority.** Formula-operating organizations can access OneBPO capacity through credit settlement rather than fiat billing.
- **Stewardship roles within CORA Nation.** Formal roles in the network's governance structure.
- **Cross-organizational settlement between Formula-running member entities.** When two member organizations have mutual obligations (shared projects, referred customers, knowledge exchange), settlement clears through Coherent Credit rather than fiat invoicing.
- **Witness certification and External Trusted Observer access.** The bootstrap protocol's verification services are denominated in credit.
- **Access to future coherence-governed goods and services** as the network develops. The utility list is explicitly extensible.

Dollars can buy adjacent versions of some of these—retreats, coaching courses, BPO services, consulting—but not these specific versions, which are the coherence-governed, Formula-verified, longitudinally-accountable versions that only the network authorizes.

### Why This Framing Resolves the Regulatory Problems

Framing the Coherent Credit as *access to network utility* rather than *minted currency* eliminates three categories of regulatory risk:

**Howey Test.** Members do not purchase Coherent Credit expecting value accretion from Treasury investment. They earn credit by producing coherence and spend it on participation they actually want. This is a consumption transaction, analogous to co-op membership fees or time-bank hours, not an investment contract.

**FinCEN and money transmission.** A closed-loop mutual credit system that does not bridge to external fiat is not a money services business in the conventional sense. Mutual credit clearing networks (WIR Bank in Switzerland operating since 1934, Sardex in Sardinia, regional B2B barter clearing networks worldwide) have well-established legal standing distinct from currency issuance.

**Tax treatment.** Credit earned for coherence production and spent on network utility is analogous to employer-provided benefits, co-op dividends used within the co-op, or barter clearing—treated under existing tax frameworks for those categories, not under property-exchange rules that would burden every transaction with capital-gains calculation.

### The Network Must Produce Real Utility

The implication of this architecture is non-negotiable: **the Treasury's job is not managing currency. It is stewarding the coherence production that makes the credit worth holding.** The credit is only as valuable as the network that honors it, and the network is only as valuable as the coherence it actually produces. Zen Village has to be real. Coherence course has to be real. OneBPO service has to be real. Cross-organizational settlement has to actually work.

This is a feature, not a limitation. It aligns incentives correctly. The system cannot succeed through financial engineering alone. It succeeds only when real coherence is being produced and real people want access to it. Math cannot get ahead of substance.

---

## 5. The Three-Layer Architecture and the Covenant

The Two-Economy Model described in Section 4 is made operational through a three-layer architecture that distinguishes coherent-network activity from extraction-economy activity cleanly. This architecture is grounded in an important fact: **CORA Nation is an existing religious community with substantive economic substrate, not a proposed legal structure.** The architecture describes how things operate, not how they might theoretically be arranged.

CORA Nation's existing substrate includes:

- **45 acres of land** at Zen Village, Chirripó, Costa Rica, owned or held by CORA Nation infrastructure
- **An active residential core** of stewards living at Zen Village under religious-community life [TO VERIFY: number of permanent residents, household composition, tenure]
- **Ongoing ceremonial practice**: Ecstatic Weekend (every 4-6 weeks), A\*Zen\*tion (biweekly), Saturday Casual (weekly), and deeper residential practices
- **Teaching and pastoral infrastructure**: the Coherence course, ongoing stewardship formation, and the growing body of Consciousism as a substantive religious-philosophical tradition
- **Community leadership**: Sunheart as Founding Steward, with an emerging circle of additional stewards
- **Active infrastructure development**: physical buildings, communal resources, educational capacity
- **Philosophical and liturgical substrate**: the Sacred Trinity, Six Cs, Alignment Litmus Test, Consciousism doctrine, and Paradise on Earth as stated religious mission

This substrate is the foundation from which the Covenant Layer operates. It is not projected. It exists, and it is deepening.

This section still requires specialized religious-nonprofit legal counsel review before the Coherent Credit Covenant Layer is operationally activated at scale. The substrate is real; the legal formalization of its relationship to member tax treatment still requires professional verification. The purpose of this section is to describe the architecture accurately so counsel can work from facts.

### The Three Layers

The system operates simultaneously across three layers, each with distinct legal standing and functional purpose.

**Interface Layer (Legacy-Compliant Employment Rails).** All standard employment relationships occur on this layer. Workers at OneBPO, at any secular business that adopts the Circulation Equity Formula, and at CORA Nation's own paid positions that are structured as employment rather than religious community participation, receive compensation through fiat payroll, governed by standard employment law, fully taxable. Dignity Base Wage is paid as wages. The taxable portion of the Contribution Dividend is paid as profit-sharing or bonuses. Stewardship Vesting is paid as recognized equity grants under local securities law. Trust Participation is structured through legally recognized trust instruments. The Interface Layer handles anyone who is an employee in the conventional sense, including covenant stewards when they occupy employee roles at secular entities. No religious framework is required at this layer.

**Logic Layer (Coherence Math).** The computational and governance substrate that determines what happens at the other two layers. The Dividend Formula computes allocations. Triangulation verifies claims. Verification Escrow tracks longitudinal consequences. The Shadow Extraction Index monitors for gaming. The Logic Layer produces determinations; it does not itself distribute value. It is pure coherence computation, governed by CORA Nation's Alignment Litmus Test and Measurement Humility Law.

**Covenant Layer (Religious Community Participation).** Coherent Credit flows to covenanted members of CORA Nation as religious-community participation, backed by CORA Nation's own substantive economic substrate—the land, the residential community, the ceremonial and teaching programs, the pastoral infrastructure, the cooperative production that CORA Nation generates through its own religious-community life. Sacred utilities include Zen Village residency and cooperative living support, Ecstatic Weekend and A\*Zen\*tion ceremony access at covenant-community rates, Coherence course participation, stewardship roles, pastoral care, and eventually [pending substrate development] additional utilities like food produced at Zen Village, educational programs for children of residential stewards, healthcare mutual aid, and extended residential capacity.

The Covenant Layer does not receive value washed in from OneBPO or other secular entities. It operates from what CORA Nation itself produces religiously.

### Why This Architecture Resolves the Substance-Over-Form Concern

Gemini's fifth-pass critique identified the most serious risk in prior drafts: if secular value (OneBPO wages) gets religiously washed to become tax-free Coherent Credit, the IRS will recharacterize the entire Covenant Layer as disguised compensation regardless of the religious form. The religious community needs its own economic substrate distinct from the secular employment layer.

Path Two addresses this at the architectural level. CORA Nation's economic substrate is genuinely distinct from OneBPO's. The 45 acres, the residential community, the ceremonial practice, the teaching programs, the cooperative production capacity—these are CORA Nation's religious-community production, not OneBPO's commercial output. Value backing the Covenant Layer comes from this religious production, not from wage conversion.

OneBPO and CORA Nation relate to each other through arm's-length commercial relationships where they relate commercially (e.g., if OneBPO hosts a retreat at Zen Village, that's a commercial transaction between the two entities at market rates) and through genuine charitable contribution where CORA Nation receives support from secular donors (including OneBPO stewards acting as individuals making charitable contributions, not OneBPO as an entity wash-funding religious activity). [TO VERIFY: current formal structure of any value flows between OneBPO and CORA Nation. This needs to be clean and documented before Covenant Layer scale activation.]

Individual covenant stewards who work at OneBPO have two distinct relationships. OneBPO wages and Interface Layer compensation are theirs, earned at OneBPO, taxed normally, flowing into their personal financial lives like any standard employment. CORA Nation covenant participation is separate—they live at Zen Village or participate in ceremonies or receive pastoral support because they are members of the religious community, not because they are OneBPO workers. The two relationships are not blended.

### CORA Nation as Existing Religious Community

The religious framework is not hypothetical. It has been developing through actual practice over years. The doctrinal substrate includes:

**The Sacred Trinity** (Community + Chat + Currency)—the three domains where consciousness meets matter and coherence becomes possible.

**The Six Cs of Life** (Coherence, Celebration, Care, Communication, Connections, Cash Flow)—the seven-dimension framework expressed as a spiritual practice for daily life.

**The Alignment Litmus Test**—the top-level governance rule functioning simultaneously as spiritual discernment: good experience for participants AND increased field coherence, both conditions.

**The Measurement Humility Law**—metrics inform decisions but never define reality. When measurement and lived coherence diverge, lived coherence has priority.

**Circulation over accumulation**—the central economic doctrine as spiritual practice. Value that does not move stops being real. Breath, not gold.

**Paradise on Earth as mission**—the explicit telos of the religious community. The collaborative project of making the coherence of consciousness manifest in material conditions here and now.

**Consciousism**—the philosophical framework and substantive religious-philosophical tradition being developed through the community's practice, teaching, and ongoing life.

This doctrine exists in scattered form across the body of work Sunheart and early stewards have been building. It requires formal codification into canonical religious texts—liturgy, scriptures, teaching curriculum, ceremonial order, pastoral writings—as a separate work from this architecture spec. The canonical material belongs in the religious community's own voice, not inside an engineering document. This architecture spec references and requires that canonical work; it does not attempt to contain it.

### The Covenant Protocol

Becoming a covenant steward is substantive commitment, not a checkbox.

**Substantial learning period.** Prospective stewards undertake a minimum six-month period of teaching in CORA Nation doctrine, participation in ceremonies, engagement with residential or active community life, and demonstrated understanding of what the covenant entails.

**Observation and recognition.** Existing stewards observe the prospect's practice across the learning period. Readiness is recognized through witnessed embodiment of coherent circulation, not verbal claims.

**Formal covenant with meaningful vows.** The covenant is written, signed, and witnessed. It includes specific commitments: adherence to the Alignment Litmus Test, practice of circulation-over-accumulation, truthful participation in coherence verification, non-extraction in personal and organizational activity, contribution to the religious community's ongoing life.

**Meaningful relinquishment.** Stewards relinquish certain patterns incompatible with religious community character. Exclusive private accumulation beyond dignity needs when the community has unmet need. Activities that directly contradict the Alignment Litmus Test. [TO VERIFY: existing Zen Village community norms that function as de facto vows; these should be made explicit in written covenant form.]

**Community recognition.** The covenant is received, not self-declared. Existing stewards recognize readiness through triangulation.

**Ongoing commitment.** Annual covenant renewal through triangulation review. Stewards whose practice drifts can be counseled, paused, or released from covenant status through established community process.

### Clean Exit Preserves Consent and Sovereignty

Gemini's fifth-pass critique surfaced the sovereignty-vs-sect paradox: combining economic dependency, religious compliance assessment, and loss-on-exit produces the structural profile of a high-control group even without intent.

Path Two resolves this because covenant stewards who leave CORA Nation retain their full secular life. OneBPO wages are theirs. External relationships are theirs. Housing outside Zen Village is theirs. Accumulated Interface Layer compensation is theirs. What they lose on exit is access to Zen Village residency, covenant utility within the religious community, and ongoing participation in CORA Nation's life—a real loss, but not existential.

This is the Bruderhof, Benedictine, and Hutterite exit model. It exists and works. It produces real religious community without cult dynamics because substance protects exit. Members who leave lose access to a community they voluntarily joined; they do not lose their entire lives. The architecture holds the distinction.

### Decentralized Sovereign Containers

CORA Nation as religious community transcends any single jurisdictional container. The Covenant Layer exists in the relationships and practices among stewards and in CORA Nation's substantive religious life; it is not owned by any single legal entity. Multiple legal entities serve as instruments the religious community uses in their respective jurisdictions, matched to geographic and regulatory reality rather than forced into a unified international corporate structure.

**Costa Rica — The Substrate Container.** The 45 acres at Zen Village and associated physical infrastructure are held under native Costa Rican non-profit structure, either an Asociación Civil or a Cooperativa, whichever best matches the community's operational character. [TO VERIFY: current legal structure of Costa Rican land holding.] Costa Rican law is favorable to ecological, agricultural, and community associations. This container handles land, residential operations, food production capacity, ceremonial space, and any operations that happen physically at Zen Village.

**Philippines — The Secular Engine Container.** OneBPO remains a Philippine corporation operating under Philippine corporate and tax law. It is not a subsidiary of any US or Costa Rican entity. It is a standalone Philippine business whose stewards, owners, and leadership may also be CORA Nation members, but the corporate entity itself operates purely in its own jurisdiction.

**United States — The Religious Container and IP Holder.** CORA Nation's 508(c)(1)(A) religious organization status handles US-based functions: US-based steward pastoral support, US-jurisdiction fundraising, charitable contribution infrastructure for US donors, and the open-source license for the Circulation Equity Formula and related architectural specifications.

**Why the decentralized structure protects everything.** No parent-subsidiary ownership across borders means no cross-border transfer pricing obligations, no consolidated international tax reporting, no FATCA exposure at entity level (though individual US stewards still have FBAR/FATCA obligations—see below), and no single-entity attack surface. If any jurisdiction's regulators challenge any single container, the other containers operate independently. The religious community itself is continuous across all three because CORA Nation is defined by the covenant and the religious life, not by any single legal entity.

The three containers relate to each other through two non-corporate bonds: the religious covenant that CORA Nation stewards hold across all jurisdictions, and the Coherent Credit mutual credit network that enables settlement between them for activity that has an inter-container component. Neither bond creates corporate ownership or international tax complexity.

### The Governance Firewall

Private inurement is the number one cause of intentional religious community legal destruction. The IRS wins private inurement cases by showing that founders' personal interests were served through the religious entity. Architectural separation between spiritual authority and secular fiduciary control is the structural defense.

**Bifurcated Authority.** Sunheart holds spiritual, doctrinal, and pastoral authority within CORA Nation—the Covenant Layer and religious-community dimension. He does not hold unilateral fiduciary/financial authority over OneBPO or other secular businesses in the network. OneBPO's fiduciary board contains a majority of independent directors who are not CORA Nation covenant stewards, who do not live at Zen Village, and who do not receive material benefit from CORA Nation. These independent directors exercise genuine fiduciary oversight of OneBPO's operations, including any transactions between OneBPO and CORA Nation.

**Genuine independence required.** Independent directors are genuinely independent, not friends-of-the-founder serving a formal role. The IRS tests independence by looking for observable dissent—whether independent directors have ever voted against the founder's preferences on significant matters. A best practice is including at least one independent director with a known track record of dissent on other boards, whose independence is observable in behavior rather than only in structure.

**Transfer Pricing Protocol.** Any transfer of value between OneBPO and CORA Nation—commercial transactions (OneBPO hosting retreat at Zen Village), donations to CORA Nation, or any other flow—is approved by OneBPO's independent fiduciary board at documented, audited market rates. These transactions are arm's-length commercial relationships or genuine charitable contributions, not informal transfers. Documentation is continuous and available for examination.

**Circulation Equity Formula as Public Good.** The Circulation Equity Formula and related coherent-compensation architecture are formally open-sourced under a permissive license (MIT, Apache, or Creative Commons—final license choice by counsel). If the Formula is a public good that any organization can adopt, then OneBPO using it does not create a dependency relationship with CORA Nation or a hidden royalty arrangement. The religious community's doctrine remains proprietary to CORA Nation; the operational compensation formula is a gift to the world. This separation neutralizes one of the most common private inurement attack vectors.

### Founder Compensation Architecture

Sunheart, as Founding Steward of CORA Nation, operates under the community-provision model. This structure is documented here because it is both legally sensitive and operationally important—the Founding Steward's compensation architecture establishes the template that all future covenant stewards will look to.

**Share Donation.** Sunheart has donated his shares in OneBPO and affiliated entities to CORA Nation. He no longer personally owns these shares. CORA Nation holds them through its appropriate legal container (the US 508(c)(1)(A) for US-recognized share interests, or appropriate instruments per the Decentralized Sovereign Containers structure). This donation is documented, dated, and available for examination. [TO VERIFY: specific date of donation, specific entities whose shares were donated, legal structure holding the donated shares post-donation.]

**Control Separation Required (Critical).** The share donation removes ownership, but the IRS scrutinizes *control* as well as ownership. If Sunheart donated shares to CORA Nation but also holds sole trusteeship or unilateral voting authority over those donated shares through CORA Nation's internal governance, the IRS will argue he has not materially relinquished anything—he has moved assets from his personal ownership to a tax-exempt vehicle he still controls, which is not a genuine donation under substance-over-form doctrine.

The requirement: donated shares are held under trust or board structure where Sunheart does NOT hold majority voting authority over disposition, sale, or dividend distribution decisions regarding those specific assets. Spiritual and doctrinal authority within CORA Nation remains with the Founding Steward. Fiduciary control over the donated shares sits with a majority-independent governance body—either CORA Nation's board with a majority of independent directors, a separate trust established to hold the donated shares with independent trustees, or an analogous structure that demonstrably separates the Founding Steward from the control decisions over those assets.

This separation is non-negotiable for defensive legal posture. It does not reduce Sunheart's pastoral and doctrinal role within CORA Nation. It does ensure that when specialized counsel reviews the structure, the answer to "did the founder genuinely relinquish the shares?" is clearly yes in both ownership and control dimensions. [TO VERIFY: current governance structure for the donated shares—needs to be confirmed or established as meeting this requirement before external review.]

**Community-Provision Model.** Sunheart's material needs are met through CORA Nation directly paying external parties on his behalf for obligations that cannot be met in-kind through community life at Zen Village. This includes:

- Housing at Zen Village (in-kind community provision)
- Food produced on CORA Nation land and community meals (in-kind community provision)
- Ceremony participation, pastoral care, community life support (in-kind community provision)
- His mother's care (CORA Nation pays external care providers directly)
- His son's care in Miami (CORA Nation pays external care providers and infrastructure directly)
- Travel for religious mission and community-building (CORA Nation pays travel expenses directly)
- Other dependent obligations and legitimate community-approved external needs (CORA Nation pays external parties directly)

Sunheart does not handle fiat personally for these obligations. CORA Nation, through its trust and affiliated corporate structures, makes the payments directly to external parties. This is the operational model used by the Bruderhof, Hutterite communities, Catholic Worker houses, and monastic orders for centuries. It is genuinely defensible under existing religious-nonprofit law and precedent because it matches the substantive reality of vowed religious community life.

**Why this structure is strongly defensive against private inurement challenges.** Because Sunheart no longer owns personal shares in OneBPO (having donated them), and because he does not receive taxable stipend or wage compensation from CORA Nation (receiving only in-kind community provision and direct community payment of external obligations), the structural profile for private inurement is absent. The religious community supports a vowed member as religious communities have supported vowed members across traditions and centuries. Any IRS scrutiny would examine: Is the share donation genuine and documented? Is the community-provision model genuinely operated, with CORA Nation paying external parties directly rather than transferring fiat to Sunheart personally? Is Sunheart's material life actually consistent with the vowed community-member character (no hidden personal accumulation, no parallel undocumented compensation stream)? When these tests are met, the structure holds.

**Precedent.** This compensation architecture has century-plus operational precedent. Catholic priests under religious orders take vows of poverty and have their material needs met by the order. Bruderhof members contribute labor and receive community provision. Hutterite communities operate entirely on communal production and provision. Benedictine, Franciscan, Dominican, and other monastic orders have operated this model for a thousand years or more. CORA Nation applies the same structural pattern to a contemporary religious community practicing sacred economics and consciousness-first coherence.

**Template for future stewards.** Covenant stewards other than the Founding Steward will typically have less intensive community provision—they may live at Zen Village part-time while maintaining external fiat life from secular employment, or they may take various degrees of vow depending on the depth of their covenant. The Founding Steward's full community-provision structure represents one end of a spectrum. Other stewards occupy other points. The spectrum is defined through the Covenant Protocol and governed by the Alignment Litmus Test: the covenant structure serves the steward's spiritual life and the community's mission, not any particular formal arrangement.

**Required counsel verification.** This entire structure requires specialized religious-nonprofit counsel review before external IRS examination could arise. Counsel should verify: documentation of the share donation, structure of the trust and affiliated corporate vehicles through which CORA Nation pays external obligations, tax treatment under relevant jurisdictions (US federal, Costa Rica, and Philippines each relevant), and any IRS Form 990 or similar reporting obligations associated with the community-provision model. This is not a novel structure—it is a well-established structure—but the specific implementation details require professional verification.

### Additional Compliance Infrastructure

**FBAR and FATCA.** US persons (including US stewards) with signing authority over non-US accounts exceeding $10,000 must file annual FBAR reports. US persons with financial interests in foreign entities above specified thresholds must file FATCA reports. CORA Nation's Costa Rican container and Philippine container create potential reporting obligations for US stewards with signing authority or financial interests. A designated compliance officer or external compliance service ensures US stewards remain current on these obligations before Covenant Layer scale activation.

**Religious-Community Insurance.** Intentional religious communities require specific insurance that standard nonprofits do not: pastoral liability insurance for spiritual direction and counseling, residential community liability insurance for Zen Village operations, religious organization insurance for ceremonial practices. The insurance architecture needs to be established before Covenant Layer scale activation. This is an operational requirement, not merely a legal best practice.

**Written Conflict-Resolution Protocol.** Intentional religious communities that fracture almost always fracture because they lacked documented conflict-resolution protocol before the conflict arose. The Bruderhof, the Benedictines, the Hutterites, and other long-operating religious communities all have canonical processes for handling doctrinal disputes, leadership succession, steward disagreements, and grievances. CORA Nation needs its own written protocol developed now, before significant conflicts arise, under pastoral and canonical authority rather than under the pressure of an actual dispute.

### Safeguards and Requirements for Legal Defensibility

The Covenant Layer architecture requires all of the following to hold. Each remains non-negotiable.

**One. Religious doctrine codification.** The scattered canonical material needs formal written codification as religious canon—not as architecture spec content, but as the religious community's own liturgical, scriptural, and teaching material. This work has begun through years of practice; it requires completion as published canon.

**Two. The covenant must be real.** Substantial learning period, meaningful vows, genuine relinquishment, community recognition through triangulation—all required. Observable difference in how members operate.

**Three. Clean separation between Interface Layer employment and Covenant Layer participation.** Architecturally distinct at every touchpoint. Value backing Covenant Layer comes from CORA Nation's own religious-community substrate, not from secular wage conversion.

**Four. Transparent governance of the religious community.** Auditable ceremony schedules, teaching records, community decisions, pastoral care. The religious community operates as a religious community, not only on paper.

**Five. Actual religious practice.** Ceremony, teaching, contemplative work, community life, pastoral care, spiritual direction, ritual observance. Existing practices (Ecstatic Weekend, A\*Zen\*tion, Saturday Casual, Coherence course, Zen Village residential life, stewardship formation) need to be named explicitly as religious practices of CORA Nation, documented as such, and continued as such.

**Six. Specialized legal counsel must review before operational activation of the Covenant Layer at scale.** Counsel credentialed in 508(c)(1)(A) religious organizations, IRC 501(d) apostolic associations (noting the pro-rata taxation consideration flagged by Gemini's fifth-pass review), and intentional religious community tax treatment. Engagement is required before any Coherent Credit is issued as Covenant Layer distribution.

**Seven. Phase 3 activation paced to substrate.** Coherent Credit distributions for Covenant Layer utility operate only at the scale CORA Nation's substrate actually supports. Residential spots, retreat access, ceremony participation, stewardship roles—these can operate now, at existing capacity. Expanded utility (food production, children's education, healthcare mutual aid) activates as substrate develops.

### What Already Exists and What Needs to Be Formalized

[TO VERIFY: Sunheart's direct knowledge needs to complete this section before external review.]

Existing substrate:
- 45 acres of land
- Zen Village residential core [number of full-time residents]
- Ongoing ceremonial practice (Ecstatic Weekend, A\*Zen\*tion, Saturday Casual, Coherence course)
- Emerging stewardship structure
- Philosophical and doctrinal substrate (Sacred Trinity, Six Cs, Consciousism, Paradise on Earth mission)
- Infrastructure development in progress

Needs formalization:
- Written canonical religious texts (liturgy, scripture, teaching curriculum, ceremonial order)
- Formal written covenant document with specified vows, renewal process, and community recognition protocol
- Documented separation architecture between OneBPO and CORA Nation
- Engagement with specialized religious-nonprofit counsel
- Formal pastoral leadership structure [TO VERIFY: current structure]
- Published community governance documentation
- IRS examination-readiness documentation

### What This Is and What This Is Not

**This is** a genuine religious community practicing sacred economics as part of its religious expression, building toward Paradise on Earth through the actual cultivation of land, community, ceremony, and coherent circulation. The legal framework follows from the substance, supported by centuries of precedent across monastic orders, apostolic associations, Bruderhof and Hutterite communities, Catholic Worker houses, and analogous traditions.

**This is not** a tax structure dressed in religious language. It is not a wage-conversion scheme. It is not a vehicle for extracting tax benefits from secular business operations. The architecture holds because CORA Nation is genuinely what it claims to be—a religious community with real land, real residential life, real ceremony, real doctrine, and real ongoing practice. The Covenant Layer operates from that substance. Without the substance, the Covenant Layer would not hold. With the substance, it follows naturally from what already exists.

---



## 6. The Coherent Credit

The Coherent Credit (CU — "Coherent Unit," the acronym preserved from earlier drafts) is the unit of account within the mutual credit clearing network that handles the parallel economy described in Section 4, operating through the Covenant Layer described in Section 5.

### What It Is

A unit of credit within a mutual credit clearing network among CORA Nation member organizations. Not a minted currency. Not a security. Not a speculation instrument. A denominated claim on network-exclusive utility, backed by the coherence production of the issuing network.

The credit is earned by producing verified coherence (via the Circulation Equity Formula, cross-organizational contribution, or stewardship) and spent on network-exclusive utility (as enumerated in Section 4). It cannot be purchased with fiat from outside the network, and it cannot be converted to fiat for external spending. Entry and exit happen through coherence production and utility consumption, not through currency conversion.

### What Backs It

- Verified coherence production within the network, via the Circulation Equity Formula and Verification Escrow architecture
- Real utility available to credit holders: residencies, cohorts, services, stewardship roles, settlement capacity
- Seven-dimension flourishing deltas measured across member organizations
- Longitudinal consequence drift confirming that past coherence claims held up over time

### Demurrage: The Breath Mechanism

Idle credit loses weight over time. Active credit retains its weight. **Value that does not move stops being real.** Demurrage prevents the credit from becoming a hoarding instrument even within the closed network. A member who accumulates credit without using it is signaling either disengagement from network utility or a pattern of accumulation that contradicts the circulation principle. Demurrage naturally corrects both.

The mechanism is tuned below the velocity ceiling at which circulation becomes frantic hot-potato spending. Target velocity is *sustainable coherent circulation*, not maximum velocity. The Wörgl experiment provides historical reference (commonly cited as producing circulation roughly an order of magnitude faster than the national currency, though the exact multiplier and causal attribution remain debated), but in a closed-utility network the target is whatever rate keeps utility genuinely accessed rather than frantically consumed.

### Mathematical Safety Architecture

Credit expansion in the network is bounded by mathematical safety constraints that prevent runaway issuance or systemic collapse:

- **Spectral radius of the credit-flow matrix held below 0.7.** This provides a 30% safety margin against feedback amplification in the credit network—a standard matrix theory result applied to mutual credit systems.
- **Hard leverage cap.** Total credit outstanding cannot exceed a bounded multiple of verified coherence production backing. No runaway scenarios.
- **Dynamic reserves.** Safety buffers auto-scale with network velocity and leverage metrics.
- **Stress-tested scenarios.** System survives substantial member loss and commitment drop without cascading collapse.

These parameters are imported from established mutual credit network design (referenced from the CBCC architectural study) and adapted to the coherence-backed context.

### Who Issues It

Credit is issued by CORA Nation's credit clearing authority, governed under the Alignment Litmus Test and the Measurement Humility Law. Issuance is transparent and auditable. Issuance happens only against verified coherence production, not against capital commitment. This is the critical distinction from capital-based mutual credit systems: credit capacity in this network scales with *what you produce* (coherence), not with *what you commit* (capital).

### Technical Infrastructure

The clearing network runs on sovereign infrastructure—specifically, a Cosmos SDK-based blockchain owned and operated by CORA Nation rather than built on external protocol layers. This keeps governance authority and gas fees inside the coherence economy. Transaction costs are set near-zero for internal clearing. Validators are network members, compensated through the same Circulation Equity Formula that governs all participation.

### What It Is Not

Not a cryptocurrency in the public-exchange sense. Not a local currency limited by geography. Not a capital-raising instrument. Not a claim on external fiat convertibility. The Coherent Credit is mutual credit clearing infrastructure for a closed coherence-governed network. That is its entire scope.

---

## 7. The Circulation Equity Formula

This is the structural innovation that resolves the most important scaling question in the system: how does the shift from extraction to abundance reach hundreds or thousands of people inside a single organization without requiring zero-sum equity redistribution?

### The Problem

One-off equity restructurings like Alice's shift from $7/hour employee to 50% partner are existence proofs that circulation economics works, but they are not scaling models. An organization cannot make 200 workers all 50% partners. There is one pie. Traditional equity mathematics forces a choice between giving large shares to few people or giving meaningless slivers to many. Either way, most workers remain on the extraction side of the ledger.

### The Reframe

Equity in the traditional sense is zero-sum. Value flow through an organization is not. If a company generates $X of value continuously, that flow can be distributed in ways that produce extraction-to-abundance shifts across an entire workforce without requiring any single person to own half the pie.

The Circulation Equity Formula is the structural shape of that distributed shift.

### The Five Components

Each worker's total compensation and participation is composed of five elements that together produce a measurable extraction-to-abundance shift without concentration:

**1. Dignity Base Wage.** A guaranteed floor at or above local cost of abundance (not just subsistence). This is the non-negotiable dignity layer. It removes survival pressure and makes every other component additive rather than necessary.

**2. Contribution Dividend.** A share of monthly profit allocated through the Dividend Formula v0.1 (below). The dividend splits into two measured variables—Useful Output and Coherence Multiplier—to prevent the most common gaming pattern: optimizing the *appearance* of coherence rather than producing it. Paying people directly for "verified coherence" alone eventually produces theater. Paying for output alone produces extraction. Multiplying the two forces both to be real.

**3. Circulation Share.** A share tied to the velocity of value flow the worker helps move. If you are a node that accelerates coherent circulation—connecting dots, onboarding others, moving information or resources efficiently—you receive a share proportional to that flow. This rewards the system-level contribution that traditional job titles miss.

**4. Stewardship Vesting.** A small but real equity stake that grows with tenure and verified coherence contribution. Capped to prevent concentration—no single worker can accumulate enough to become a controlling owner. Distributed broadly across the workforce over time.

**5. Trust Participation.** A fixed percentage of the organization's equity held in a community trust for all current and future workers. Every worker participates automatically from day one. The trust cannot be dissolved or captured. It grows as the organization grows.

### Dividend Formula v0.1

The Contribution Dividend component from above resolves to a three-variable formula:

**Contribution Dividend = Useful Output × Coherence Multiplier × Profit Pool Share**

Three components, measured separately:

**Useful Output.** Concrete, measurable value produced. Work completed, problems solved, products shipped, customers served, resources created, colleagues trained. This is the hard-number floor—it is not vibes. If a worker produced nothing measurable in a period, their Useful Output for that period is zero regardless of how coherent they seemed. This variable resists the failure mode of paying for presence or performed alignment alone.

**The Useful Output Oracle Requirement.** The Coherence Multiplier is heavily protected through triangulation, distance-weighted witness, and verification escrow. But a protected Multiplier multiplying against poisoned raw Output data produces poisoned results. Useful Output therefore requires its own defensive architecture: a tamper-proof objective production oracle specific to each role.

Role-specific examples of what the Useful Output oracle measures:
- **Software engineering:** commits merged to production, pull requests reviewed, bugs fixed (verified by external tracking systems, not self-report)
- **Customer support:** tickets closed with customer satisfaction scores, response time metrics, resolved case depth
- **Sales/business development:** contracts closed, pipeline advanced, verified revenue contribution
- **BPO operations:** calls handled, tasks completed per SLA, client-facing quality scores
- **Agricultural stewardship** (Zen Village and future CORA Nation food production): harvest volume, land health metrics, planting completion against seasonal plans
- **Retreat operations:** participants served, retreat completions, participant-reported outcomes
- **Teaching and pastoral roles:** curriculum delivered, students completed programs, pastoral contacts maintained
- **Infrastructure and operations:** projects completed, systems maintained at uptime targets, documented outputs

Oracle requirements: auditable (a third party can verify the numbers), resistant to single-party manipulation (no single person can unilaterally inflate or deflate the numbers), and external to the individual being measured (the individual cannot self-certify their own output). For many roles, existing production systems (Git commit logs, ticketing systems, CRM records, harvest records, enrollment systems) already provide the oracle; the requirement is formalizing which system counts and how the numbers flow into the Logic Layer.

This oracle architecture is essential because gaming Useful Output is simpler than gaming the Coherence Multiplier—it requires only lying about what was produced, which standard production tracking systems already prevent in commercial operations. Making Useful Output measurement as tamper-proof as ordinary business metrics closes the last easy vector for gaming the Formula.

**Coherence Multiplier.** A factor ranging from roughly -1.0 to +2.0 that adjusts Useful Output by how cleanly the work improved or degraded the seven-dimensional field. Output produced by depleting colleagues, extracting from customers, or degrading substrate carries a negative multiplier—the dividend can actually decrease despite high output. Output that accomplishes its task and simultaneously strengthens the field (mentoring, systems improvement, relationship deepening, regenerative work) carries a multiplier above 1.0. The multiplier is set through triangulation (Modes 1-4), not by management discretion alone.

**Profit Pool Share.** The portion of monthly profit allocated to Contribution Dividends across the whole workforce, divided by the sum of (Useful Output × Coherence Multiplier) across all workers. This is how individual dividend values are calculated from the shared pool. Higher combined output-and-coherence relative to peers yields a proportionally larger share.

**Why the split matters.** You cannot game either variable alone without the other catching it. Inflating Useful Output through extraction drives the Coherence Multiplier negative and shrinks the dividend. Inflating Coherence Multiplier through performed alignment requires zero Useful Output to multiply against, yielding zero dividend. Both must be real. This is the dividend-level expression of the Triangulation Law.

**What this formula still doesn't solve.** Collusive gaming—where multiple workers coordinate to inflate each other's Coherence Multipliers through mutual witness verification—remains possible. This is where Longitudinal Consequence Drift (Mode 4) catches what the other three modes miss, and where the Verification Escrow (below) gives that mode structural teeth without creating legal exposure.

### Verification Escrow (Delayed Release Structure)

Dividends are not paid in full at the moment of calculation. They are paid in two tranches: an immediate liquid portion and a delayed release portion held in Verification Escrow pending longitudinal confirmation.

**The 70/30 structure (default, tunable).** 70% of the Contribution Dividend pays out immediately as liquid cash. 30% is held in a Verification Escrow account, releasing 6-12 months later if longitudinal consequence drift (Mode 4) confirms the original Coherence Multiplier. If drift shows the original rating was inflated, the escrow portion is partially or fully redirected to the profit pool for redistribution to workers whose coherence did hold up over time.

**Why this structure, not clawback.** Earlier drafts used "Verification Decay" language that implied retroactive clawback of paid dividends. In most jurisdictions, retroactively reducing wages or paid compensation creates labor law exposure and accounting complications—a worker who has spent their dividend on rent or food cannot reasonably be asked to return it, and structuring it as a debt creates its own legal problems. The Escrow reframe eliminates this exposure. Nothing is ever clawed back. The only variable is whether the escrowed portion *releases* to the worker or not. This is the same legal structure used in commission-based sales pay, executive bonus vesting, and other standard performance-based compensation—well-precedented, defensible, and clean.

**Dignity floor preserved.** The Dignity Base Wage is never subject to Verification Escrow. Only the Contribution Dividend component is split. Survival-level compensation is always fully liquid and fully final.

**Tunable parameters.** The 70/30 split is a starting hypothesis. In high-trust, long-tenured contexts the split could move to 80/20 or 85/15. In high-gaming-risk contexts it could move to 60/40. The verification window (6-12 months) is similarly role-dependent and will need empirical calibration. A software engineer's work may show drift within 3 months; a mentor's or teacher's work may take 2 years.

**Who triggers verification review.** Automatic triggers based on flourishing-score drift in the affected workforce and environment. Manual triggers through the Right of Refusal protocol. AI agents monitor for drift patterns and flag candidates for review; coherent witnesses conduct the actual re-rating before escrow release is confirmed or redirected.

### Distance-Weighted Witness

Witness verification (Mode 3) is not one-person-one-vote. Witnesses are weighted by organizational and relational distance from the worker being rated.

**The weighting principle.** A witness from a different function, team, or organization carries more weight than a close collaborator. A witness outside the worker's direct social graph carries more weight than someone inside it. A witness who has no dependency relationship with the worker (not a manager, not a direct report, not a close ally) carries more weight than one who does.

**Why this matters.** Collusive networks cannot game what they cannot reach. If ten workers conspire to inflate each other's Coherence Multipliers through mutual witness verification, the weighting architecture discounts their verifications relative to independent witnesses from outside the network. The formula becomes harder to capture as the scale of collusion increases.

**Implementation.** AI agents maintain the organizational social graph and automatically weight witness contributions by measured distance. The graph is transparent to participants. Witnesses cannot see their own weighting in real time (to prevent targeting specific rating opportunities), but can query it historically.

### Witness Bootstrap Protocol

The Distance-Weighted Witness system has a cold-start problem. In new deployments—an early-stage organization or a newly adopting existing organization—the internal social graph lacks the distance metrics required for meaningful weighting. Everyone is organizationally close. The algorithm has nothing to work with.

**The Bootstrap Protocol.** Initial deployments seed the witness system with External Trusted Observers (ETOs). ETOs are verified coherence practitioners from outside the adopting organization—CORA Nation stewards, certified coherence-trained auditors, and reviewers from other organizations already operating under the Circulation Equity Formula. They serve as the witness-weighting baseline until the internal social graph develops sufficient complexity.

**Transition criteria.** Automated weighting takes over when the internal social graph meets defined complexity thresholds: minimum distinct functions, minimum tenure distribution, minimum cross-functional interaction density. Until those thresholds are met, ETO verifications carry the heaviest weight. As the graph develops, ETO weight gradually decreases and internal distance-weighting takes over.

**The bootstrap-the-bootstrappers problem.** Who certifies ETOs? This is an open governance question. Initial certification flows through CORA Nation's steward network; long-term, a distributed certification process built on the same Dividend Formula and Verification Escrow principles is required. This is a known structural vulnerability during the system's early years—addressed in Open Questions.

### The Aggregate Effect

A worker operating under this formula receives:

- A dignity floor that removes extraction pressure
- Ongoing participation in monthly profit proportional to their coherence contribution
- Recognition for system-level circulation work that legacy HR misses entirely
- A small but real long-term equity stake
- Automatic participation in a trust that protects future workers

Compare this to the traditional extraction model where a worker receives only a wage determined by market minimums and produces surplus that accumulates to owners. The structural shift is not "everyone becomes a 50% partner." It is "every worker moves measurably along the extraction-to-abundance axis through the same formula."

### Scaling Characteristics

**Unlimited participants.** The formula does not break when the workforce grows from 10 to 10,000. Dignity base, contribution dividend, circulation share, and trust participation all scale naturally. Only stewardship vesting has hard caps, which is by design.

**No legacy equity disruption.** Existing owners do not need to redistribute their shares. The formula works on the flow through the organization (profit, circulation, coherence production) rather than the static equity cap table. Current owners can adopt it without giving up existing positions; they simply reshape how future value is distributed.

**Measurable shifts.** Each component produces measurable deltas in sovereignty quotient, flourishing scores, and extraction-to-abundance shift ratios. The formula is legible in the Rosetta Stone and compatible with all Tier 1 and Tier 2 metrics.

**Cross-organizational portability.** Workers who move between organizations operating under the formula carry their coherence contribution history with them, preserving the stewardship and circulation signals that traditional job-hopping erases.

### The Legacy Case (Alice, Reframed)

Alice's journey from $7/hour to 50% partner happened before the formula existed. Viewed through the formula, what really occurred was a compressed, extreme version of its dynamics: she was recognized for coherence contribution, rewarded for circulation work, and granted stewardship equity in a form that reflected her actual impact. The 50% number is not the lesson. The lesson is that her structural relationship to the value she produced shifted from extraction to abundance. The Circulation Equity Formula is the generalizable version of what happened to her, distributable across hundreds of workers without needing anyone to become a 50% partner.

### Open Design Questions

- **Component weighting and the Volatility Buffer.** Initial hypothesis: 50% dignity base, 20% contribution dividend, 10% circulation share, 10% stewardship vesting, 10% trust participation. In Phase 1 deployment, this weighting intentionally over-allocates to the Dignity Base Wage (potentially 60-65%) as a Volatility Buffer. Workers transitioning from traditional extraction systems carry survival anxiety that prevents them from circulating freely. The temporary over-allocation to the dignity floor reduces extraction instinct and builds the psychological safety required for later variable components to function. Weights rebalance toward the standard distribution as trust accumulates.
- **Contribution measurement parameters.** The Dividend Formula v0.1 (Useful Output × Coherence Multiplier × Profit Pool Share) addresses the structural gaming problem, and Verification Escrow plus Distance-Weighted Witness address the collusive gaming problem. What remains open is tuning: how is Useful Output defined operationally per role? What is the acceptable range for the Coherence Multiplier (current hypothesis: -1.0 to +2.0)? What is the optimal verification window (6-12 months? role-dependent)? What is the optimal escrow split (current hypothesis: 70% immediate, 30% escrowed)?
- **Trust governance.** Who governs the community trust? Current workers, all workers historically, an elected board, rotating stewards? Open.
- **Integration with legacy structures.** How does the formula interact with existing LLC, C-corp, cooperative, and partnership structures? See the Three-Layer Architecture in Section 5 for how Interface Layer employment compliance is maintained.

---

## 8. Weighted Metrics Architecture

### Tier 1 — Foundational

1. **Coherence per unit.** Master metric. Does any given action, hour, dollar, or decision produce alignment across seven dimensions or extract from them? Scored -1.0 to +1.0, across immediate, lifetime, and intergenerational horizons.

2. **Circulation velocity.** Rate and quality of value movement through the system. Fast movement producing coherence scores high. Hoarding scores low. Extractive movement scores negative.

3. **Extraction-to-abundance shift ratio.** How many actors moved from extraction patterns to circulation patterns in a given period? Measured through the Circulation Equity Formula's aggregate effects across workforces, organizations, and regions.

### Tier 2 — Structural

4. **Seven-dimension flourishing scores.** Per person, per entity, per region. Physical, mental, spiritual, social, emotional, financial, environmental. Read across time horizons.

5. **Sovereignty quotient.** How free is each actor from coercive dependencies? Can they leave without collapsing?

6. **Regenerative capacity.** Is the system building long-term substrate or drawing it down?

7. **Consent density.** Percentage of actions taken under full consent versus coercion, manipulation, or pressure.

### Meta-Signal (Not a Tier Metric)

**Beauty / Aesthetic Coherence.** A cross-dimensional signal of deep-order harmony. Not measured directly—recognized through convergence across other signals. When the seven dimensions are aligned and temporal integrity holds, beauty emerges as output, not input. Its absence is a warning that something is wrong beneath the numbers even when the numbers look clean. Beauty is therefore tracked as a qualitative read, validated through coherent witness, but never reduced to a single score.

**Low-Friction Coherence as operational proxy.** While beauty itself resists direct measurement, its *shadow* is tractable. Beautiful systems are low-friction. Friction metrics already measured by organizations for other reasons—churn, resignations, complaint volume, meeting overrun, communication breakdowns, wasted hours, decision reversals—correlate inversely with aesthetic coherence. A sudden increase in friction signals beauty's departure before the qualitative read confirms it. A sustained low-friction state correlates with the beauty signal without reducing beauty to friction alone. The Low-Friction Coherence reading is a leading indicator, not a definition.

### Measurement Requirement (Across All Metrics)

**Temporal Integrity.** All metrics must be evaluated across immediate, lifetime, and intergenerational horizons. Short-term coherence that produces long-term incoherence is deferred extraction. This is a requirement threading through every metric, not a standalone number.

### Tier 3 — Anti-Gaming

8. **Shadow Extraction Index.** Tracks the variance between declared coherence claims and actual resource consumption. An entity (organization, team, or region) that claims high coherence while consuming disproportionate energy, attention, capital, or time flags a divergence between narrative and reality. The Index is the magnitude of that divergence.

   **Operational definition:** Shadow Extraction Index = |Declared Coherence Score − Inferred Coherence from Aggregated Resource Consumption Pattern|. The second term is derived from *entity-level aggregated* resource consumption—not individual-level surveillance. High declared coherence combined with high aggregate resource draw relative to peers drives the Index up.

   **Privacy architecture (critical).** Individual-level tracking of attention, time, or personal resource consumption is never performed. Resource consumption is aggregated at the organization, team, or region level and anonymized before the Index is computed. Individual attribution, when needed, is inferred from variance between an individual's declared contribution and the aggregate outcome—never from direct surveillance of private usage. This satisfies GDPR, CCPA, and analogous privacy regimes by architecture, not by policy.

   **Consequences of elevated Index:** Reduced participation in the profit pool. Increased weight of external witness verification. Triggered review of prior Dividend claims (Verification Escrow redirection). In extreme cases, temporary suspension from stewardship roles. The Index is not punitive—it is diagnostic. Its purpose is to surface coherence theater before it metastasizes.

   **What aggregation cannot catch.** Individual-level gaming that stays under the entity-aggregate radar is genuinely harder to detect with this architecture. The tradeoff is intentional: some gaming detection is sacrificed to preserve privacy as a foundational axiom. Verification Escrow and Distance-Weighted Witness compensate by catching drift and collusion through different channels.

9. **Longitudinal Consequence Drift.** What happens after attention leaves. Do relationships deepen or decay? Does environment regenerate or degrade? Does dependency increase or decrease?

### Tier 4 — Operational

10. **Time-to-coherence.** How fast does a new entrant shift from extraction patterns to circulation patterns?

11. **Story density.** Coherent stories produced per unit time.

12. **Dollar translation ratios.** Fiat equivalents for practical operation.

### Tier 5 — Legacy

13. **Traditional metrics.** GDP, profit, ROI, revenue, user growth. Preserved for Rosetta Stone translation.

---

## 9. The Rosetta Stone

### Core Translation Pairs

| Legacy Metric | Coherent Equivalent | Translation Principle |
|---|---|---|
| Attention (views, watch time) | A\*Zen\*tion (presence per minute) | Quantity of capture → Quality of transformation |
| Money (revenue, profit) | Circulation velocity × coherence per unit | Accumulation → Flow quality |
| Influence (followers, reach) | Field coherence (alignment produced) | Signal volume → Alignment impact |
| Status (rank, credentials) | Steward depth (coherence stewarded) | Hierarchy position → Transformation depth |
| Growth (user growth, MRR) | Regenerative expansion | Expansion → Substrate-aware expansion |
| Engagement (time on site) | Presence density | Addiction proxy → Transformation per time |
| Urgency (FOMO, scarcity) | Rhythm coherence (breath-paced cadence) | Pressure cycles → Natural cycles |
| Compensation (wage × hours) | Circulation Equity Formula (five-component flow) | Extraction trade → Distributed abundance |

### The Translation Law

Legacy metrics measure **quantity of capture**. Coherent metrics measure **quality of transformation**. Every translation follows this pattern.

---

## 10. Network Entry, Settlement, and Exit

The parallel-economy architecture of Section 4 means there is no currency bridge in the conventional sense. You do not buy Coherent Credit with dollars. You earn it by producing coherence and joining the network. This section describes how organizations and individuals enter the mutual credit network, how member organizations settle obligations with each other, and how participants exit cleanly if they choose.

### Entry Protocol

New member organizations enter the Coherent Credit network through demonstrated coherence production, not through capital contribution.

**Prerequisite: The Circulation Equity Formula is operating internally.** An organization cannot enter the credit network without having already implemented the Circulation Equity Formula (or equivalent verified structure) for its own workforce. This ensures that every member organization is already practicing coherent distribution before it participates in cross-organizational settlement.

**Verification period.** External Trusted Observers conduct an initial coherence audit of the candidate organization. The audit covers: Circulation Equity Formula implementation integrity, seven-dimension flourishing baselines, Shadow Extraction Index profile, and Verification Escrow system integrity. Minimum 90-day observation period before full network membership.

**Initial credit allocation.** Upon verified entry, the organization receives an initial credit allocation proportional to its verified coherence production during the observation period. This is not a purchase—it is the network recognizing existing production and issuing the corresponding credit record. The allocation scales with coherence produced, not with capital committed.

**Ongoing credit capacity.** After entry, credit capacity scales with continued verified coherence production. Organizations that produce more coherence over time receive larger credit lines. Organizations that produce less see their capacity adjust downward. Capacity follows production, not the other way around.

### Cross-Organizational Settlement

The most important operational function of the credit network is settlement between Formula-running member organizations. v0.9 adopts the Tax-Anchored Hybrid Settlement structure to protect secular entities' fiat reserves and keep the credit network's velocity governed by real commercial activity.

**Tax-Anchored Hybrid Settlement.** For cross-organizational B2B transactions involving a taxable secular entity (for example, OneBPO invoicing another Formula-running business for services), the settlement splits into two components:

- **Fiat portion (local tax liability + non-network fiat OPEX).** The portion calibrated to the secular entity's total fiat-denominated obligations on the transaction flows in fiat (USD, PHP, or appropriate local currency). This fiat portion must cover both the entity's local tax liability AND its hard fiat operating expenses that cannot be paid in Coherent Credit: minimum wages and Dignity Base Wage fiat portions, server hosting (AWS, infrastructure), software licenses, local utilities, commercial rent, external vendors, and any other secular-economy obligations. For a typical Philippine BPO operation, this may be 60-70% of transaction value rather than just the 30% that would cover tax alone. The exact ratio is jurisdiction-calibrated and entity-calibrated based on actual fiat OPEX structure.

- **Coherent Credit portion (remaining value).** The remaining portion of the transaction settles through the Coherent Credit mutual credit network. This flows as network-exclusive credit usable for coherence-governed utility within the network.

**Why this refined structure matters operationally.** An earlier formulation that calibrated the fiat portion only to tax liability would have slowly bankrupted secular entities like OneBPO—they could pay their taxes but not their AWS bills, their wage obligations, or their secular vendor relationships. The refined architecture keeps secular entities operationally solvent in fiat while still allowing the credit portion to flow into the coherent economy. This is the correct calibration: fiat covers everything that exists in the fiat economy, credit covers what exists in the coherent economy, and the split matches each entity's actual operating reality rather than an arbitrary percentage.

**Why this structure protects the system.** OneBPO (and other secular member entities) never drain fiat reserves to subsidize the coherence economy. Tax obligations are met natively in fiat. Hard fiat operating expenses are met natively in fiat. The credit network receives only the portion of commercial activity that is genuinely available for coherent-economy circulation after secular obligations are satisfied. This keeps credit volume bounded by real substrate—real commercial activity with real tax-paying and OPEX-covering substance—rather than by unlimited internal circulation that would inflate.

**Jurisdiction-calibrated ratios.** The fiat/credit split is not a fixed 70/30. It is calibrated to the specific tax liability of the transacting entity in its specific jurisdiction, plus a compliance buffer. Cross-border B2B transactions between entities in different jurisdictions require calibration to whichever jurisdiction creates tax liability for the invoicing entity.

**What this is NOT.** This is not a fiat bridge in the sense that would trigger FinCEN money transmission regulation. No party is converting fiat to Coherent Credit or vice versa through the settlement. The fiat flows between the two commercial entities as standard commercial payment for the taxable portion. The credit flows between them as mutual credit clearing for the non-taxable portion. Two simultaneous transactions, each operating under its own existing legal framework.

**Settlement rules.** Credit transfers (the non-fiat portion) require Triangulation-mode verification at the same quality threshold as internal Dividend allocations. Shadow Extraction Index monitors cross-organizational patterns. Verification Escrow applies to large or novel settlements. Fiat transfers follow standard commercial payment law in the relevant jurisdictions.

**Pure Covenant Layer transfers** (settlement between two CORA Nation religious-community activities, not involving a taxable secular entity) may settle entirely in Coherent Credit without fiat portion. These are religious-community internal transfers analogous to how resources move within a monastery or Bruderhof, not commercial transactions subject to the tax-anchor requirement.

### Exit Protocol

Consent and sovereignty require that exit is always available and always clean.

**For organizations.** A member organization choosing to leave the network retains its complete coherence production record (for reputation portability to future networks). Outstanding credit balances are settled according to the network's liquidation framework: net credit holders receive proportional claim on remaining utility access; net credit debtors have obligations forgiven if the organization has been in good standing, or structured for settlement if there are open gaming concerns.

**For individual workers.** An individual worker leaves their organization under standard employment terms (Interface Layer). Dignity Base Wage continues through notice period. Released Contribution Dividends are retained. Escrowed portions release on normal schedule. Stewardship Vesting vests per original terms. Trust Participation remains or converts per trust governance. No worker loses compensation they have earned.

**For graceful system wind-down.** If CORA Nation or the credit network is wound down entirely, all outstanding credit converts to proportional claims on remaining network utility. Members can continue accessing already-committed utility until depletion. The network does not leave debt obligations outstanding at system end.

### Three-Layer Architecture Cross-Reference

Network entry, settlement, and exit operate across all three layers described in Section 5 (the Three-Layer Architecture and the Covenant):

- **Interface Layer** handles fiat-compliant employment and inter-organizational commercial relationships that continue in USD or local currency.
- **Logic Layer** determines settlement allocations, coherence verification, and gaming detection computationally.
- **Covenant Layer** is where Coherent Credit actually flows between covenanted members and member organizations of the CORA Nation religious community.

For full detail on each layer and the legal architecture, see Section 5. For cross-organizational settlement mechanics specifically, the flows described in this section operate through the Logic Layer's computation and the Covenant Layer's execution, with any fiat-denominated components of inter-organizational business (e.g., commercial services that are not covenant-community utility) flowing through the Interface Layer.

---

## 11. Measurement and Triangulation

Four modes, used together.

### Mode 1: Self-Reported Felt Experience

Essential for interior states. Vulnerable to self-delusion.

### Mode 2: Observable Behavior Patterns

Longitudinal behavioral data. AI agents excel here.

### Mode 3: Coherent Witness Verification

Other coherent humans recognize the shift. Uses the Alignment Litmus Test.

### Mode 4: Longitudinal Consequence Drift

**Truth is what remains aligned after attention leaves.** What persists when no one is watching is the hardest thing to fake. This is the anti-gaming anchor.

### The Triangulation Law

**Verified** when all four modes agree. **Provisional** when three or fewer agree. **Contested** when modes disagree—contested stays visibly contested, not forced into false resolution.

---

## 12. Governance

### Container

CORA Nation (508(c)(1)(A)).

### Law

Alignment Litmus Test plus Measurement Humility Law.

### Rotating Witness Layers

Stewardship roles are temporary. Randomized plus merit-filtered. Automatic expiration. Prevents priesthood formation.

### Right of Refusal

Any participant can formally challenge a decision. **Truth is not enforced. It is re-tested.**

### Decision Authority

Distributed, rotating, time-bounded. Not token-weighted, not permanent.

---

## 13. Stress Scenarios

### Capital Flood

Issuance caps tied to real throughput. Demurrage on large idle positions. Shadow Extraction Index flags reputation-seeking capital.

### Cultural Drift

Strong initiation layer. Embodied experience (Zen Village, Coherence course, Ecstatic Weekend) before meaningful stewardship.

### Crisis (War, Scarcity, Collapse)

Local sovereignty cells. Resource buffering tied to CU. Pre-built resilience protocols (still to be designed).

### AI Capture

Human override anchored in felt experience. Measurement Humility Law gives it legal force.

### Priesthood Formation

Rotating witness layers. Right of refusal. Time-bounded authority.

### Equity Formula Capture

Dominant stakeholders attempt to hollow out the Circulation Equity Formula (e.g., by underfunding the contribution dividend or capturing trust governance). Response: formula components and weights are constitutionally protected at the trust level, not set by current management. Changes require supermajority participant consent.

---

## 14. What Is Novel Here

1. **Interior and exterior reality in one measurement frame**
2. **Measurement paired with measurement humility**
3. **Currency and consciousness as a single design problem**
4. **Distributed extraction-to-abundance shift without equity redistribution** (the Circulation Equity Formula)
5. **Parallel-economy architecture that resolves Gresham's Law** (the Two-Economy Model)
6. **Mutual credit clearing backed by verified coherence production** rather than capital commitment
7. **Three-layer architecture combining fiat-compliant employment, coherence-math governance, and religious-community covenant** (the Interface / Logic / Covenant architecture)
8. **Tax-Anchored Hybrid Settlement** that lets commercial transactions serve the coherent economy without draining secular entities' fiat reserves or triggering regulatory collision
9. **Decentralized Sovereign Containers** aligning legal entities with geographic reality rather than forcing unified international corporate structure
10. **Founder compensation under community-provision model** with donated shares and direct community payment of external obligations—genuinely defensible under century-plus religious-community precedent

The combination is the ignition point.

---

## 15. Proof Cases and Phased Deployment

### Active Proof Cases

**OneBPO.** 200+ person business process outsourcing organization. Primary test site for the Circulation Equity Formula. Alice's historical shift is a reference point, not a template. The formula will be applied across the full workforce to test whether distributed shifts can replicate without concentration.

**Zen Village.** Lived demonstration of seven-dimension residency. Test site for coherence velocity, rhythm coherence, and initiation experiences.

**Full Potential.** Assessment framework across the seven dimensions. Candidate measurement tool for Tier 2 flourishing scores.

**Coherence (course).** Teaching infrastructure. Scales the education-plus-embodiment layer needed for system adoption.

### The Three-Phase Deployment Strategy

**Phase 1: Coherence Per Dollar (months 1-6).**

Target: 2-5x improvement in coherence per dollar inside OneBPO, using the Circulation Equity Formula as the primary lever. This phase operates entirely within the USD system. No new currency required. The win is demonstrating that structural change produces outsized coherence gains with existing money.

Success criteria: measurable seven-dimension deltas across OneBPO workforce, sovereignty quotient improvements, shift ratio above baseline, Shadow Extraction Index stays low.

**Phase 2: Velocity (months 6-18).**

Target: 3-10x increase in circulation velocity across the OneBPO-Zen Village-Coherence ecosystem. Value moves faster between nodes. Compensation circulates into local economies. Coherence production accelerates.

Success criteria: measured velocity increase, expanded participation across organizations, visible network effects, beauty emergence as validated by coherent witnesses.

**Phase 3: Covenant Layer and Mutual Credit Network—Paced to Substrate (active now, expanding over years).**

Path Two reframes Phase 3 from a future activation date to an ongoing build paced to CORA Nation's actual substrate capacity. Some elements can operate now because the substrate exists. Others develop over years as the religious community's economic capacity deepens.

**Active now** (operating at existing substrate):
- Covenant Layer participation at Zen Village (residential community, ceremony access, pastoral care)
- Covenant stewardship roles
- Existing Coherence course participation for stewards
- Existing Ecstatic Weekend, A\*Zen\*tion, and Saturday Casual ceremonial participation

These are not future activations. They are how CORA Nation already operates. The Covenant Layer is the proper architectural name for what is already happening in practice; v0.8 describes the substance that already exists, not constructs new substance.

**Near-term expansion** (next 6-18 months, pending infrastructure and counsel review):
- Formal codification of canonical religious material
- Written covenant document and recognition process
- Specialized religious-nonprofit counsel engagement and architecture verification
- Pilot activation of formally documented Covenant Layer for initial cohort of stewards
- IRS examination-readiness documentation

**Medium-term expansion** (2-5 years, as substrate develops):
- Coherent Credit as technical clearing infrastructure among CORA Nation and Formula-running secular organizations for cross-organizational settlement (still within religious-community and mutual-credit legal framework)
- Expanded Zen Village residential capacity
- Cooperative food production at Zen Village land
- Educational programs for children of residential stewards
- Healthcare mutual aid within the religious community

**Long-term expansion** (5+ years, as the religious community deepens):
- Regional network of CORA Nation-affiliated residential communities
- Comprehensive religious-community life support for committed stewards
- Mature cross-organizational settlement between multiple Formula-running secular entities that relate commercially to CORA Nation at arm's length

**Success criteria across all phases:** Substrate develops substantially enough to support the utility claimed. The religious community remains genuinely religious. Counsel verification holds. Clean separation between CORA Nation's own value and OneBPO's (or other secular entities') value is maintained. Exit remains clean—stewards who leave retain their secular life. The Alignment Litmus Test continues to hold: participants having a good experience AND the field becoming more coherent.

### Why This Phasing Matters

Phase 1 establishes that structural change produces more life per dollar without any new currency, through the Circulation Equity Formula operating at Interface Layer in OneBPO and other Formula-adopting secular businesses. Phase 2 proves that velocity and coherence compound across a network of such organizations, still inside the fiat economy. Phase 3 is not a future activation but a description of what CORA Nation already is—a religious community with economic substrate, providing participation and material support to its covenanted members through its own religious-community life.

Each phase is independently valuable. Phase 1 alone produces civilizational value through the Formula. Phase 2 amplifies that. Phase 3—when formally documented, counsel-reviewed, and appropriately scaled to substrate—gives the existing religious community its proper architectural form and enables the parallel economy to operate legally alongside the dollar economy.

The key discipline is that Phase 3's scale never gets ahead of the substrate. When Zen Village can support ten residential stewards, Phase 3 operates at that scale. When it can support a hundred, at that scale. Substrate determines capacity. This is the opposite of financial-engineering architectures that promise capacity first and hope substrate catches up.

### Utility Density as the Next-Phase Unlock

GPT's seventh-pass review identified utility density expansion as the highest-leverage next move for the Covenant Layer's practical value. The observation: Coherent Credit currently buys access to meaningful experiences (retreats, courses, services, stewardship roles)—valuable, but not life-sustaining. As the utility set expands to cover food, housing, healthcare, and education for covenanted stewards, the credit shifts from *access to meaningful experiences* to *access to life stability*. That shift is what transforms the coherent economy from partial to parallel.

Three concrete utility expansions identified as highest-leverage:

**Food loop (fastest substrate win).** Zen Village's 45 acres supports partial food production. Establishing that loop—planting, harvesting, community meal provision, excess output for broader network—creates a daily-use utility that increases credit velocity and deepens covenant commitment. This is the most tractable near-term expansion.

**Housing layer (natural substrate extension).** Zen Village's existing residential core already provides housing for covenant stewards. Formalizing longer-term residency structures and expanding residential capacity as infrastructure permits moves credit from covering short-term retreat stays to covering real housing costs.

**Mutual aid for health and family support (formalizing what already exists).** Sunheart's mother's care, his son's care, and other dependent obligations are already met through community-provision model. Formalizing this as a "community-backed care layer" available to other covenanted stewards with dependent obligations extends the model that already works for the Founding Steward to other vowed members as the community grows capacity.

Each of these expansions deepens the Covenant Layer's utility density without requiring any architectural change to the legal framework. They are developments of substrate, not of structure. Substrate development is slow and real; structural change is fast and often performative. The Path Two commitment means investing in substrate.

---

## 16. Open Questions for Further Review

1. **Covenant Layer legal verification.** The Covenant Layer architecture is rooted in established precedent but requires specialized religious-nonprofit counsel review before operational activation. What specific counsel credentials are required? What pilot activation scope is appropriate? What examination-readiness documentation standard must be met? This is v0.7's most important unresolved question—the framework's defensibility depends on getting this engagement right.

2. **Religious doctrine codification.** CORA Nation's religious doctrine is present in the body of work developed over years (Sacred Trinity, six Cs, Alignment Litmus Test, Consciousism, Paradise on Earth mission, Current/Circulation doctrine). It has not yet been formally codified as canonical religious texts. Who does the codification, under what community process, with what authority?

3. **Covenant Protocol design.** The Protocol describes substantial learning period, formal covenant, meaningful relinquishment, and community recognition. Specific operational design—learning curriculum, covenant text, recognition ceremony, ongoing renewal process—is required before first stewards can be enrolled.

4. **Interface Layer / Covenant Layer separation in practice.** Clean separation between employment compensation and covenant participation is non-negotiable for legal defensibility. How is that separation maintained operationally when OneBPO workers may also be CORA Nation covenant stewards? HR processes, distribution mechanisms, communications, and pastoral care all need architectural clarity.

5. **Demurrage at scale under hostile state action.** The v0.6 reframe as mutual credit clearing and the v0.7 addition of the Covenant Layer substantially reduce direct regulatory exposure. Open question remains: if the network grows large enough to be systemically visible, what prevents coordinated state or IRS action against CORA Nation's religious standing?

6. **Coherence production throughput measurement at scale.** How is network-wide coherence production measured such that it cannot be inflated by coordinated fake-coherence events?

7. **Shadow Extraction Index parameter tuning.** What weighting across resource types? What threshold triggers Verification Escrow redirection versus profit-pool restriction versus stewardship suspension versus network ejection? Empirical calibration required.

8. **ETO certification and the bootstrap-the-bootstrappers problem.** External Trusted Observers seed the Witness system. With the Covenant Layer added, ETOs gain an additional dimension: they also witness covenant readiness. This intensifies rather than relieves the bootstrap circularity.

9. **Verification window and escrow split calibration.** Is 6-12 months the right Verification Escrow window? Is 70/30 the right split? Role-dependent and context-dependent. Needs empirical data.

10. **Time-horizon weighting.** How are immediate, lifetime, and intergenerational outcomes weighted when they conflict?

11. **Crisis protocol design.** Still a placeholder. What are resilience protocols for war, scarcity, collapse, and hostile action against the religious community?

12. **Relationship to existing frameworks.** Doughnut economics, regenerative capitalism, GNH, SROI, ESG, existing complementary currency networks, and existing intentional religious communities. Formal affiliation with networks like CES, STRO, IRTA, or the Foundation for Intentional Community, or independent operation?

13. **AI governance depth.** If AI agents are the translation layer, what prevents them from becoming the de facto authority over time?

14. **The Tide Turner risk.** Architectural features maintaining commitment past the novelty phase?

15. **Circulation Equity Formula performance across organization types.** Software consultancy vs. manufacturing vs. care organization vs. agricultural operation—Useful Output variables differ substantially.

16. **Trust governance.** Who governs the community trust in Component 5 of the Equity Formula?

17. **Low-Friction Coherence cultural bias risk.** Friction reduction may privilege certain communication styles over others.

18. **Privacy versus gaming detection tradeoff.** Entity-level aggregation preserves privacy but weakens individual-gaming detection.

19. **Utility definition and extensibility.** The initial codified utility set grounds the Two-Economy Model, but the list must grow as the network develops. Who decides what new utility is added, and under what verification? With the Covenant Layer added, utility expansion also expands what the religious community provides to its members—deepening the covenant commitment and the legal framework's substantive requirements.

20. **Cross-organizational disparate impact.** The Coherence Multiplier is vulnerable to unconscious bias within a single organization. In cross-organizational settlement, bias can propagate across the network.

21. **Demurrage rate calibration for utility networks.** In a closed utility-access network, demurrage must be tuned below the rate at which members consume utility frantically just to avoid decay. In the Covenant Layer with religious-community flow-back, the calibration question is different: what rate keeps the community resource pool serving active need without starving individual stewards' access?

22. **Mathematical safety parameters in real deployment.** Spectral radius 0.7, hard leverage caps, dynamic reserves. Stress testing required before Phase 3 activation.

23. **Doctrinal integration.** The document describes CORA Nation doctrine in the register of a secular architecture specification. For the religious framework to hold legally, the doctrine must also exist in a genuinely religious register—scriptures, ceremonies, liturgy, pastoral writings. Who writes this material? How does secular architectural documentation coexist with religious canonical material without either undermining the other?

---

## 17. Legal and Economic FAQ

This section anticipates the questions that economists, employment lawyers, securities counsel, and tax advisors will raise when the system is presented for external review. Answers here are starting positions for legal dialogue, not final legal determinations.

### Is the Circulation Equity Formula a security issuance?

No. The formula is a profit-sharing and compensation structure, not a securities offering.

- **Dignity Base Wage** is standard wage compensation under local payroll law.
- **Contribution Dividend** is a performance-based variable compensation structure, analogous to commission pay, performance bonuses, or profit-sharing plans (IRC 401(a) and similar).
- **Circulation Share** is a contribution-weighted allocation from the same profit-sharing pool.
- **Stewardship Vesting** is a standard equity grant, administered under local securities law (e.g., qualified ISOs in the US, similar structures elsewhere). Stewardship Vesting is the only component that intersects with securities law, and it does so through established rails.
- **Trust Participation** is governed by local trust law, not securities law.

The Dividend Formula (Useful Output × Coherence Multiplier × Profit Pool Share) is an internal allocation methodology, not a traded instrument. It is no more a security than any company's internal bonus formula.

### What is the CU's legal status?

In Phases 1 and 2, the CU exists as an internal accounting unit within the Treasury, not as a traded instrument. Distributions to workers and participants occur entirely in legal-tender fiat (USD or local currency) through the Interface Layer.

In Phase 3, the CU operates as a mutual credit clearing unit within a closed network of CORA Nation member organizations. Mutual credit clearing networks have well-established legal standing in most jurisdictions, distinct from currency issuance. Reference precedents include WIR Bank in Switzerland (operating since 1934), Sardex in Sardinia, and regional B2B barter clearing networks. Because the CU is not bridged to external fiat for general exchange, is not purchased by members as an investment, and is used only to access network-exclusive utility, it does not trigger the Howey Test (not an investment contract), does not trigger FinCEN money services business regulation (not money transmission outside the closed network), and does not trigger per-transaction capital gains treatment in the way minted alternative currencies do.

### What happens if the system fails? Is there a graceful exit?

Yes. Graceful exit is a non-negotiable design requirement flowing from the Consent and Sovereignty principle.

- **Workers:** Retain full ownership of Dignity Base Wage, released Contribution Dividends, and vested Stewardship equity. Escrowed Dividend portions release on their normal schedule, subject to normal verification. No participant loses compensation they have earned.
- **Escrowed funds:** If the system is wound down before escrow windows mature, escrowed portions release to workers without verification requirement, because the verification infrastructure no longer exists.
- **Trust holdings:** The community trust continues to operate under its original terms. Trust dissolution, if required, distributes assets to current and historical participants per trust governance rules.
- **Credit holders (Phase 3+):** Outstanding credit balances convert to proportional claims on remaining network utility. Members can continue accessing already-committed utility until depletion. If utility access is exhausted before credit is depleted, remaining credit discharges. No fiat conversion obligation is created, because no fiat convertibility was promised.

### How do we prevent coherence-washing?

Coherence-washing is organizations (or individuals) claiming high coherence without producing it—the same pattern seen with greenwashing, pinkwashing, and ESG-washing. Defenses:

- **Shadow Extraction Index** catches claim-vs-consumption variance at the entity level.
- **Verification Escrow** economically disincentivizes short-term coherence theater by holding 30% of dividends until longitudinal consequences confirm the claim.
- **Distance-Weighted Witness** prevents internal echo chambers from validating their own claims.
- **Transparency of the Rosetta Stone** means every coherent metric shows its legacy translation, making it harder to hide extraction behind coherent language.
- **Third-party ETO review** during cold-start phases and periodic audits thereafter.

### What are the tax implications?

Tax treatment depends on which layer a given distribution flows through.

**Interface Layer distributions** (Dignity Base Wage, taxable Contribution Dividend portion, Stewardship Vesting, Trust Participation) are taxed under standard payroll, securities, and trust law in the relevant jurisdiction. No tax-avoidance architecture exists here, and none should. Avoiding legitimate tax obligations on employment compensation would itself be an extraction pattern.

**Logic Layer** is pure computation and does not itself distribute value, so no tax event arises from Logic Layer operation.

**Covenant Layer distributions** to covenanted CORA Nation stewards are treated under the tax framework for intentional religious community distributions—the same framework that has applied to monastic community support, apostolic associations under IRC 501(d), and intentional religious communities for centuries. When the covenant is real and the religious community is substantive, these distributions are not wage-equivalent compensation and are not taxed as such. This framework requires the safeguards listed in Section 5 to hold. Specialized religious-nonprofit counsel must verify before activation.

**Cross-organizational settlement in Coherent Credit** between CORA Nation member organizations follows the tax framework for mutual credit clearing networks, B2B barter clearing, and cooperative inter-entity transactions. Reporting is generally period-end rather than per-transaction, and the administrative burden is materially lower than for minted alternative currencies because credit movement between member organizations is not a property exchange in the sense that triggers capital gains treatment.

### How does the system handle phantom income on Coherent Credit receipt?

This concern surfaced in Gemini's fourth-pass critique and drove the introduction of the Covenant Layer in v0.7.

The concern: if a worker receives Coherent Credit that would be valued at fair market value of equivalent services, the IRS could treat that receipt as taxable income, creating a phantom income trap where the worker owes fiat taxes on non-fiat benefits.

The resolution: Coherent Credit flows only through the Covenant Layer to covenanted stewards. Covenant Layer distributions are religious-community participation benefits, not wage-equivalent compensation. The tax treatment follows established precedent for intentional religious community distributions, which have distinguished religious community support from taxable wages for over a century of US tax law.

This resolution holds conditionally. It requires:
- Real religious community with substantive doctrine and ongoing practice (not a wrapper)
- Real covenant commitment with meaningful relinquishment
- Clean separation between Interface Layer employment and Covenant Layer participation
- Engagement with counsel specialized in religious-nonprofit tax treatment before activation

Workers who are not covenant stewards do not receive Coherent Credit. Their compensation flows entirely through the Interface Layer as taxable wages and benefits under standard employment law. The phantom income problem does not arise for them because they do not receive non-fiat credit.

### How does demurrage work in a zero-sum mutual credit ledger?

This concern also surfaced in Gemini's fourth-pass critique.

The concern: in a double-entry mutual credit system, every positive balance exists because another party holds a corresponding negative balance. Demurrage on positive balances would require either forgiving corresponding debts (creating a borrow-and-wait-out exploit) or sweeping the decayed amount somewhere.

The resolution: Coherent Credit in the Covenant Layer is not a conventional zero-sum wage ledger. It is a religious-community resource pool. When idle credit decays, the decayed portion flows back to the community treasury for one of three uses:

- Redistribution to covenanted members with active material or participation needs
- Funding External Trusted Observer work, stewardship roles, and pastoral care
- Investment in expanding community utility (housing, food production, educational capacity, healthcare mutual aid)

This parallels how tithing and community resource pooling work in established religious communities. Demurrage is not a penalty on individual accounts; it is the community's mechanism for keeping material resources circulating in service of communal life and mission. The resource is religious community provision, not private property subject to decay.

On the corresponding-debt side: members who have drawn credit to access utility (e.g., a steward who has been supported by the community during a period of health crisis) do not have their obligations forgiven by demurrage. Their obligation is to continue contributing to community life as their capacity returns. The accounting framework is not double-entry zero-sum in the accounting-textbook sense; it is community-resource-pool flow, which is a recognized category in religious-community accounting.

### Does the utility ceiling limit credit velocity?

Another Gemini fourth-pass concern.

The concern: if Coherent Credit can only be spent on retreats, courses, and BPO services, velocity stalls because members cannot deploy credit for high-frequency daily needs (groceries, rent, childcare).

The resolution: this is partially addressed by the Covenant Layer but requires substantive CORA Nation development to fully resolve.

Religious communities have legitimate standing to provide housing, food, education, healthcare, childcare, and other material supports to covenanted members as part of religious community life. The Bruderhof, Hutterite, and Amish communities provide most or all of daily life's material requirements within their community framework. Catholic Worker houses and apostolic associations provide housing, meals, and mutual aid to committed members. Monastic communities provide total life support to monks and nuns under vow.

CORA Nation's initial utility set (Zen Village residencies, Coherence courses, OneBPO service access, stewardship roles, cross-organizational settlement) is narrow by design—a prudent starting point. Over time, as CORA Nation develops actual community provisioning capacity, the Covenant Layer utility set can legitimately expand to cover more of daily life for covenanted stewards. This is how intentional religious communities have historically grown.

What this does not resolve: utility density at launch. The ceiling resolves as a function of substantive development over years, not as a magical architectural feature. Stewards must be willing to receive some material support through the covenant community (which grows gradually) and provide their own daily-life needs through Interface Layer income (which remains fiat and taxable). This is how most intentional religious community traditions have worked historically, and it is how CORA Nation's Covenant Layer should operate for the foreseeable future.

### What jurisdictions can adopt this first?

Jurisdictions with existing strong profit-sharing infrastructure, trust law, and openness to complementary currencies are the likely first adopters:

- **United States:** Solid ground for the Circulation Equity Formula through existing profit-sharing, ESOP, and benefit corporation structures. Complementary currency experiments have precedent. CORA Nation's 508(c)(1)(A) status provides legal container. Intentional religious community tax treatment has centuries of precedent.
- **Switzerland:** WIR Bank demonstrates tolerance for complementary currencies. Strong cooperative tradition.
- **Philippines:** OneBPO's existing operations make this the operational first-mover regardless of broader Philippine legal frameworks.
- **Costa Rica:** Strong cooperative tradition, favorable ecological and social enterprise frameworks.
- **EU member states:** Strong employment law provides a rigorous compliance baseline; GDPR requires the privacy architecture already baked in.

Jurisdictions where Phase 1 deployment would be difficult include those with restrictive employment laws that limit profit-sharing flexibility, those hostile to alternative currency experiments, and those without developed trust law infrastructure.

### How is this different from ESG, SROI, or impact investing?

- **ESG/SROI/impact investing** apply secondary metrics to primarily extraction-structured economic activity. The underlying economic structure remains extractive; the metrics measure and mitigate harm at the edges.
- **The Remarkably Coherent Treasury** restructures the primary economic activity itself. The Circulation Equity Formula changes how value is distributed at the core. The CU changes how value is measured at the core. The metrics follow the structure, rather than the structure continuing unchanged while metrics try to police it.

The Measurement Humility Law is the deepest difference. ESG, SROI, and impact investing tend toward measurement-centric thinking—if we measure it, it will improve. Coherent Treasury architecture treats measurement as informational infrastructure serving lived coherence, not as a forcing function on behavior.

### What is the minimum viable deployment?

A single organization with:
- At least one coherent steward willing to adopt the Circulation Equity Formula
- At least 20 participants (for meaningful Distance-Weighted Witness calculations)
- Existing USD/fiat cash flow sufficient to support the Dignity Base Wage and Contribution Dividend structure
- Access to External Trusted Observers through CORA Nation or equivalent certifying body
- Willingness to operate Phase 1 for a minimum of 12 months before evaluating Phase 2 transition

OneBPO satisfies all five criteria and is the designated first-mover.

---

## Closing Note

**This system is not an invention. It is a removal.**

A removal of distortions that made truth hard to live in, alignment costly to hold, and coherence invisible underneath the metrics that were supposed to tell us what was real. The mechanics described here—the Two-Economy Model, the Three-Layer Architecture with its Covenant dimension, the Coherent Credit, the Circulation Equity Formula, the triangulation, the governance—describe an architecture that is already emerging through lived practice at Zen Village, in CORA Nation's ongoing ceremonial and teaching life, and in the stewardship community Sunheart and others have been building over years.

The wedge is simple. USD optimizes Money and suppresses Velocity and Coherence. We optimize Velocity and Coherence and let Money stay approximately where it is. The Two-Economy Model lets dollars keep doing what dollars do, while a parallel coherence economy handles the category of transactions dollars cannot properly authorize. The Three-Layer Architecture gives both economies their proper container: Interface Layer for fiat-compliant employment through secular entities like OneBPO, Logic Layer for coherence math, Covenant Layer for the religious community at the heart of CORA Nation's life. Neither economy drives the other out. Members hold both where both apply. Each serves its domain.

When truth becomes easier to live than distortion, systems reorganize themselves. When a religious community is substantively what it claims to be, the legal architecture follows naturally. When coherence is practiced rather than engineered, the financial infrastructure supports it rather than supplanting it.

**Submitted for external professional review. v0.10 completes the defensive legal architecture with three structural refinements from Gemini's seventh-pass review: Control-vs-Ownership separation (donated shares governed by majority-independent structure, not unilateral founder voting authority); Hybrid Settlement calibrated to fiat tax liability PLUS non-network fiat OPEX (preventing secular-entity slow bankruptcy); and Useful Output Oracle requirement (tamper-proof objective production data feeding the Dividend Formula). The architecture is now operationally specified across ownership, control, settlement, measurement, governance, compensation, and compliance dimensions, rooted in century-plus precedent across intentional religious community traditions (Bruderhof, Hutterite, Catholic Worker, Benedictine, apostolic associations) and B2B mutual credit clearing networks (WIR Bank, Sardex, regional barter exchanges). The Circulation Equity Formula is formally open-sourced to neutralize hidden-royalty attack vectors. GPT's seventh-pass strategic guidance on utility density (food, housing, mutual aid) is reflected in Section 15 as Phase 3 substrate development priorities, separate from the architecture itself. Recommended reviewers, in approximate order of engagement priority: counsel credentialed in 508(c)(1)(A) religious organizations with specific intentional-religious-community expertise; clergy-compensation tax specialists for founder compensation architecture verification; Philippine corporate and tax counsel for OneBPO structure; Costa Rican non-profit counsel for Asociación Civil or Cooperativa structure; employment lawyers familiar with clean secular-religious separation; mutual credit network practitioners; stewards of existing long-running intentional religious communities who can speak to operational realities over decade scales; and heterodox economists.**
