# Legal Critique — Sunheart / CORA Nation Current Operational State (2026-05-11)

**Reviewed:** 2026-05-11
**Focus:** Current operational state assessment — solid/grey/exposed buckets + this-week fixes
**Disclaimer:** AI critique grounded in retrieved Sunheart legal corpus. NOT legal advice. Engage licensed counsel for sign-off.

---

## TL;DR

The religious community substrate and basic entity stack are more defensible than most early-stage structures at this scale — the corpus work is real and shows serious thought. However, **three things are running hot right now with no structural cover:** (1) the leveraged SOL short inside a religious treasury is indefensible as prudent investment; (2) Cheyenne's psychic-readings business is operating commercially under the Sunheart brand with no clear entity or liability separation; and (3) the OneBPO → CORA Nation monthly contribution is a massive inurement exposure without documented arm's-length transfer pricing and independent board approval. Fix those three this week. Everything else is grey or fixable over the next 30-90 days.

---

## Strengths

- **Entity stack is multi-layered and intentional.** 508(c)(1)(A) + Trust + commercial LLCs is the correct separation architecture. `remarkably-coherent-treasury-v0.10.md §Decentralized Sovereign Containers` explicitly requires this separation and the doc reflects it in practice.

- **WPA / Character Cards / Mirror Pairing as member-gating.** Requiring religious-community participation steps before economic access is the right sequencing. `remarkably-coherent-treasury-v0.10.md §What Already Exists` confirms ceremonial and covenant participation as existing substrate, not projected. This supports the "genuinely religious community" defense the IRS would examine.

- **fp-credits as off-chain ledger tied to participation, not purchase.** Earning credits through covenant activity (WPA sign, DW witness, Mirror pair) rather than cash purchase is structurally sound for mutual-credit / religious-community-economy framing. `remarkably-coherent-treasury-v0.10.md §Three-Layer Architecture` and `§Two-Economy Model` explicitly support this design.

- **Treasury yield strategy is documented.** The three-tier approach (safety / yield / growth) matches `180pgChurch_Legal_Resource.pdf §Phase 4` which describes the same tiered structure. Documented policy is better than no policy.

- **Separation of spiritual authority from fiduciary authority is at least identified.** `remarkably-coherent-treasury-v0.10.md §Bifurcated Authority` explicitly requires that James not hold unilateral fiduciary control over OneBPO. The architecture knows the right answer — the gap is whether it's operationalized.

---

## Issues (ranked by severity)

---

### 🔴 CRITICAL — OneBPO → CORA Nation Monthly Contributions: Inurement Exposure

**Risk:** OneBPO is contributing $15–35k/month to CORA Nation, with James as Founding Steward of CN and (presumably) a controlling interest in OneBPO. This is the textbook inurement pattern the IRS examines first: a for-profit entity controlled by the church founder funneling money to the church, which then benefits the founder. The risk is not that the contributions are wrong — it's that without (a) an independent OneBPO board approving each transfer, (b) documented arm's-length rationale, and (c) clear classification (charitable donation vs. commercial payment for services), the IRS can recharacterize these as private inurement and revoke 508(c)(1)(A) status retroactively. April's $35,500 is above the $15–30k stated range — that variance, unexplained, is exactly the kind of thing that triggers scrutiny.

**Corpus citation:** `remarkably-coherent-treasury-v0.10.md §Bifurcated Authority` — "Any transfer of value between OneBPO and CORA Nation... is approved by OneBPO's independent fiduciary board at documented, audited market rates." `remarkably-coherent-treasury-v0.10.md §Control-vs-Ownership separation` — v0.10 explicitly flags that IRS examines *control* as well as ownership. `remarkably-coherent-treasury-v0.10.md §Genuine independence required` — "Independent directors are genuinely independent, not friends-of-the-founder."

**Suggested fix (this week):** Draft a one-page Transfer Pricing Policy for OneBPO → CN contributions. Classify each contribution type: (A) charitable donation from OneBPO to CN (requires arm's-length board resolution, no quid pro quo, no benefit flowing back to OneBPO or James personally); or (B) commercial payment for services CN provides OneBPO (requires a services agreement at market rate, UBIT analysis on CN's side). Convene at least a paper independent-board resolution approving the April and May contributions before May closes. This is the highest-ROI 30-minute legal task this week.

