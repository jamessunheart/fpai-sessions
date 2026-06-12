# Legal Critique — BUTR Universe v0.2

**Reviewed:** 2026-05-13
**Focus:** Securities + creator-economy + meme-token
**Disclaimer:** AI critique grounded in retrieved Sunheart legal corpus. NOT legal advice. Engage licensed counsel for sign-off.

---

## TL;DR

v0.2 is meaningfully safer than v0.1. The three structural fixes (MC-target marketing killed, Howey loop decoupled, MTL avoidance via wallet-to-wallet) are real improvements, not cosmetic. The highest remaining risk is **residual Howey exposure in the "cultural identity marker" framing** — describing BUTR as something that signals "you're in the Churn Crew if you hold BUTR" still creates a soft membership/access inference that sophisticated SEC staff will probe. The biggest unaddressed gap is **no explicit Howey "common enterprise" severance** — the doc kills profit expectation language but doesn't affirmatively sever the "efforts of others" and "common enterprise" prongs at the structural level. Secondary concern: the FTC influencer disclosure framework is acknowledged but not yet operationalized, and that's the fastest enforcement path in a creator-economy play.

---

## Strengths

- **Standalone Brand LLC architecture (§0)** is the correct call. The corpus (remarkably-coherent-treasury-v0.10.md, Closing Note) confirms that CORA Nation's Two-Economy Model and 508(c)(1)(A) substrate are incompatible with open-market meme-token mechanics. Keeping BUTR separate prevents religious-nonprofit contamination and eliminates the inurement/private-benefit vectors that the corpus flags repeatedly (remarkably-coherent-treasury-v0.10.md, Governance Firewall section: "Private inurement is the number one cause of intentional religious community legal destruction").

- **Arm's-length charitable donation structure to Heart-of-Gold (§0)** is correctly framed as a donor relationship, not a structural linkage. This tracks the corpus's repeated insistence on entity separation as the primary defense against IRS challenge.

- **Hard presale ban (§7)** is clean and unambiguous. Removing "if possible" language was the right move. Presale + fixed supply + revoked mint/freeze authority is the minimum viable Howey-defense token architecture. The corpus (18pgChurch_Legal_Summary: "Securities Act Section 3(a)(4)," citing Howey) confirms this is the right framing.

- **Wallet-to-wallet tipping with no Brand LLC custody (§4, §8)** correctly addresses the FinCEN MTL vector. The corpus does not address money transmission law directly, but the fix is consistent with general FinCEN/BSA doctrine (reasoning beyond corpus — well-established).

- **Engagement-based leaderboard replacing spend-based ranking (§4)** severs the most direct Howey "expectation" loop. Rank-for-spend is a classic investment-contract pressure point; rank-for-participation is not.

- **"No-purchase-necessary" gift program framing (§6)** is the correct FTC 16 C.F.R. Part 251 move. Explicitly acknowledged in the doc.

- **Section 12 risk-vector table** is thorough and shows genuine legal engineering rather than checkbox compliance.

---

## Issues (ranked by severity)

### 🔴 CRITICAL — "Cultural Identity Marker" / Soft Membership Framing Retains Howey Residue

**Risk:** §5 defines BUTR as "a cultural identity marker (you're in the Churn Crew if you hold BUTR)." Even with the access-key severance, this sentence structurally ties BUTR holding to a membership status ("Churn Crew") that — if the Churn Crew has *any* perceived value (social recognition, community belonging, brand affiliation) — recreates the "benefit from others' efforts" prong of Howey. The SEC's post-*Impact Theory* enforcement posture targets exactly this: NFT/token projects that disclaim investment while promising community belonging that buyers expect to appreciate in value as the brand grows. The doc correctly kills price-prediction language, but brand growth (more Milkmaids, more events, more Heart-of-Gold press) is still "others' efforts." If BUTR holders believe their "Churn Crew" status becomes more culturally valuable as the brand scales, that's a Howey expectation — even without a price target.

