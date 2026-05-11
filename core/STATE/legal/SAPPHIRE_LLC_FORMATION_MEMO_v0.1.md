# Sapphire LLC — Formation Memo + Interim Operational Guardrails

**Status:** DRAFT — for Cheyenne + James review
**Date:** 2026-05-11
**Subject:** Sapphire Bot commercial operations entity formation

---

## The issue (per Counsel critique 2026-05-11)

Cheyenne's Sapphire Bot (@LilSapphirebot + cheyennesapphire.com) is **live and accepting clients commercially** for psychic readings. Without a clear LLC or corporate entity:

1. **Liability flows to James personally and/or the Sunheart Trust** as the platform operator
2. **Could be characterized as CORA Nation running commercial services** → triggers UBIT (Unrelated Business Income Tax)
3. **Some states regulate "fortune telling" / psychic services** — licensing or disclosure required
4. **FTC consumer protection** — psychic readings marketed commercially need truthful advertising disclosures

Per Counsel: *"Before onboarding any more Champion Stack members to commercial operations: (a) determine whether Cheyenne has her own LLC — if not, she needs one before taking another client payment."*

---

## 🛑 PRECONDITION TO LLC FORMATION (added 2026-05-11 post-sanity-check)

**Identify Cheyenne's state of legal residence FIRST.** This affects two material decisions:

1. **LLC formation choice:**
   - If Cheyenne lives in her home state, forming an LLC in Delaware (or any state other than home) means registering as a foreign LLC in her home state — added cost ($100-300/yr registered agent in BOTH states), added compliance, no real benefit for a small services LLC.
   - For Sapphire's scale (psychic readings, single member, simple commercial activity): **Cheyenne's home state is likely the cleanest choice** unless she has specific reason for Delaware.
   - Delaware is best for entities raising outside investment or planning multi-state expansion. Sapphire is neither.

2. **Psychic services regulatory profile:**
   - State licensing requirements vary substantially: California has local fortune-telling ordinances; New York §165.35 requires "entertainment only" disclaimer to avoid Class B misdemeanor; Florida varies by county; most other states have lighter rules.
   - The right disclaimer language and pricing posture depends on Cheyenne's residence + where her clients are.

**Action before LLC filing:** Confirm Cheyenne's state of residence and her primary client geography. Form the LLC accordingly. The Delaware-default in v0.1 may not be the right answer for her specific situation.

---

## Action sequence

### Immediate (this week) — Interim guardrails until LLC is formed

If Sapphire Bot continues taking clients before LLC formation:

1. **Update terms of service** on cheyennesapphire.com to clearly state:
   - "Sapphire is operated by Cheyenne [Lastname] as a sole proprietorship."
   - "Sapphire is NOT operated by CORA Nation, Sunheart Trust, or Sunheart Ventures LLC."
   - "Sessions are for entertainment and inspiration purposes."
   - "Sapphire makes no claims of supernatural ability or psychic accuracy."
2. **Adjust payment routing** so client payments go to Cheyenne's personal account, NOT to any Sunheart/CORA-related account.
3. **Sunheart support of Sapphire is limited to:** technical platform (bot hosting, site), brand creative, mentoring. Sunheart does NOT process payments or sign client agreements.
4. **No further Champion Stack commercial activations** until at least the first one (Sapphire) is properly entitied.

### 1-2 weeks — Form Sapphire LLC

**Step 1: Choose state of formation**
- **Recommended: Delaware** (preferred for LLCs; minimal state income tax for online services; standard formation procedures)
- **Alternative: Cheyenne's home state** (if she wants simpler tax setup; some states allow "domestic" LLCs that match her physical operations)

