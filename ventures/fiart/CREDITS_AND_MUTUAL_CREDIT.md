# Fi-art — Credits & Mutual Credit (substrate integration)

Companion to `SITE_SPEC.md`. The finding: **Fi-art should not invent its credit/vouch/reserve layer — the FPAI ecosystem already has a battle-tested mutual-credit substrate, and its live rail runs on the same server as fiart.org (198 / zen-host).** This doc maps that substrate into Fi-art and lists what to add to the site.

> Sources: CORA "Coherent Credits" protocol v0.1.1 (`~/.config/fpai/coherent_credits_bank/`), Sunheart Reserve, System Capacity Formula, Trust Index, Relational Credit, Barter Chain (FPOS vault `05_CONCEPTS/Treasury`), live `fp-credits-gateway` (`SERVICES/fp-credits-gateway/SPEC.md`), CORA probe rewards (`core/STATE/CORA_PROBE_REWARDS.md`).

---

## 1. The headline — ride the rail, don't reinvent

`fpai-credits-gateway` is **already live on 198.54.123.234** (the same box now serving fiart.org). It's a unified multi-currency ledger: `/balance`, `/credit`, `/debit`, `/transfer`, `/exchange`, `/transactions`, immutable audit, WebSocket balance push. Exchange config already supports FP Credits ↔ CORA Credits ↔ USD.

**→ Fiart Credits should be a registered currency in that existing gateway, not a new ledger.** This is the dual-sovereignty win from NORTH_STAR: own currency, own value circulation, minimal extraction — and the rail already exists.

## 2. What a Fiart Credit IS (language discipline)

Borrow the **UC Credits** framing: a Fiart Credit is a **service/access credit**, pegged, closed-loop. Never "currency," never "investment," never "security."
- **Peg:** 1 FC = $X art-value, read live from the gateway (never hardcoded).
- **Closed-loop:** redeemable for art, capacity, access — not fiat (until Mirror/Phase 5).
- **Copy line:** *"A Fiart Credit is a redeemable note for art and access — not currency, not legal tender."*

This keeps Fiart Credits outside money-transmission/securities the same way the whole note system stays "not legal tender."

## 3. Mutual credit = the apex of the Truth Panel mission

Fi-art's whole pitch is teaching "what backs value." **Mutual credit is the deepest lesson in that curriculum** — value can clear through community trust and offsetting obligations *before* any fiat moves. Three FPAI mechanics make this concrete and teachable:

- **Barter Chain** — real exchanges complete along a chain (massage → meal → ride → art) and clear with zero fiat; currency only closes residual gaps. → Fi-art capacity notes can clear peer-to-peer before anyone cashes out. This IS SPEC §1's "value circulates inside the system before cashing out."
- **Mutual Reserve Pool** — Tier 4 of Fi-art's existing Redemption Confidence Stack (SPEC §5). The community backstop. Already in the spec; now it has a real mechanism behind it.
- **Funded/Reserve vouches** — Fi-art already separates social (no backing) from funded/reserve (real backing). This is exactly the CORA "Ponzi-distinguisher": **new credit enters only against verified value, never against signup/referral.**

## 4. The guardrail trio → Fi-art's Trust Center

CORA's automated circuit-breakers map 1:1 onto Fi-art's Trust Center (SPEC §14, the "glass floor"). Adopt these as the public transparency metrics for redeemable notes:

| CORA guardrail | What it measures | Fi-art Trust Center metric |
|---|---|---|
| **BCI** — Backing Coverage Index | liquid+yield reserve ÷ credits outstanding | **Reserve coverage ratio** for Mirror Notes |
| **CRBR** — Customer-Revenue Backing Ratio | real-purchase share of all credits issued (>50% healthy) | **% of credits backed by real art/capacity sales** (vs promo) |
| **PCR** — Physical Capacity Ratio | monthly redemption capacity ÷ issuance | **Capacity fulfillment ratio** — can providers honor outstanding notes? |
| **Trust Index** (0–1) | treasury + commons + participation health | **System health band** (generous / balanced / conservative / frozen) |

Band-based action is automatic: e.g. PCR < 0.7 → cap new capacity-note minting (prevents a soft bank-run on retreat seats). These belong on a public `trust.html`.

## 5. Backing math — Sunheart Reserve + System Capacity Formula

For any reserve-backed Fi-art (Mirror Notes, Mutual Reserve Pool), adopt:
- **Sunheart Reserve split:** 70% deep reserve (never sold) · 25% yield-producing · 5% operational buffer. Only yield funds ops. Quarterly published audit.
- **System Capacity Formula:** `Available = (Resources − Reserved − Committed) × 0.8 safety × sustainability`. Never issue more redeemable Fi-art than this. Directly prevents PCR failure.

## 6. Trust scoring → the vouch + provider layer

- **Relational Credit (0–10)** for creators/providers/collectors — fulfillment, communication, honoring pricing, honoring boundaries. Modulates access to limited drops + private collections. Fi-art already has "Fulfillment Score" in the provider dashboard (SPEC §10) — make it the public Relational Credit.
- **High score expands access; low contracts it.** Ties redemption confidence to behavioral history, not just collateral.

## 7. Earned vs purchased credits (dual ledger)

Mirror Zen Village's two-ledger model:
- **Purchased Fiart Credits** — patrons buy them (gift-card style, supporter tiers à la CORA Nation Front Door: Citizen/Patron/Founding Patron).
- **Earned Fiart Credits** — creators curate/mentor/refer; viewers engage deeply (CORA probe-reward template: +credits for meaningful engagement, idempotent, closed-loop). Referral pays credits **only on real purchase/mint, never signup** (FTC-safe).

---

## What to ADD to the site (prioritized)

1. **★ Learn module: "What is a Fiart Credit?" + "What is mutual credit?"** — credits are currently an unexplained price unit. This is the single highest-value gap: the site's whole function is money literacy, and its own internal currency is the perfect live lesson. *(Shipping now.)*
2. **★ Trust Center page (`trust.html`)** — the "glass floor": Backing Coverage, Capacity Fulfillment, Reserve Coverage, System Health band, Relational Credit. Phase-1 figures labeled as illustrative until the gateway feeds live data. *(Shipping now.)*
3. **Wire Fiart Credits to `fpai-credits-gateway`** — register FC as a currency; read peg live; balances via the existing API. (Backend task — spec'd here, build when the wallet layer lands.)
4. **Mutual Reserve Pool surfacing** — show Tier-4 community backstop in the Truth Panel's "Backed by" when applicable.
5. **Barter/clearing view** — "value circulating inside the system" visualized: how a capacity note can clear peer-to-peer before fiat. (Phase 4, with the vouch graph.)
6. **Relational Credit badge** on creator/provider profiles — public fulfillment score. (Phase 2.)

---

## The one-line synthesis
Fi-art's "what backs value?" mission and the FPAI mutual-credit substrate are the same project seen from two ends: **Fi-art is the public, teachable face of the sovereign credit economy.** The notes teach what backs value; the credits *are* value backed by real art, capacity, and community trust — circulating with minimal off-ramp, exactly the NORTH_STAR economic-sovereignty goal.
