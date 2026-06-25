# Fi-art — Roadmap & v1 Scope

Phasing per SPEC §9. Capacity before cash. Lowest legal density first.

---

## Phase 1 — Open Fi-art Gallery (v1, build first)

**Goal:** prove the teaching loop. A living museum of money-art. Zero redemption claims.

**In scope:**
- Public gallery — browse/scroll money-inspired art (the "tiny cathedral").
- Anyone connects + mints `type='open'` notes (art-only).
- **Truth Panel on every piece** (even Open — most fields show "n/a / not redeemable / art-only"). The panel is the product even at v1.
- Creator Covenant signing flow (one-time, version-stamped) — required before first mint.
- Money-claim language scanner on mint (blocks "yield/redeemable/guaranteed" on Open notes).
- Currency-imagery compliance notice + creator guide at mint time.
- `/dmca` page + designated agent + takedown action path.
- Educational-theme field surfaced prominently — each note is a tiny money lesson.

**Out of scope (later phases):** redemption, payments, reserves, vouches, fiat exits, verification beyond covenant.

**Done when:** a visitor can browse the museum, read any note's Truth Panel, understand what backs it (nothing, by design), and a creator can mint an Open note after signing the Covenant.

---

## Phase 2 — Verified Creator Layer
- Identity + art-ownership checks → `tier='verified'`.
- Truth Panels become mandatory + structurally enforced (no mint without complete panel).
- Marketplace listings, limited editions, gallery collections.
- Verification badge surfaced in Truth Panel "Who must honor."

## Phase 3 — Capacity Notes (the differentiator)
- Verified merchants (hotels, retreats, therapists, venues, artists) mint redeemable Capacity Notes.
- **Claims-only redemption** — platform records request + status; merchant honors off-platform. No fund custody.
- Booking-window + replacement-terms enforced in schema.
- **Zen Village is anchor merchant**: retreat seats, Camp Zen sessions, wellness slots → first real Capacity Notes.

## Phase 3b — Art Notes + physical claims
- Custody status, claim/shipping flow, certificates of authenticity, auctions, installation profiles.

## Phase 4 — Vouches + Mutual Credit (trust graph before cash)
- Social / funded / capacity / reserve vouches.
- Reputation, collateral locks, vouch display on Truth Panel, community backstop pool.

## Phase 5 — Mirror Notes + Cash Exits (Art Holder Network)
- Fiat-linked liquidity notes with formal reserve partners; approved liquidity stewards provide fiat exits.
- Money-transmitter / custody / stablecoin compliance gets real → **counsel review gate before launch.**
- Art-holder verification · reserve dashboard · KYC/KYB · jurisdiction gating · attestations · limits.

> Ordering matches SITE_SPEC §21: build the trust graph (P4) **before** cash exits (P5).

---

## Open decisions (defaults chosen — reversible, flag to change)

| Decision | Default chosen | Why |
|---|---|---|
| **Where it lives** | Standalone brand at `fiart.org`, sharing the brain/memory substrate; settles into Zen Village capacity | Map says standalone north star; Zen Village is the natural anchor merchant |
| **Chain vs off-chain v1** | Off-chain records (SQLite on brain substrate) for Phase 1–2; "NFT" as a display metaphor; chain-anchor optional at Phase 3+ | Ship the museum + Truth Panel without wallet friction; anchor when redemption demands provenance |
| **Redemption custody** | Claims-only through Phase 3 (no platform fund custody) | Keeps money-transmitter exposure off the table until Phase 4 |
| **Auth** | Reuse FP guide/brain auth rails where possible | Don't rebuild identity |

Change any default by saying so — none are locked.

---

## Next build step (when you say go)
Scaffold Phase 1: gallery page + mint form + Truth Panel component + Covenant gate + claim-scanner. Deploy target TBD (162 service or fiart.org standalone). Spec → scaffold is the next loop.