**Corpus citation:** 18pgChurch_Legal_Summary-Resource.md.pdf cites *SEC v. Howey, 328 U.S. 293 (1946)* as controlling securities authority. The corpus does not analyze "cultural identity marker" language specifically — this is reasoning beyond the corpus grounded in post-*Howey* SEC enforcement posture (*SEC v. Impact Theory* 2023, *SEC v. Stoner Cats* 2023 — general law, not from corpus).

**Suggested fix:** Three moves:
1. Replace "you're in the Churn Crew if you hold BUTR" with "BUTR is one way to participate in the churn — but the Churn Crew is everyone who shows up, tips or not."
2. Add an explicit sentence: "BUTR does not confer membership. Churn Crew is a cultural description of participants, not a defined member class. Holding BUTR neither admits you to nor excludes you from any defined group."
3. In §7 hard-no list, add: **"Framing BUTR holding as membership in any defined community or club"** — consistent with the existing "(SEC v. Dapper Labs)" note already in the hard-no table.

---

### 🔴 CRITICAL — "Common Enterprise" Prong Not Affirmatively Severed

**Risk:** The doc's Howey defense focuses almost entirely on killing the "profit expectation" prong (no price targets, no yield, no revenue share). But Howey has four prongs: (1) investment of money, (2) common enterprise, (3) expectation of profits, (4) from efforts of others. A fair-launch meme token where buyers pool capital into an open-market price is arguably a *horizontal* common enterprise (buyers' fortunes rise and fall together based on Brand LLC's brand-building efforts). The doc never affirmatively addresses this. If the Brand LLC publicly promotes BUTR, runs Churn House events that drive cultural value, and receives tips it then donates to Heart-of-Gold (creating positive PR), those are "efforts of others" that a determined SEC examiner will point to.

**Corpus citation:** 18pgChurch_Legal_Summary-Resource.md.pdf cites Howey as controlling; corpus does not address common-enterprise prong analysis specifically — reasoning beyond corpus, grounded in standard Howey four-prong framework.

**Suggested fix:** Add a §5 subsection: "BUTR and the Howey Framework." State explicitly: "Brand LLC does not pool BUTR proceeds. Brand LLC does not receive BUTR in exchange for promises of brand-building activity. Brand LLC's creative work is independent of BUTR's market price. BUTR holders' market outcomes are not linked to each other through any Brand LLC mechanism." This is a structural severance argument, not just marketing language. Counsel must confirm whether the actual operational structure (Brand LLC promotes BUTR content, BUTR rises) survives this prong.

---

### 🟠 HIGH — FTC Influencer Disclosure Is Acknowledged But Not Operational

**Risk:** §12 correctly flags FTC 16 C.F.R. Part 255 and says it will be "codified in Content & Language Policy + Milkmaid agreement." But neither document exists yet, and the launch sequence (§11) shows Milkmaid recruitment happening at Step 7, before Content & Language Policy is confirmed operational. If a Milkmaid posts BUTR content after receiving a tip or gift without disclosing the relationship, the FTC exposure attaches to **Brand LLC** as the "advertiser" under its endorsement guides — not just to the Milkmaid. The FTC's 2023 updated guides significantly expanded liability for brands that fail to ensure their creator partners disclose. This is a fast enforcement path: FTC consumer protection investigations move faster than SEC securities actions.

**Corpus citation:** Corpus does not address FTC Part 255 directly. General law, well-established. Referenced in §12 of the doc itself.

**Suggested fix:** Promote Content & Language Policy v0.1 to a **gate** before Step 7 (Milkmaid recruitment), not a parallel deliverable. The Milkmaid agreement must include: (a) mandatory disclosure language templates for every BUTR promotional post; (b) Brand LLC right to require disclosure correction before next collaboration; (c) Milkmaid representation that they will comply with applicable FTC rules. Do not recruit Milkmaids without a signed agreement containing these provisions.

---

### 🟠 HIGH — 1099-NEC / Crypto Tip Tax Notice Is Incomplete for Milkmaid Risk

