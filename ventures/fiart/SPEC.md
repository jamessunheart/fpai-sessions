# Fi-art — Master Spec

**One sentence:** Fi-art is a cultural liquidity system where anyone can create money-inspired art, verified creators can attach real-world utility, capacity providers turn unused inventory into liquid notes, and trusted art holders support fiat exits — every note carrying a Truth Panel that teaches monetary literacy through use.

**Domain:** fiart.org
**Status:** SPEC (no code yet) · 2026-06-25
**North star:** A living museum where the exhibits can pay for hotel rooms, massages, retreats, meals, art, and experiences. A tiny cathedral of liquidity. Money literacy machine disguised as art and utility.

**Positioning line (use everywhere):**
> Fi-art does not manufacture money. It manufactures symbolic notes, capacity claims, collectible art, and redeemable access instruments.

---

## 1. The core loop

```
FIAT → MIRROR NOTES → FI-ART MARKET → {ART · CAPACITY · ACCESS notes}
     → value circulates inside system → EXIT via Art Holders
```

Cash does not need to leave every time value moves. It stays in the reserve layer while real-world usefulness moves through notes.

| Stage | What happens |
|---|---|
| 1 | User brings fiat |
| 2 | User receives Mirror Note (fiat-linked) |
| 3 | Mirror Note buys Capacity / Art / Access notes |
| 4 | Value circulates inside system (trade / gift / use) |
| 5 | User redeems capacity, collects art, trades note, **or** exits to fiat through an Art Holder |

---

## 2. The four note types

| Type | What it is | Redeemable for | Risk | Best use |
|---|---|---|---|---|
| **Open Fi-art** | Anyone-created symbolic money art | Nothing unless stated | Low | Education, satire, culture, collectibles |
| **Mirror Note** | NFT mirror of real fiat/reserve value | Fiat/cash or equivalent | High | Liquidity entry & exit |
| **Capacity Note** | Claim on unused real-world capacity | Hotel night, retreat, massage, dinner, session | Medium | Turning idle capacity into liquid value |
| **Art Note** | Physical/digital art object, possibly using fiat imagery | The art object, not cash unless stated | Medium | Auctions, collecting, cultural value |
| **Access Note** | Membership / event / community privilege | Entry, club, privileges | Medium | Community value |

**The sacred distinction:**
- Anyone can make Fi-art.
- Only **verified** participants can make **redeemable** Fi-art.
- Only **approved liquidity stewards** (Art Holders) can support fiat exits.

---

## 3. The three creator tiers

### Tier 1 — Open Fi-art
Anyone mints symbolic/educational art.
**Label:** `Art only. Not redeemable. Not legal tender. No reserve claim.`
Use: satire, oversized notes, "money as myth", visual essays, cultural commentary.

### Tier 2 — Verified Fi-art
Creator passes basic checks: identity, art ownership, currency-image compliance, no counterfeit-like designs, no misleading financial language.
**Label:** `Verified creator. Art ownership attested. No cash redemption unless stated.`
Use: marketplace listings, limited editions, gallery collections, educational drops.

### Tier 3 — Redeemable Fi-art
Strictest. Work redeems for fiat, capacity, access, or a physical object.
**Label:** `Redeemable for: [thing]. Backed by: [reserve/capacity]. Terms: [rules].`
Use: Mirror Notes, Capacity Notes, retreat/hotel/service notes, physical art claims.
> Redemption promises are where poetry becomes plumbing — this tier requires diligence.

---

## 4. The Truth Panel (the education engine)

**Every Fi-art note displays this. Mandatory from Phase 2; shown on Open notes too (most fields "n/a").**

```
FI-ART TRUTH PANEL
─────────────────────────────────────────
Type:            Open / Mirror / Capacity / Art / Access
Redeemable:      Yes / No
Redeemable for:  $100 / 1 hotel night / 1 massage / artwork / membership / nothing
Backed by:       fiat reserve / merchant capacity / physical art / creator promise
Who must honor:  creator / merchant / art holder / reserve partner
Expiration:      none / date / booking window
Transferable:    yes / no / restricted
Exit path:       burn-to-redeem / book service / claim physical object / no exit
Risk label:      art-only / creator-backed / capacity-backed / reserve-backed
Legal status:    not legal tender
Educational theme: what this piece teaches about money
─────────────────────────────────────────
```

It trains every user to ask: **What backs this? Who owes performance? What can I redeem? What can fail? What is value here?**

This is monetary literacy through use, not lectures.

---

## 5. Redemption Confidence Stack (reserve & vouch layer)

