# Fi-art — Site Spec v0.1 (canonical build doc)

Authoritative site/product spec. Supersedes the data-model sketch in `DATA_MODEL.md` (kept as v0 reference); concept north-star lives in `SPEC.md`; phasing in `ROADMAP.md`; legal detail in `COMPLIANCE.md`.

> ⚠️ Knowledge cutoff Jan 2026 — regulatory cites (FinCEN, OCC, SEC/CFTC, BEP, §333) are pointers, not legal advice. Counsel review gates Phase 3 (capacity) and Phase 5 (Mirror/cash).

---

## Product thesis
Fi-art is a marketplace + learning system where money-inspired art becomes a bridge into real-world capacity. The site lets people:
1. Create symbolic Fi-art.
2. Buy, sell, gift, collect, redeem Fi-art notes.
3. Turn underused real-world capacity into tradable notes.
4. Learn what backs value: cash, capacity, trust, art, reputation, or belief.
5. Exit into fiat through verified liquidity stewards when appropriate.

**Core principle:** Anyone can create Fi-art · verified creators can create *redeemable* Fi-art · approved liquidity stewards can support fiat exits.

---

## 1. Site identity
- **Name:** Fi-art
- **Tagline:** Art that teaches money and unlocks real-world value.
- **Positioning:** Fi-art transforms fiat-inspired art into collectible, redeemable, and capacity-backed notes.
- **Tone:** Elegant, playful, trustworthy — museum-meets-marketplace. Not crypto casino, not new bank, not fake money. A living museum of value where the exhibits can be used.

## 2. Core site structure
```
Home
├── Explore Marketplace → Open · Capacity · Art · Access · Mirror
├── Create → Mint Open · Mint Capacity · Mint Physical Art · Apply Redeemable Creator
├── Redeem → Redeem Capacity · Claim Physical Art · Cash Exit · Redemption History
├── Learn → What Backs Money? · Fiat as Art · Cash vs Capacity · Risk Labels · Creator Guidelines
├── Trust Center → Reserve Status · Capacity Fulfillment · Art Holder Profiles · Vouch Graph · Redemption Metrics
└── Dashboard → Collector · Creator · Capacity Provider · Art Holder · Admin Console
```

## 3. User roles
Visitor · Collector · Open Creator · Verified Creator · Redeemable Creator · Capacity Provider · Art Holder / Liquidity Steward · Backer / Voucher · Admin / Trust Operator. (Permissions per role detailed in original brief; enforced in role table §18.)

## 4. Note taxonomy
| Type | Redeemable | Redeemable for | Backed by | Risk label |
|---|---|---|---|---|
| **Open Fi-art** | No | Nothing unless stated | Artistic/cultural value | Art-only |
| **Capacity Note** | Yes | Service, stay, experience, ticket, session, access | Provider capacity | Capacity-backed |
| **Art Note** | Maybe | Physical/digital art, certificate, installation, print | Artwork + creator promise | Art-backed / creator-backed |
| **Access Note** | Yes | Membership, event, credential, gated experience | Platform/creator access | Access-backed |
| **Mirror Note** | Yes | Fiat/cash/equivalent | Verified reserve / liquidity steward | Reserve-backed |

- **Open** label: `Art only. Not redeemable. Not legal tender. No reserve claim.`
- **Capacity** required fields: provider · service desc · location · booking window · expiration · blackout dates · transferability · cancellation · replacement · redemption method.
- **Art Note:** the NFT represents ownership/claim to the artwork, **not** cash redemption.
- **Mirror Note:** strictest controls. FinCEN CVC guidance separates ordinary users from administrators/exchangers (money-transmitter rules); OCC/Treasury stablecoin rulemaking treats payment-stablecoin issuance as regulated. Counsel gate.

## 5. Homepage
- **Hero headline:** "Money is already art. Fi-art makes it usable."
- **Sub:** Create, collect, and redeem money-inspired art backed by real-world capacity, physical artwork, community trust, or verified reserves.
- **Buttons:** Explore Notes · Create Fi-art · Learn How It Works.
- **Hero visual:** Fiat → Mirror Note → Capacity Note → Real-world experience (branch → Art Note → Cash exit).
- **Sections:** (1) How it works — 3 cards · (2) Explore note types — 5 cards each showing redeemable?/backed-by/risk/example · (3) The Truth Panel — live sample · (4) Capacity marketplace — hotels/retreats/massages/dinners/studio/commissions/tickets · (5) Learn while using · (6) Creator invitation ("Create art. Attach truth. Let value move.").