**Risk:** §12 notes "1099-NEC issued for >$600/year" and references IRS Notice 2014-21 for crypto tip taxation. This is directionally correct but under-specified in two ways. First, 1099-NEC applies to Brand LLC payments to Milkmaids — but if tips go wallet-to-wallet (fan→Milkmaid, no Brand LLC custody), Brand LLC has **no reporting obligation** and **no visibility** into Milkmaid tip income. The Milkmaid tax notice in the agreement is then the only protection, and it needs to be explicit: "You are solely responsible for reporting all cryptocurrency received as tips, gifts, or compensation as ordinary income at fair market value on date of receipt per IRS Notice 2014-21. Brand LLC is not your withholding agent for wallet-to-wallet transfers." Second, if Brand LLC ever receives BUTR (e.g., in its own wallet for any operational purpose), that receipt is itself a taxable event — the doc doesn't address Brand LLC's own crypto tax position.

**Corpus citation:** remarkably-coherent-treasury-v0.10.md references "individual US stewards still have FBAR/FATCA obligations" — same individual-vs-entity distinction applies here. Corpus does not address IRS Notice 2014-21 directly.

**Suggested fix:** (1) Milkmaid agreement must contain explicit IRS Notice 2014-21 notice, not just a reference in §12. (2) Add a Brand LLC Crypto Tax Policy covering: when/if Brand LLC ever holds BUTR, how it values and reports those holdings; whether the charitable donation of BUTR-equivalent value to Heart-of-Gold triggers recognition. (3) Engage a crypto-tax CPA alongside securities counsel — this is a distinct specialty.

---

### 🟠 HIGH — AB5 Survival Is Claimed But Not Structurally Locked

**Risk:** §3 lists the AB5 survival mechanics (own content, own schedule, free to post elsewhere, no brand-directed production requirements, leaderboard not used as management). These are the right factors. But two structural gaps remain. First, the "no Brand-directed production requirements" claim is in tension with §6's gift program: "Milkmaids may churn actual butter (licensed creamery / commercial kitchen)" — if Brand LLC organizes, directs, or schedules the churning activity, that's directorial control under Dynamex/AB5. Second, "Brand LLC provides... optional creamery access" (§3) — if the creamery is Brand LLC-controlled and Milkmaids work in it, they are almost certainly employees in California regardless of other factors.

**Corpus citation:** Corpus does not address AB5 or California employment law. General law (Dynamex Operations West, Inc. v. Superior Court, 2018; AB5 Cal. Lab. Code §2775 et seq.) — not from corpus.

**Suggested fix:** (1) The Milkmaid agreement must pass the ABC test on its face in CA: (A) free from Brand LLC control in connection with the work; (B) performing work outside the usual course of Brand LLC's business (if BUTR's business IS creator content, this is a hard B-prong problem — counsel must advise); (C) independently established in the same trade. The B-prong is the danger zone for a content brand recruiting content creators. (2) "Creamery access" must be structured as a venue rental or third-party facility — not a Brand LLC-controlled workspace. (3) Flag this explicitly as needing CA employment counsel sign-off before any CA Milkmaid recruitment.

---

### 🟡 MEDIUM — Reves "Family Resemblance" Test Not Addressed for BUTR

**Risk:** The doc correctly cites Reves in the hard-no table (yield promises → Reves notes). But Reves matters for a different reason: if BUTR is characterized as a **note** (a debt instrument) rather than an investment contract, the Reves family-resemblance test applies instead of or alongside Howey. Meme tokens are not obviously notes, but if Brand LLC ever accepts BUTR in exchange for any promise of future delivery (butter, merch, events) — even informally — that creates a debt-instrument argument. The doc's current structure avoids this, but the analysis is not stated.

**Corpus citation:** 18pgChurch_Legal_Summary-Resource.md.pdf cites Reves implicitly through the corpus's "Securities Act Section 3(a)(4)" reference. Reves v. Ernst & Young, 494 U.S. 56 (1990) is general law, not from corpus.

**Suggested fix:** Add one line to §5: "BUTR is not a note, bond, or debt instrument. Brand LLC makes no promise of future delivery of any good, service, or asset in exchange for BUTR." This closes the Reves door proactively.

---

### 🟡 MEDIUM — "Churn Wars" Community Event / Sweepstakes Line Remains Fuzzy