**Step 2: Choose entity name**
- Name suggestion: "Sapphire Readings LLC" or "Sapphire & Co LLC" or similar
- Avoid: anything implying CORA Nation / Sunheart affiliation (preserves arm's-length)
- Verify name availability via the state's Secretary of State website

**Step 3: File Articles of Organization**
- Delaware: file online at [Delaware Division of Corporations](https://corp.delaware.gov), ~$110 filing fee + Registered Agent ($50-150/yr)
- Other states: similar process, fees vary

**Step 4: Get EIN from IRS**
- Apply online at [irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online](https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online)
- Free, immediate
- Required for opening business bank account

**Step 5: Open business bank account**
- Routes Sapphire revenue to LLC account
- Separates personal finances from business finances
- Standard small business banks: Mercury (online), local credit unions, Chase Business

**Step 6: Update Sapphire Bot + site**
- Terms of service: contracting entity is now "Sapphire Readings LLC"
- Payment processor (Stripe, etc.): account in LLC name
- Privacy policy: entity references updated

**Step 7: Update CORA Nation / Sunheart relationship**
- Per Brand Tokenization Architecture v0.4: Brand LLC operates at arm's length from CORA
- Sapphire LLC may voluntarily contribute % of profit to CORA Nation (per Cheyenne's own decision, no quid pro quo)
- Sapphire LLC may accept Coherent Credit for member discount eligibility (binary check only)

---

## State-specific licensing / disclosure considerations

Psychic services are regulated differently by state. The major frameworks:

- **California:** Local ordinances may require "fortune telling" permits; "entertainment only" disclaimer commonly used
- **New York:** §165.35 makes fortune telling a Class B misdemeanor unless for "show or entertainment" — disclaimer required
- **Florida:** Some local jurisdictions require fortune telling permits; statewide framework lighter
- **Most other states:** No specific licensing; standard consumer-protection / truthful-advertising rules apply

**Recommended language on the site (works in most jurisdictions):**

> *Sapphire Readings are provided for entertainment, self-reflection, and spiritual inspiration purposes. Sapphire makes no claims of supernatural ability, psychic accuracy, or predictive power. Readings are not a substitute for professional medical, financial, legal, or psychological advice. Clients should make their own informed decisions and consult appropriate licensed professionals for matters requiring expert guidance.*

**If targeting clients in California, New York, or other regulated states specifically:** Add explicit "for entertainment purposes only" language above the booking flow.

---

## Liability insurance (consider)

Once LLC is formed, Sapphire Readings LLC should evaluate:
- **General liability insurance** ($1M / year, ~$500-1,000/yr) — covers consumer claims
- **Professional liability / E&O** (if applicable to psychic services — coverage varies; some insurers exclude)
- **Cyber liability** if storing client information

Not a Day 1 requirement, but should be in place within 60 days of LLC formation.

---

## Champion Stack template implication

The Champion Stack at `SERVICES/champion-bot/` is designed to ship Sapphire-style bots for the other 5 First Cohort members. Each commercial Champion needs the same LLC structure:

| Champion | Brand suggestion | LLC formation status |
|---|---|---|
| Cheyenne — Sapphire | Sapphire Readings LLC | 🟡 needs formation (this memo) |
| Atlás — Camp Zen | Camp Zen LLC | 🔴 needs formation before retreat ops |
| Halley — TBD | TBD | 🔴 needs formation before commercial activation |
| Josh — TBD | TBD | 🔴 needs formation before commercial activation |
| Sierra — TBD | TBD | 🔴 needs formation before commercial activation |
| Delaney — TBD | TBD | 🔴 needs formation before commercial activation |

**Policy:** No First Cohort member operates commercially under the Sunheart / CORA Nation umbrella without their own LLC. Use this Sapphire LLC formation as the template.

---

## Counsel-engagement scope

Sapphire LLC formation is a routine commercial setup — does NOT need the same specialty counsel as the Brand Tokenization Architecture review. Options:

- **DIY (Delaware) with online services:** Stripe Atlas (~$500 all-in), Clerky, LegalZoom — ~30 min of work
- **Local counsel ($500-1,500):** for state-specific licensing review (especially CA, NY operations)
- **Recommended:** DIY Delaware formation now (1 hour, $500); add specialty counsel review after Brand Tokenization counsel engagement completes (one engagement covers multiple Brands)

---

## What this enables

After Sapphire LLC is formed:
- Cheyenne owns Sapphire LLC; CORA Nation has zero equity
- Sapphire revenue flows to LLC account, not Sunheart-related accounts
- Liability isolated to Sapphire LLC
- UBIT exposure eliminated from CORA Nation side (CORA isn't running the commercial activity)
- Champion Stack template proven; replicable for the 5 remaining First Cohort members
- Brand Tokenization Architecture v0.4 operational baseline established (first Brand LLC operating)

---

## Action required this week

- [ ] Cheyenne reviews this memo
- [ ] Decision: form Sapphire LLC in Delaware OR home state
- [ ] Cheyenne files Articles of Organization (or James assists; ~1 hour)
- [ ] Apply for EIN (15 min)
- [ ] Open business bank account (within 2 weeks of formation)
- [ ] Update cheyennesapphire.com TOS + payment routing within 1 week of bank account open

Total cost: ~$500 + Registered Agent annual ~$100. Total time: ~3-4 hours of Cheyenne's attention over 1-2 weeks. Risk reduction: liability exposure eliminated; CORA / Sunheart umbrella cleaned up; Champion Stack template established.

---

## Until LLC is formed

**If Cheyenne wants to keep taking clients THIS week before LLC is filed:**
- Accept payments to her personal account ONLY
- TOS update: "Sapphire is operated by Cheyenne [Lastname] as a sole proprietorship"
- Make the disclaimer language live on the site immediately
- No invoices, receipts, or communications reference CORA Nation, Sunheart Trust, or any Sunheart entity

This is interim — sole proprietorship liability is still personal (Cheyenne, not James/Sunheart), but the umbrella cleanup is the urgent fix. LLC formation upgrades the protection.