---

### 🔴 CRITICAL — Leveraged Derivatives Position in Religious Treasury: Prudent Investor Violation

**Risk:** A 3x leveraged short on 1,000 SOL held inside the Sunheart Private Trust is indefensible under the prudent investor standard applicable to trustees (general law, not from corpus — Uniform Prudent Investor Act applies in most US jurisdictions). The hard stop at $100 does not cure this: the position is speculative by design, uses leverage, and is held in a trust that also holds the religious community's 508(c)(1)(A) operational assets. If this position moves adversely, the trustee has personal liability exposure. If the IRS examines the trust during a 508(c)(1)(A) review, a leveraged crypto short inside the trust undermines the "prudent fiduciary" narrative across the entire treasury.

**Corpus citation:** `remarkably-coherent-treasury-v0.10.md` does not address leveraged derivatives as an authorized treasury instrument. The Tier 3 "Growth" bucket in `180pgChurch_Legal_Resource.pdf §Phase 4` and `legal_framework_synthesis_v2.md §Phase 4` includes "consciousness investments, strategic" — not leveraged speculation. The new 2026-05-11 treasury policy ("No gambling, sure wins + optimal yields") directly contradicts holding this position. The policy was set the same day as this review; the position predates it.

**Suggested fix (this week):** Either (a) close the SOL short position and document the closure as alignment with the new treasury policy — this creates a clean before/after narrative for any examiner; or (b) if you believe the position has strong thesis, transfer it to a personal account outside the Trust, document the transfer at fair value, and hold it as a personal (not trust/church) position. The Trust should not hold 3x leveraged derivatives. Pick one path today, document it in writing.

---

### 🔴 CRITICAL — Cheyenne / Sapphire Bot: Commercial Operation Under Sunheart Brand, No Entity Cover

**Risk:** A psychic-readings commercial business is live and accepting clients. It appears to operate under the Cheyenne/Sapphire brand with a live site and bot. The Champion Stack template at `SERVICES/champion-bot/` suggests this is a replicable model for 6 cohort members. The legal exposure here is layered: (1) **Liability** — psychic/spiritual services have generated consumer-fraud claims in multiple states; without a clear LLC or corporate entity, liability flows to the trust or to James personally as the platform operator; (2) **UBIT** — if this is characterized as CORA Nation running commercial services for members, it's Unrelated Business Income and triggers UBIT; (3) **State licensing** — some states regulate "fortune telling" or spiritual counseling; (4) **FTC / consumer protection** — "psychic readings" marketed commercially require truthful advertising disclosures. The corpus explicitly warns about commercial activities endangering exempt status.

**Corpus citation:** `180pgChurch_Legal_Resource.pdf §Phase 4` distinguishes church-owned operations (UBIT analysis required) from standalone commercial entities. `remarkably-coherent-treasury-v0.10.md §What Needs to Be Formalized` lists "Documented separation architecture between OneBPO and CORA Nation" as a requirement — same principle applies to champion commercial operations. The corpus does not address psychic-services licensing specifically (beyond corpus, general law).

**Suggested fix (this week):** Before onboarding any more Champion Stack members to commercial operations: (a) determine whether Cheyenne has her own LLC — if not, she needs one before taking another client payment; (b) ensure the site's terms of service clearly identify the contracting entity (her LLC, not CORA Nation or Sunheart Trust); (c) add a standard "entertainment purposes" disclaimer if operating in states that require it; (d) document that this commercial revenue flows to Cheyenne's entity, not to CORA Nation, and that CN's relationship to the Champion Stack is pastoral/educational, not commercial agency.

---

### 🟠 HIGH — $75k USDC on BitTrue at 8% Smart Earn: Counterparty + MSB Risk