**Risk:** §3 and §11 (Step 12) describe Churn Wars as "community events, NOT prize sweepstakes" — but the reframing is more declaration than structural analysis. State sweepstakes law (particularly in NY and FL, which require registration and bonding for sweepstakes over $5,000 in prizes) doesn't care what you call the event. If participants compete for something of value and winners are selected by chance or a combination of chance and skill, it's a sweepstakes/contest regardless of branding. The doc's mitigation — "if prizes are awarded, separate sweepstakes-law review + no-purchase-necessary mechanic" — is correct but incomplete. "Cream Rising" (most-shared meme of the week) involves selection and recognition; if the recognition has any monetary value (signed merch, gift packages), that may trigger contest law in some states.

**Corpus citation:** Corpus does not address sweepstakes law. General law.

**Suggested fix:** In §3 and §11, add: "Any Churn Wars recognition that includes items of monetary value will be reviewed against state contest/sweepstakes law before announcement, including NY and FL registration requirements. Recognition items of purely nominal or zero monetary value (shout-outs, digital badges, name on wall) do not trigger sweepstakes law." Draft the Churn Wars rules document before the first event.

---

### 🟡 MEDIUM — Section 230 "Hosting Platform" Claim Needs Operational Reality Check

**Risk:** §12 claims Brand LLC operates Churn House "as a hosting platform, NOT as content co-creator." Section 230 protection (47 U.S.C. § 230) requires that Brand LLC not materially contribute to the creation of Milkmaid content. But the doc also says Brand LLC provides "brand assets (logos, lore, mascots, churn aesthetic)" and that Milkmaids operate within "internal content guidelines" defining what "flirty" means. Providing brand assets + content guidelines + aesthetic direction makes Brand LLC look less like a passive host and more like a content co-creator or at minimum an editorial director — which erodes 230 protection for third-party content. This matters most if Milkmaid content generates complaints (FTC, state AG, platform bans).

**Corpus citation:** Corpus does not address Section 230. General law.

**Suggested fix:** Counsel must advise on the co-creation vs. hosting line given the brand-asset provision and content guidelines. At minimum: content guidelines should define prohibited content (explicit, illegal) without prescribing affirmative creative direction ("be flirty this way"). Brand assets should be available optionally, not required. The Churn House terms of service should include a clear notice that Milkmaid content is theirs and that Brand LLC is not a content producer.

---

### 🟢 LOW / NOTE — Charity Flow-Through Percentage Not Locked Creates Marketing Risk

**Risk:** §0 and §5 reference "we donate X% of profits to Heart-of-Gold" and "% of any BUTR it receives." The percentage is not defined in this doc. This is fine for now — it's a v0.2 design doc. But publicly marketing a charity percentage before it's locked in a formal charitable contribution agreement creates FTC deceptive advertising exposure (if the percentage is implied and then not delivered) and state charitable solicitation registration requirements in many states.

**Corpus citation:** remarkably-coherent-treasury-v0.10.md references "charitable contribution infrastructure for US donors" as a CORA Nation function — confirms the arm's-length donation model is structurally sound. Corpus doesn't address state charitable solicitation law.

**Suggested fix:** Before any public marketing of the charity relationship, (a) lock the percentage in the charitable contribution agreement per Brand Tok v0.4 Addendum B.2; (b) review whether Brand LLC's state charitable solicitation law requires registration before publicly promoting the donation; (c) be precise in copy — "we donate a portion of profits" rather than implying a specific percentage until it's legally committed.

---

### 🟢 LOW / NOTE — Delaware vs. Wyoming LLC Choice Has Securities Implications

**Risk:** §11 Step 3 defers LLC formation state to counsel. This is correct. But note for the record: Wyoming LLC law (specifically Wyo. Stat. §17-29-110) has been used by crypto projects to argue for DAO-LLC structures with reduced member liability and governance flexibility. Delaware has more established case law for investor disputes. The choice matters for how Milkmaid contractor agreements and any future token-governance disputes are litigated. Wyoming's crypto-forward statutory environment may also affect how regulators perceive the entity's intent.

**Corpus citation:** Corpus does not address LLC formation state choice. General law.