## 6. Marketplace
- **Tabs:** All · Open · Capacity · Art · Access · Mirror · Featured Drops · Local Capacity · Ending Soon · Recently Redeemed.
- **Filters:** note type · redeemable y/n · redemption type · location · date window · price · creator · provider · risk label · reserve coverage · transferability · expiration · verified-only · physical/digital · auction/fixed.
- **Card:** thumbnail · title · note type · price · redeemable-for · risk label · creator/provider · verification badge · expiration/booking window · reserve/capacity confidence indicator.

## 7. Note detail page
Gallery wall + financial nutrition label. Left = media; right = price / Buy·Bid·Redeem·Gift·Transfer / Truth Panel / risk label / creator profile.
Sections: **A** Artwork (media, edition, creator, desc, educational theme) · **B** Truth Panel · **C** Redemption box (capacity → book/dates/terms; art → claim/shipping/custody/certificate; mirror → cash eligibility/reserve/fees/limits/window/identity) · **D** Provenance (mint, ownership history, transfers, redemptions, price history, vouches, impairment) · **E** Education capsule (one money idea per note).

## 8. Truth Panel (the heart)
**Universal fields:** Note ID · type · creator · verified status · redeemable y/n · redeemable for · cash redeemable y/n · backed by · who must honor · transferable · expiration · jurisdiction limits · risk label · dispute path · legal status · educational theme.
**Backing types:** none · creator promise · physical art · provider capacity · access rights · fiat reserve · funded vouch · mutual reserve pool · mixed.
**Risk labels:** art-only · creator-backed · capacity-backed · access-backed · physical-art-backed · reserve-backed · partially-backed · over-collateralized · impaired · redeemed · expired.
**Mandatory warning logic:** not-redeemable → "art-only, no redemption claim" · capacity → "redeemable only for listed good/service, not cash unless stated" · mirror → "subject to reserve terms, eligibility, fees, verification" · expired → disable purchase (unless collectible-after-expiry) · impaired → impairment banner + recovery status.

## 9. Creator Studio
**Onboarding:** account → choose creator type → accept Covenant → profile → upload art → choose note type → complete Truth Panel → compliance checks → preview → mint/list.
**Minting flow (8 steps):** upload → note type → story+educational theme → redemption status → backing details → compliance checklist → preview Truth Panel → submit/publish.
**Compliance wizard questions:** Did you create this? · rights to all materials? · includes real currency imagery? · resembles a real bill? · one-sided? · intentionally over/undersized? · uses words like legal tender/Federal Reserve/Treasury/banknote/guaranteed/yield/investment? · promises cash redemption? · promises a good/service? · who fulfills? · what if fulfillment fails?
**Creator Covenant:** I created this/have rights · I'm responsible for art+claims+promises · no counterfeit-like currency · no implied government endorsement · not legal tender · no cash redemption unless approved · no promised profit/yield/appreciation · note may be delisted/frozen/impaired/removed if claims false or fulfillment fails.

## 10. Capacity Provider dashboard (the commercial wedge)
**Onboarding:** business profile · identity/business verification · service category · location · calendar/inventory connect · payout · fulfillment terms · cancellation · provider agreement.
**Modules:** Mint Capacity Note · Manage Inventory · View Bookings · Redemption Requests · Transfer/Trade Activity · Revenue · Fulfillment Score · Disputes · Provider Profile.
**Capacity Note builder fields:** service title · description · retail value · Fiart price · quantity · location · booking window · expiration · blackout dates · transferability · refund/replacement policy · redemption method · capacity proof · contact window.

## 11. Art Holder / Liquidity Steward dashboard (guarded vault door)
**Functions:** hold fiat reserves · hold physical art · provide Mirror-Note liquidity · back creators/notes · process redemptions · publish reserve status · build trust profile.
**Modules:** Reserve Overview · Outstanding Mirror Notes · Redemption Queue · Collateral/Vouches · Vaulted Art · Liquidity Limits · Settlement History · Trust Score · Compliance Status · Dispute Queue.
**Public profile:** name/entity · verification · total reserves supported · notes backed · redemption history · avg redemption time · failed redemptions · coverage ratio · vouched creators · supported providers.
**Redemption queue fields:** request ID · user · note ID · amount · eligibility · KYC status · reserve source · fee · status (pending/approved/paid/rejected/disputed) · timestamp.

