# Fi-art — Compliance Guardrails

The platform is a **curated protocol**: open enough to create, strict around money-claims. "Artists are responsible" is true — but the platform still carries the rails, labels, and takedown duty. This file is the creator guide + the enforcement spec.

> ⚠️ Knowledge cutoff Jan 2026. This is product-design guidance, **not legal advice**. Get counsel review before Phase 3 (capacity) and Phase 4 (mirror/fiat) launches.

---

## 1. US currency imagery (Open / Art notes)
Color illustrations of US currency must follow conditions like:
- **One-sided** reproduction.
- Sized **below ¾** or **above 1½×** the real item's linear dimension.
- Production/digital files **deleted or destroyed** after final use.
- BEP also restricts using currency likenesses in **advertising**.

**Enforcement:** mint-time creator guide + checkbox attestation; flag uploads that look like full-size two-sided reproductions for review.

## 2. Physical art using real bills (Art notes)
Avoid cutting, cementing, perforating, or otherwise altering banknotes **with intent to render them unfit for reissue** — **18 U.S.C. § 333** (mutilation of national bank obligations).

**Enforcement:** physical-art listings carry a § 333 notice; creator attests no render-unfit-for-reissue intent.

## 3. User-generated uploads — DMCA (§512 safe harbor)
The Copyright Office: §512 safe harbors can shield qualifying online service providers from monetary liability for user infringement **when they cooperate with rights holders and meet conditions**. Providers hosting user material must **designate a registered DMCA agent** and **keep that info current**.

**Enforcement:**
- Register a DMCA agent; publish at `/dmca`.
- Real takedown pipeline → `dmca_actions` table (takedown / freeze / delist / impair / restore).
- Counter-notice path.

## 4. Money-claim language (all tiers)
No "yield / profit / guaranteed / APY / reserve-backed / cash redemption" on notes unless the creator is **verified + reserve-backed**.

**Enforcement:** automated scanner on `title` + `educational_theme` + `redeemable_for` at mint. Blocks the mint with an actionable message. Hard rule: a **social vouch never displays as redemption backing**.

## 5. Legal-tender + endorsement
- Every note stamps `not legal tender`.
- No implication of government endorsement.
- Framing discipline: "symbolic notes, capacity claims, collectible art, redeemable access instruments" — never "we manufacture money."

---

## Tier → diligence map
| Tier | Required checks |
|---|---|
| Open | Covenant signed · claim-scanner · currency-imagery notice |
| Verified | + identity · art-ownership attestation |
| Redeemable | + reserve/capacity record · honoring-party named · terms stated · (Phase 4 fiat) counsel review |

---

## The covenant carries the promise; the platform makes it visible
The creator owns the art and the claims. The platform owns the rails, the labels, the scanner, and the takedown duty. The Truth Panel makes every promise — and every risk — legible.