| Tier | Layer | Meaning |
|---|---|---|
| 1 | Primary reserve | Actual fiat, cash, or custodied fund |
| 2 | Issuer stake | Creator/provider has skin in the game |
| 3 | Funded vouches | Backers lock collateral |
| 4 | Mutual reserve pool | Community backstop |
| 5 | Recovery / impaired | If redemption cannot be honored |

**Vouch types — what counts as backing:**

| Vouch | Counts as backing? | Meaning |
|---|---|---|
| Social vouch | **No** | "I trust this person." |
| Funded vouch | **Yes** | "I locked value to back this promise." |
| Capacity vouch | Sometimes | "I can provide replacement capacity." |
| Reserve vouch | Yes, if verified | "I hold actual redeemable liquidity." |

Hard rule: a social vouch may never display as redemption backing in the Truth Panel.

---

## 6. The Creator Covenant (signed before minting)

Plain language, signed once per creator, version-stamped:

> - I created this work or have rights to use it.
> - I am responsible for my art, claims, imagery, and redemption promises.
> - I will not create counterfeit-like currency or imply government endorsement.
> - I will not promise cash redemption, yield, profit, or reserve backing unless verified.
> - If this note represents capacity, I will honor the listed service or replacement terms.
> - If my work violates rules, it can be removed, frozen, delisted, or marked impaired.

**The clean rule:** The platform provides the rails and labels. The creator owns the art and the claims. The system makes the truth visible.

---

## 7. Platform guardrails (the curated protocol)

Open enough to create, strict enough around money-claims. See `COMPLIANCE.md` for full detail. Summary:

- **US currency imagery** — color illustrations must be one-sided, below ¾ or above 1½× the real item's linear size, production files deleted/destroyed after final use; BEP restricts currency likeness in advertising.
- **Physical art using real bills** — no cutting/cementing/perforating with intent to render unfit for reissue (18 U.S.C. § 333).
- **User uploads** — real DMCA takedown system; designate a registered DMCA agent (§512 safe harbor); keep it current.
- **Money-claims** — automated scan blocks "yield / profit / guaranteed / reserve-backed / cash redemption" language on non-verified notes.
- **Every note** — `not legal tender` stamped, no government-endorsement implication.

---

## 8. The capacity unlock (the most practical engine)

```
UNDERUSED CAPACITY (empty rooms, open slots, unsold retreat seats,
   unused venues, available artist time, wellness services)
      → MINT CAPACITY NOTES (clear redemption terms)
      → SELL in Fi-art Market (paid w/ Mirror Notes or Fiart Credits)
      → CAPACITY BECOMES LIQUID
      → user can redeem / trade / gift / bundle / auction
```

**Example:** Hotel has 20 empty rooms → mints 20 "Night Stay Notes" → users buy with Fi-art liquidity → hotel fills rooms → users get real value → the note is tradable before redemption.

**The alchemy:** unused capacity becomes a circulating asset. This is the Zen Village bridge — retreat seats, Camp Zen sessions, massage/wellness slots become Capacity Notes.

---

## 9. Launch sequence (build capacity before cash)

| Phase | What ships | Legal density |
|---|---|---|
| **1** | **Open Fi-art Gallery** — anyone mints art-only notes, no redemption claims | Low |
| **2** | **Verified Creator Layer** — guidelines + mandatory Truth Panels | Low-Med |
| **3** | **Capacity Notes** — hotels, retreats, therapists, venues, artists mint redeemable capacity | Medium |
| **4** | **Mirror Notes** — fiat-linked liquidity with proper reserve partners | High |
| **5** | **Vouches + Mutual Credit** — social trust, funded backstops, liquidity graph | High |
| **6** | **Art Holder Network** — trusted liquidity stewards provide fiat exits | High |

> Build capacity (Phase 3) before cash redemption (Phase 4). More useful, more differentiated, less legally dense.

---

## 10. The mantras (brand voice)

```
Art creates attention.
Capacity creates substance.
Reserves create trust.
Vouches create credibility.
Redemption creates reality.
Education creates legitimacy.
```

Sub-mantra for the loop:
> Creators make the art, merchants back capacity, art holders provide liquidity, collectors circulate value, and the platform makes the truth visible.

---

## Companion specs
- `DATA_MODEL.md` — note schema, Truth Panel fields, creator/verification tables, vouch & reserve records
- `ROADMAP.md` — Phase 1 build scope, milestones, what's in/out of v1
- `COMPLIANCE.md` — currency-imagery rules, §333, DMCA, money-claim scanner