**Risk:** BitTrue is a centralized exchange. Smart Earn is a yield product — structurally similar to the products that caused FTX, Celsius, and Voyager losses. The 50% counterparty diversification rule (set 2026-05-11) implies awareness of this. But there's a second risk: if CORA Nation or the Trust is deploying funds to a centralized exchange yield product, FinCEN and the IRS may characterize this as investment activity that requires reporting, and depending on how "Smart Earn" is structured, it may be a security (Howey: pooled funds, managed by a third party, expectation of profit). If BitTrue is deemed an unregistered securities issuer and CN is a known participant, that's reputational and legal exposure.

**Corpus citation:** `legal_framework_synthesis_v2.md §Phase 4` Tier 1 safety bucket: "treasuries, HYSA, money market" — a centralized exchange yield product is not in this tier. Corpus does not address BitTrue specifically. Beyond corpus: FinCEN guidance on virtual asset service providers and the SEC's ongoing scrutiny of exchange yield products (Kraken staking settlement, Coinbase enforcement) are general law context.

**Suggested fix:** Migrate $75k USDC to a regulated, insured vehicle (US Treasury-backed stablecoin fund, HYSA, or on-chain yield from a regulated custodian) within 30 days. Document the migration in the treasury ledger as compliance with the new diversification policy. If the 8% yield is mission-critical, get written legal opinion on whether Smart Earn constitutes a security before keeping funds there.

---

### 🟠 HIGH — PMA Structure: Implied But Not Documented

**Risk:** The doc says PMA protections are "informally implied via Coherent Champions Manifesto but NOT formally articulated as PMA charter." This means you're getting zero of the benefit. PMA protections under First Amendment association doctrine require: a written charter, clear private membership terms, documented membership acceptance, and genuine private (not public) commerce. Without the charter, every "private" transaction is public commerce subject to full commercial regulation. If the fp-credits ledger, WPA covenant, or Champion Stack services ever face regulatory scrutiny, there's no PMA charter to point to.

**Corpus citation:** `Cora Nation Manifesto.md §CORA Nation Citizenship Benefits` lists "508(c)(1)(A) protection, ecclesiastical trust advantages" as legal benefits — but does not formalize PMA charter. `180pgChurch_Legal_Resource.pdf` references PMA structure in the broader architecture. The corpus identifies the gap but doesn't close it.

**Suggested fix:** Draft a one-page PMA Charter this week. Minimum elements: name, purpose, membership criteria, membership agreement language, statement that the association operates privately among members. Have every WPA signer simultaneously sign the PMA membership agreement. This is a 2-hour drafting task that closes a structural gap you're already running.

---

### 🟠 HIGH — Costa Rica Entity: Unknown Legal Structure Holding $1.5M+ in Property

**Risk:** The doc states "CR legal layer not surfaced in cockpit." The corpus (`remarkably-coherent-treasury-v0.10.md §Costa Rica — The Substrate Container`) says it should be an Asociación Civil or Cooperativa — but explicitly flags "TO VERIFY: current legal structure of Costa Rican land holding." This means $1.5M in property is sitting in an unknown legal container with unknown governance, unknown directors, and unknown relationship to the US Trust and CORA Nation. Unknown = undefended. Costa Rica has its own nonprofit, labor, and property laws. If the CR entity is a for-profit company, or if James is listed as the sole owner/director, property ownership may trigger Costa Rican income attribution, residency rules, or complicate US FBAR/FATCA reporting.

**Corpus citation:** `remarkably-coherent-treasury-v0.10.md §Costa Rica — The Substrate Container` — the "[TO VERIFY]" flag is unresolved. `remarkably-coherent-treasury-v0.10.md §Decentralized Sovereign Containers` — the architecture requires the CR container to handle land and residential operations; it cannot do that if the legal structure is unknown.

**Suggested fix:** This week: pull the actual CR corporate registry record (Registro Nacional) for whatever entity holds the 45-acre property. Get the answer: what entity type, who are directors/members, what is the legal status. That's the foundation for everything else in Costa Rica. You cannot architect around an unknown.

---

### 🟠 HIGH — FBAR / FATCA: Foreign Exchange Account + Foreign Entity + Crypto