## 12. Vouch system (separates social trust from financial backing)
| Vouch | Counts as backing? | Description |
|---|---|---|
| Social | **No** | "I trust this creator/provider." |
| Funded | **Yes** | Backer locks collateral for amount + period |
| Capacity | Sometimes | Another provider offers replacement capacity |
| Reserve | Yes, if verified | Steward backs redemption with verified reserve |

Flow: choose target → choose type → set amount/signal → duration → accept terms → lock collateral (if funded) → publish. **Hard rule: social vouches never count as reserve coverage.**

## 13. Redemption system
**Types:** capacity · physical art claim · access · cash exit · refund/replacement.
**Generic flow:** click Redeem → check ownership → check eligibility → check expiration/status → confirm terms → request created → honoring party notified → status updates → note burned/redeemed/partial → receipt.
**Statuses:** available · pending · scheduled · redeemed · partially-redeemed · expired · disputed · impaired · cancelled · replaced.
**Cash exit gating:** by jurisdiction · identity status · limits · approved liquidity partners. (FinCEN prepaid-access: closed-loop for goods/services; ~$2,000/device exclusion for certain closed-loop; gift-card min-expiration + fee limits may apply to capacity-style credits.)

## 14. Trust Center (public — glass floor under the marketplace)
**Pages:** System Overview · Reserve Status · Capacity Fulfillment · Redemption Metrics · Art Holder Profiles · Creator Verification · Vouch Graph · Dispute/Impairment Log · Policy Library.
**Reserve dashboard:** outstanding reserve-backed obligations · verified reserve amount · coverage ratio · reserve holder · last attestation · eligible jurisdictions · redemption limits.
**Capacity dashboard:** active providers · active capacity value · redeemed value · booking completion rate · provider response time · disputes by category.

## 15. Learn section (money-literacy museum)
Modules: What is fiat? · Why money is symbolic · What backs a dollar? · What backs a Fi-art note? · Cash vs capacity backing · What is redemption/reserve/vouch? · What can fail? · How to read a Truth Panel · How creators should use currency imagery.
Each page: short explanation · visual diagram · real Fi-art example · risk lesson · action step.

## 16. Compliance & policy architecture
**Required public pages:** ToS · Privacy · Creator Covenant · Provider Agreement · Art Holder Agreement · Redemption Terms · Risk Labels · Currency Imagery Guidelines · IP/Copyright · DMCA · Prohibited Content · Dispute Resolution · KYC/Eligibility · Fees · Tax Info.
**Prohibited creator phrases** (unless approved regulated structure): legal tender · government-backed · Federal Reserve note · guaranteed profit/appreciation · risk-free · earn yield · interest · deposit · bank account · cash equivalent.
**Currency imagery:** BEP rules — one-sided · size restrictions (<¾ or >1½×) · delete/destroy reproduction files after final use.
**Securities posture:** separate collectible art / digital tools / access instruments / capacity claims / reserve-backed notes (SEC-CFTC Mar-2026 taxonomy; surrounding transaction + rights matter).
**Stablecoin/MT posture:** Mirror Notes highest-friction → approved regulated partners or structured compliance path (FinCEN CVC + Treasury/OCC stablecoin rails). Full detail in `COMPLIANCE.md`.

## 17. Technical architecture
**Stack:** Next.js/React · Node or Python FastAPI · PostgreSQL · append-only double-entry ledger · S3-compatible storage · EVM L2 (low-fee) · ERC-721 unique / ERC-1155 editions+capacity batches · Meilisearch/Typesense/Elastic · card/ACH partner + later crypto wallet · KYC/KYB provider for restricted roles · calendar/inventory booking integrations · internal admin dashboard · product + trust analytics.
**★ Storage rule:** use compliant stylized currency images; do NOT push non-compliant high-res currency reproductions to immutable/decentralized storage — currency-image rules may require deletion of source files after final use.
**Modules:** User · Creator · Note Minting · Marketplace · Ledger · Redemption · Capacity Booking · Vouch · Trust Score · Compliance Review · Notification · Dispute · Admin.

