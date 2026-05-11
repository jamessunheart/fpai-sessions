# Brand Tokenization Architecture v0.1

**Status:** DRAFT — failed first legal critique (3 CRITICAL issues). Do NOT ship as written. See companion critique doc `BRAND_TOKENIZATION_ARCHITECTURE_v0.1_critique.md`.
**Drafted:** 2026-05-11
**Council pass 1:** The Counsel (legal-critic at brain.sunheart.com/legal/) on 2026-05-11
**Next:** v0.2 redesign per critique fixes, then Cursor/GPT/Gemini council passes, then human counsel sign-off

---

## Goal

Multi-brand cooperative with cross-redemption inside the CORA Nation 508(c)(1)(A) + Sunheart Trust legal stack. Each Brand operates with substantial autonomy. The Communal Treasury holds diversified equity in all Brands and issues Village Credits backed by total value.

## Architecture (as drafted)

```
COMMUNAL TREASURY (CORA Nation 508c1a + Sunheart Trust)
├── Cash + crypto + bullion + property
├── EQUITY stakes in every Brand
└── Issues Village Credits ← claims on total value

BRAND A (e.g., Cheyenne/Sapphire)
├── Substrate (bot, site, story)
├── Issues Brand A tokens
├── Equity splits: 70% Steward / 30% Communal *(❌ critiqued — see issue 2)*
└── Token holders rights:
    - Brand-specific services
    - Pro-rata revenue distribution *(❌ critiqued — see issue 1)*
    - Cross-redemption to Village Credits at Communal NAV *(❌ critiqued — see issues 1, 4)*

STEWARD A's PERSONAL TRUST
├── Their own Brand A tokens
└── Optionally other Brand tokens (cross-investment)
```

## Token mechanics (as drafted)

- ERC-20 style on credit-gateway (off-chain ledger today, on-chain optional later)
- Cap table per Brand maintained on the gateway
- **No public secondary market** — Member-to-Member transfer only ✅
- Member-gating: WPA signed + Character Card + Mirror paired ✅ (substantive — keep)

## Cross-redemption math (as drafted)

```
Village Credit NAV = (Communal Treasury Liquid + Communal Equity holdings)
                    / Village Credits outstanding
```

Brand token holder can redeem at Communal at current NAV.

## Mockumentary integration (as drafted)

- "The Village" daily mockumentary documents each Brand's evolution
- Audience growth → demand for Brand tokens + Village experiences *(❌ critiqued — see issue 3)*

---

## Legal critique summary (council pass 1 — The Counsel, 2026-05-11)

**Verdict:** Do not ship. Three CRITICAL issues require redesign before v0.2.

| # | Severity | Issue | Fix direction |
|---|---|---|---|
| 1 | 🔴 CRITICAL | Howey investment-contract structure (pro-rata revenue + NAV redemption + equity splits) | Redesign as pure utility token OR Coherent Credit mutual-credit model — no revenue distribution, no NAV redemption |
| 2 | 🔴 CRITICAL | Steward equity split = private inurement, endangers 508(c)(1)(A) | Replace with community-provision model (housing, meals, ceremony) per Coherent Treasury v0.10; arm's-length compensation via for-profit subsidiary if economic upside needed |
| 3 | 🔴 CRITICAL | Mockumentary as demand-generation = public offering signal, destroys Reg D exemptions and closed-community framing | Decouple — show documents the Village; doesn't promote token economics |
| 4 | 🟠 HIGH | Investment Company Act exposure (pooled NAV redemption) | Counsel must analyze 3(c)(1) or 3(c)(7) exemption; possibly cap members |
| 5 | 🟠 HIGH | FinCEN / state MTL stored-value risk via cross-redemption | Counsel must analyze closed-loop exemption boundaries |
| 6 | 🟠 HIGH | Reves test for note characterization (resolved by Issue 1 fix) | Same fix as Issue 1 |
| 7 | 🟡 MEDIUM | PMA doctrine does not immunize securities | Reframe member-gating as substantive religious requirement, not securities exemption |
| 8 | 🟡 MEDIUM | UBIT exposure on commercial Brand activity inside 508(c)(1)(A) | Each Brand needs substantially-related analysis OR operates via arm's-length for-profit subsidiary |
| 9 | 🟡 MEDIUM | Steward personal trust structure undefined | Define trust type; likely resolved by Issue 2 fix |

Full critique: `BRAND_TOKENIZATION_ARCHITECTURE_v0.1_critique.md` (next to this file).

---

## Direction for v0.2

Three architectural pivots required:

1. **Strip economic-return mechanics from Brand tokens.** Tokens grant access to Brand services (Sapphire readings, Camp Zen retreat beds, Halley's offerings, etc.). They do NOT distribute revenue. They do NOT redeem at NAV. Value = utility, not return.

2. **Replace equity-split with community-provision compensation for Stewards.** No personal-trust equity from 508(c)(1)(A) activity. Stewards receive housing, meals, ceremony, defined pastoral support. If economic upside required, structure as arm's-length compensation from for-profit subsidiary entities (e.g., Camp Zen LLC contracts with CORA Nation; CORA Nation does not directly fund Steward personal trusts).

3. **Sever Mockumentary from token demand-generation.** The show documents the Village's religious-community life. It does not promote token economics. Tokens (if any survive v0.2 redesign) are distributed inside the religious community to verified members for substantive religious-community participation, not in response to mockumentary audience demand.

---

## Open architectural questions for v0.2

- Do Brand tokens survive as a structural concept, or does Coherent Credit (already designed in v0.10 of Coherent Treasury) absorb their function entirely?
- If Brands need economic-upside vehicles for Stewards: separate for-profit LLCs (Sapphire LLC, Camp Zen LLC) contracting at arm's length with CORA Nation? Tax + governance implications?
- How does the Mockumentary's economic function get re-specced — as a documentary work (CORA Nation media ministry) rather than a demand-gen channel?
- Member-cap analysis: at what membership count does ICA 3(c)(1) exemption pressure require a different structure?