**Risk:** BitTrue is a foreign-domiciled exchange. If the Trust or James personally holds >$10k on BitTrue at any point, FBAR filing (FinCEN Form 114) is required annually. Additionally, if the CR entity has any bank accounts and James has signature authority or >50% ownership, those accounts also require FBAR. Failure to file FBAR is a $10k+ civil penalty per violation; willful failure is criminal. The $75k USDC on BitTrue alone triggers this threshold.

**Corpus citation:** Corpus does not address FBAR specifically. This is general law (Bank Secrecy Act, 31 USC §5314). The corpus does note in `remarkably-coherent-treasury-v0.10.md` that US-based reporting compliance is a CORA Nation architectural requirement — FBAR is part of that compliance layer.

**Suggested fix:** Confirm with a CPA whether FBARs have been filed for the BitTrue account and any CR entity accounts. The 2025 FBAR deadline (for 2025 calendar year accounts) is April 15, 2026, with auto-extension to October 15, 2026. If not filed, file now under the extension — late filing with reasonable cause is far better than non-filing.

---

### 🟡 MEDIUM — fp-credits Store: Coaching and Retreat Pricing May Constitute Commercial Services

**Risk:** The /game/store/ offers coaching at 150c and retreat at 500c + $1,500 cash. The cash component of retreat is real fiat money flowing for services rendered. If these services are delivered through or under the CORA Nation 508(c)(1)(A) umbrella, the IRS will ask whether this is UBIT (unrelated business income). The test: is the activity regularly carried on, and is it substantially related to the exempt purpose? Coaching and retreats *can* be substantially related to a religious community's mission — but only if documented as such, with clear mission-relationship memos, not just asserted.

**Corpus citation:** `180pgChurch_Legal_Resource.pdf §Phase 4` — "UBIT analysis applies" for Full Potential Store. `legal_framework_synthesis_v2.md §Documentation Required` — "UBIT defense memoranda" listed as required documentation. These memos don't appear to exist yet.

**Suggested fix:** Draft one-page UBIT relationship memo for coaching and retreat services, documenting the mission connection. This is internal documentation, not filed with the IRS, but it's the first thing you hand an examiner.

---

### 🟡 MEDIUM — Camp Zen Revenue Projections: $4M ARR at Y2 Creates Paper Trail

**Risk:** The Camp Director offer for Atlás is drafted with a "Player not employee, revenue-share model." A revenue-share model with a named individual for a planned $4M ARR operation will be examined under: (a) worker classification (is Atlás an employee under IRS 20-factor test and California/CR labor law?); (b) private benefit to Atlás (is this inurement?); (c) whether projected revenue at this scale makes Camp Zen a commercial operation rather than a religious one. The $4M ARR projection, once in writing, creates IRS examination risk if it's seen as a commercial business run inside a 508(c)(1)(A).

**Corpus citation:** `remarkably-coherent-treasury-v0.10.md §Decentralized Sovereign Containers` — Camp Zen should operate under the CR entity, not directly under CORA Nation. The separation architecture is the defense. `180pgChurch_Legal_Resource.pdf §Phase 4` — commercial retreat operations require UBIT analysis. The corpus does not address worker classification specifically.

**Suggested fix:** Before finalizing the Atlás agreement: (a) confirm Camp Zen operations are held in the CR entity, not CN directly; (b) have counsel review the revenue-share structure for worker misclassification under both CR and US law; (c) add explicit language that Atlás's compensation is mission-related and not inurement. Don't let the $4M number float in a document without a legal home for the entity running it.

---

### 🟡 MEDIUM — Coherent Treasury v0.10: Documented But Not Operationalized

**Risk:** The treasury architecture in v0.10 is sophisticated and legally grounded — but "NOT yet operationalized at all layers." This creates a specific risk: the legal defense of the structure depends on the structure actually existing. If the IRS examines CN today, they examine what actually exists, not what v0.10 intends. Specifically: the Control-vs-Ownership separation for donated shares (v0.10 requires majority-independent governance over donated shares — is that in place?), the Useful Output Oracle, and the hybrid settlement calibration are all described but not confirmed as operational.