## 18. Data model (canonical — supersedes DATA_MODEL.md sketch)
- **User:** id · name · email · wallet_address · role · verification_status · jurisdiction · created_at · risk_flags
- **Creator Profile:** user_id · display_name · bio · verification_tier · creator_covenant_signed_at · social_links · portfolio · compliance_status
- **Note:** id · token_id · chain · title · description · note_type · creator_id · current_owner_id · media_url · metadata_url · edition_size · status · price · currency · redeemable · redemption_type · risk_label · transferable · created_at
- **Truth Panel:** note_id · redeemable · redeemable_for · cash_redeemable · backing_type · backing_source_id · honoring_party_id · expiration_date · jurisdiction_limits · transfer_rules · dispute_path · legal_status_label · educational_theme
- **Capacity Offer:** id · provider_id · service_type · description · location · quantity · retail_value · fiart_price · booking_window_start · booking_window_end · blackout_dates · expiration_date · cancellation_policy · replacement_policy
- **Reserve:** id · art_holder_id · reserve_type · reported_amount · verified_amount · currency · coverage_limit · attestation_date · status
- **Vouch:** id · voucher_id · target_type · target_id · vouch_type · amount · collateral_asset · start_date · end_date · status · counts_as_backing
- **Redemption Request:** id · note_id · requester_id · redemption_type · status · requested_at · approved_at · fulfilled_at · provider_id · art_holder_id · payout_method · booking_details · dispute_id
- **Transaction Ledger:** id · from_account · to_account · asset_type · amount · note_id · transaction_type · status · created_at · reference_id

## 19. Smart contract requirements
**Functions:** mintNote · mintBatch · transferNote · burnForRedemption · markRedeemed · markImpaired · markExpired · updateMetadataPointer · lockVouchCollateral · releaseVouchCollateral · slashVouchCollateral.
**Principles:** every token has a note type · redeemable notes point to redemption terms · burn/redeem permanent · impaired status visible · metadata changes auditable · cash-like notes have transfer controls if required.
**On-chain:** ownership · transfers · minting · burn/redemption events · impairment flag · token URI · vouch collateral events (if crypto-native).
**Off-chain:** KYC/KYB · reserve details · provider scheduling · dispute evidence · payment rails · physical custody · private user data · compliance review.

## 20. Admin console
**Queues:** creator verification · redeemable-note approval · currency-imagery review · capacity-provider review · art-holder review · dispute · impaired note · suspicious activity · takedown.
**Actions:** approve/reject creator · approve/delist note · freeze transfers · mark redeemed/impaired/expired · resolve dispute · update risk label · request info · suspend account · export report.
**Review flags:** possible counterfeit-like imagery · misleading cash claim · unverified redemption promise · copyright/IP · expired capacity · provider non-response · reserve mismatch · suspicious transfer pattern.

## 21. Launch sequence
1. **Museum + open creation** — home, Learn, Open mint, open marketplace, Truth Panel v1, Covenant, admin review. (No cash redemption, no Mirror Notes, no funded vouches, no secondary trading of redeemable notes.)
2. **Capacity marketplace** — provider onboarding, Capacity mint, booking/redemption, provider dashboard, fulfillment metrics, disputes. *First serious commercial wedge.*
3. **Art Notes + physical claims** — custody status, claim/shipping, certificates, auctions, installation profiles.
4. **Vouch graph** — social/funded vouches, reputation, collateral locks, vouch display on Truth Panel.
5. **Mirror Notes + cash exits** — only with partner structure: art-holder verification, reserve dashboard, cash redemption, KYC/KYB, jurisdiction gating, attestations, limits.

## 22. MVP scope
**Must have:** Homepage · Marketplace · Note detail · Truth Panel · Creator Studio (Open) · Capacity Note flow · Provider onboarding · Basic redemption · Collector dashboard · Creator dashboard · Admin review console · Learn · Trust Center v1.
**Not yet:** open cash redemption · fractional reserve · holder yield · complex mutual credit · permissionless Mirror issuance · unreviewed currency scans.
**★ MVP north star:** Can a user understand what a note is, what backs it, and how to use it within 30 seconds?