**Suggested fix:** Securities/token counsel should advise on formation state with awareness of Wyoming's DAO-LLC statute and Delaware's investor-dispute case law. Neither is obviously superior — this is a genuine counsel question.

---

## Missing / Unaddressed

- **Explicit four-prong Howey analysis in the doc itself.** The doc does Howey work but never frames it as a four-prong analysis. A formal §5.1 "Howey Analysis" subsection (investment of money → acknowledged; common enterprise → severed; profit expectation → severed; efforts of others → severed) gives human counsel a clear target to sign off on and makes the doc litigation-defensible if ever needed.

- **State securities law (Blue Sky).** Federal Howey analysis is the focus, but state securities regulators (especially CA, NY, TX) have their own registration and exemption rules. A fair-launch meme token may still require analysis under state Blue Sky law even if it clears federal Howey. Corpus does not address this. Counsel must advise.

- **Platform-specific terms of service compliance.** §13 lists "adult-content platform-policy review (X, TikTok, IG specifically)" as open. This is not a legal risk in the securities sense but it is a **brand-survival risk** — if Milkmaid content triggers platform bans before the Churn House is independent, the entire creator-economy layer collapses. TikTok and Instagram have strict crypto promotion rules independent of SEC law. This should be a gate, not an open question.

- **OFAC / sanctions screening.** Wallet-to-wallet tipping is borderless. If a sanctioned-country wallet tips a Milkmaid in BUTR, the Milkmaid (and potentially Brand LLC if it facilitated the infrastructure) may have OFAC exposure. Corpus does not address this. Standard crypto compliance counsel question.

- **IP ownership chain for BUTR brand assets.** The doc references Brand LLC providing logos, lore, mascots — but doesn't establish who owns the IP and how it's licensed to Milkmaids. If a Milkmaid creates a viral BUTR meme using Brand LLC assets, who owns the derivative? This is a content/IP question, not a securities question, but it belongs in the Milkmaid agreement.

- **Data privacy (CCPA, GDPR) for Churn House site.** If the site collects engagement data (participation tracking for the engagement leaderboard), California CCPA and potentially GDPR apply. Not addressed anywhere.

---

## Open questions for human counsel

1. **Does the Brand LLC's ongoing brand-promotion activity (Churn House events, Milkmaid support, Heart-of-Gold PR) constitute "efforts of others" sufficient to satisfy the fourth Howey prong, even without a formal investment contract structure?** This is the core question AI cannot answer — it requires a securities attorney's opinion on the specific operational facts.

2. **Does the AB5 B-prong analysis survive for CA Milkmaids, given that BUTR's core business IS creator content?** If Brand LLC's usual course of business is producing/promoting creator content, Milkmaid creators may be employees by default in California regardless of any contract.

3. **Is the wallet-to-wallet tipping infrastructure (fan→Milkmaid, no Brand LLC custody) truly outside FinCEN money services business definition if Brand LLC designed, deployed, or recommends specific tipping software?** The line between "facilitating" and "transmitting" is a FinCEN question that requires specialized AML/BSA counsel.

4. **Do any state Blue Sky exemptions apply to the BUTR fair launch, or does the token require state-level securities analysis in target distribution states?**

5. **Does Brand LLC's receipt of BUTR (even temporarily, for any operational purpose) create a taxable event, and how should the charitable donation of BUTR-equivalent value to Heart-of-Gold be structured to avoid double taxation?** Crypto-tax CPA question.

6. **What is the correct legal characterization of the "optional creamery access" Brand LLC provides to Milkmaids — venue rental, license, or employer-provided workspace — and does it affect the independent contractor analysis?**

---

## Suggested next iteration

v0.3 should add: (1) a formal four-prong Howey analysis subsection in §5 that counsel can directly sign off on, including explicit common-enterprise severance language; (2) Content & Language Policy v0.1 as a **completed gate document** (not a future deliverable) so Milkmaid recruitment has an operationalized legal foundation; and (3) a Blue Sky / state securities law placeholder section acknowledging the gap and deferring to token counsel — right now the doc is silent on state-level securities law entirely, which will be the first thing a securities attorney asks about.