**Corpus citation:** `remarkably-coherent-treasury-v0.10.md §Changelog from v0.9` — three structural refinements (Control-vs-Ownership, Hybrid Settlement, Useful Output Oracle) are identified as required before external review. `remarkably-coherent-treasury-v0.10.md §What Needs to Be Formalized` lists the specific gaps.

**Suggested fix:** Create a one-page "v0.10 Implementation Checklist" — each architectural requirement mapped to: (a) current status (operational / drafted / not started), (b) owner, (c) deadline. This clarifies which defenses exist now versus which are aspirational. Don't let the sophistication of the document create false confidence about the current state.

---

### 🟢 LOW / NOTE — Mockumentary: Content Liability + Privacy

**Risk:** The Village Mockumentary is public-facing and daily. Participants (members, visitors, contractors) appear on camera. Without signed media releases, you have potential right-of-publicity and privacy claims from anyone filmed. This is low severity now (Day 2 of production) but becomes a real issue fast if the content gains traction or if a member leaves the community on bad terms.

**Corpus citation:** Corpus does not address media releases. General law applies (right of publicity statutes vary by state; California is strictest).

**Suggested fix:** Add a one-paragraph media consent clause to the WPA / member onboarding flow before Day 10. For non-members who appear (guests, delivery people, etc.), use a standard release form. This is a 30-minute task.

---

## Missing / Unaddressed

- **OneBPO Independent Board: Not confirmed operational.** The architecture requires it. The doc does not confirm it exists with genuinely independent directors. This is the lynchpin of the inurement defense and it's a black box.
- **James's personal compensation structure from any entity.** Not mentioned. If James draws salary or benefits from CN, Trust, or any LLC, that flow needs to be documented as reasonable compensation at market rate or it's inurement / self-dealing.
- **US state registration for CN.** 508(c)(1)(A) is federal. States have their own charitable solicitation registration requirements. If CN solicits donations from residents of multiple states (likely, given the WPA is at fullpotential.com/game), state registration may be required in each state where solicitation occurs.
- **Sapphire Bot / Champion Stack: IP ownership.** Who owns the bot, the brand, the training data? If Sunheart infrastructure builds these bots and Cheyenne commercializes them, the IP ownership and licensing relationship needs documentation.
- **Coherent Credit: No securities law analysis documented.** The corpus frames fp-credits as mutual-credit / religious-community economics, which is the right framing — but no formal Howey analysis is documented anywhere in the retrieved corpus. Before scaling fp-credits, that analysis needs to be in writing.
- **CR property: Title insurance, zoning, environmental.** $1.5M in Costa Rica land with unknown entity structure and no confirmed title chain is a material asset with unaddressed risk.

---

## Open questions for human counsel

1. **Does OneBPO currently have a genuinely independent board of directors with documented meeting minutes approving CN contributions?** If not, what's the fastest path to establish this without triggering Philippine corporate law complications?
2. **Does the Sunheart Private Trust instrument authorize leveraged derivatives as permitted investments?** If so, does that authorization survive a prudent investor standard challenge in the Trust's domicile state?
3. **What is the actual current CR legal entity holding the 45-acre property?** What are the tax implications of that structure for US beneficial owners under FBAR/FATCA/PFIC rules?
4. **Does James have any personal compensation flowing from any entity in the stack?** If so, is it documented as reasonable compensation and approved by independent parties?
5. **Do the fp-credit store transactions (coaching at 150c, retreat at 500c+$1500) constitute sale of securities, sale of services, or religious-community participation?** A formal Howey and Reves analysis is needed before scaling the credit economy.
6. **Does the WPA / covenant structure, combined with the revenue-share model for Atlás, create an employment relationship under Costa Rican labor law?** CR has strong labor protections; "Player not employee" language may not hold.

---

## Suggested next iteration

Before v0.2 of this state document, James should resolve the CR entity question (pull the Registro Nacional record and surface the actual legal structure) and confirm whether OneBPO's independent board is operational with documented meeting minutes — those two facts change the severity rating on the two largest exposures. v0.2 should also include a column in the operational table showing which entity each activity legally runs through, so the separation architecture is visible at a glance rather than assumed.