## 23. Key user flows
- **A — Buy Capacity Note:** explore → filter location/service → detail → read Truth Panel → buy → receive → book → provider confirms → redeem → marked redeemed.
- **B — Mint Open Fi-art:** account → Covenant → upload → choose Open → Truth Panel → compliance checklist → preview → mint/list.
- **C — Provider mints capacity:** apply → verify → create offer → set terms/quantity → submit for approval → mint → sell/redeem.
- **D — Claim physical art:** buy Art Note → detail → Claim Physical Art → confirm shipping/custody → admin/creator fulfills → NFT marked claimed or ownership stays linked.
- **E — Exit to fiat:** hold eligible Mirror Note → Redeem → eligibility check → payout request → art holder approves → note burned/redeemed → fiat payout recorded → receipt.

## 24. Design system
**Visual language:** gallery white space · banknote textures · fine-line engraving · receipts · vault glass · museum placards · ledger grids · soft metallic accents.
**UI motifs:** Truth Panel = financial nutrition label · note card = gallery object · Trust Center = transparent vault · Learn = illuminated manuscript for money · capacity marketplace = travel/wellness/experience marketplace.
**Badges:** Art-only · Verified Creator · Capacity-backed · Reserve-backed · Funded Vouch · Social Vouch · Redeemable · Not Cash Redeemable · Expired · Redeemed · Impaired.

## 25. Copy rules
**★ The framing law (James 2026-06-25): never globally say "Fi-art is not money" — too broad.** Say instead: *"Fi-art is not legal tender. Some Fi-art notes are art-only. Some are redeemable claims. Always read the Truth Panel."*

**The sell-vs-redeem distinction is the whole spellbook:**
- *Sell the note* → a collector/steward buys art at an agreed price = **less money-like**.
- *Redeem the note* → issuer/reserve owes a fixed thing or $X = **much more money-like** (claim / voucher / stored-value / stablecoin-like depending on structure). Framing it as art does not erase that.

**Global legal strip:** `NOT LEGAL TENDER. READ THE TRUTH PANEL.` + "Some Fi-art is art-only. Some is redeemable for capacity, access, physical art, or fiat through listed terms."

**Per-type card legal line:**
| Type | Line |
|---|---|
| Open | Art-only. Not redeemable. Not money. |
| Capacity | Redeemable for listed service. Not cash. Not legal tender. |
| Art | Claim to artwork. Not legal tender. Cash value not guaranteed. |
| Access | Redeemable for listed access. Not cash. Not legal tender. |
| Mirror | Redeemable claim. Reserve-backed. Not legal tender. Subject to terms. |

**Say:** redeemable for listed capacity · backed by provider capacity · art-only · not legal tender · Truth Panel · reserve-backed · creator promise · capacity-backed · cash exit subject to terms.
**Avoid:** "not money" (globally) · legal tender · guaranteed return/appreciation · risk-free · earn yield · banknote · deposit · Federal Reserve · government-backed · cash equivalent.

**The final mantra:**
```
Art-only notes are culture.
Capacity notes are usable value.
Art notes are ownership claims.
Mirror notes are guarded cash claims.
None are legal tender.
Only some are redeemable.
The Truth Panel decides.
```
> Money itself is symbolic art — but redemption determines financial reality. The brand can be playful; the mechanics must be sober.

## 26. Acceptance criteria (MVP ready when)
- User instantly distinguishes Art-only / Capacity-backed / Reserve-backed.
- No redeemable note publishes without redemption terms.
- No cash-redeemable note lists without approved reserve/liquidity config.
- Every note has a Truth Panel + a risk label.
- Every redemption creates an auditable event.
- Expired capacity notes can't be bought as redeemable.
- Impaired notes are visibly marked.
- Creators must accept responsibility before minting.
- Admins can freeze/delist/mark impaired.
- Users learn what backs each note without reading legal docs.

## 27. Core metrics
- **Marketplace:** gross volume · notes minted · active creators · active providers · capacity sold · capacity redeemed · repeat buyers.
- **Trust:** redemption success rate · avg redemption time · provider fulfillment rate · dispute rate · impaired rate · reserve coverage ratio · vouch-backed amount.
- **Education:** Truth Panel views · Learn completions · creator-guideline completions · comprehension quizzes.
- **Capacity impact:** unused capacity converted · hotel nights filled · retreat seats filled · service hours booked · local provider revenue generated.

## 28. Build mantra
```
Make art open.
Make redemption clear.
Make capacity useful.
Make cash exits guarded.
Make trust visible.
```
Every note must answer: What is this? Who made it? What backs it? Can I redeem it? For what? From whom? What can fail? How do I exit?
