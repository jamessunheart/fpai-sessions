# SOL Short Position — Trustee Prudent-Investor Documentation Memo

**Status:** DRAFT — for James (Trustee) review + decision
**Date:** 2026-05-11
**Trustee:** James Stinson (Sunheart Private Trust)
**Position:** BitTrue Short SOL, 1,000 contracts @ $91.42 entry, mark $95.85, hard stop $100, margin $32,045

---

## The issue (per Counsel critique 2026-05-11)

The 3x leveraged short SOL position is indefensible under the **prudent investor standard** (Uniform Prudent Investor Act, adopted in most US states) when held inside a charitable trust that supports a 508(c)(1)(A) religious community.

Even with a hard stop at $100 (capping max loss at ~$8,580), the position is:
1. **Speculative by design** — not income-generating, not preservation-oriented
2. **Leveraged** — 3x margin amplifies both gain and loss
3. **Held in a trust** that also holds the religious community's operational assets
4. **Inconsistent** with the same-day-adopted Treasury policy: *"Do not gamble with resources. Find sure wins. Get optimal yields."*

The Counsel was explicit: *"The Trust should not hold 3x leveraged derivatives. Pick one path today, document it in writing."*

---

## Decision required from Trustee

Choose ONE path and document:

### Path A: Close the position now
- **Action:** Issue close-position order on BitTrue immediately
- **Realized loss:** ~$4,462 (current unrealized P&L at mark $95.85)
- **Margin freed:** $32,045 redeployed per yield strategy (Pendle PT-sUSDe / sDAI / Aave per `reference_treasury_yield_strategy.md`)
- **Documentation:** "Position closed 2026-05-11 in alignment with Treasury Policy adopted same day. Realized loss documented. Margin redeployed to compliant yield vehicles."
- **Cost:** Realized $4,462 loss. Recovery via yield: ~5 months at 7% blended on the freed margin.
- **Benefit:** Eliminates the prudent-investor exposure immediately. Clean before-and-after narrative for any examiner. Establishes trustee discipline in adopting new policy.

### Path B: Transfer position to personal account
- **Action:** Close the position in the Trust account; if conviction is strong, James personally takes the position in a non-Trust account at fair value
- **Mechanics:** Document transfer at mark price ($95.85 for 1,000 SOL short, current margin $32k). Trust receives the equity value (margin + unrealized P&L); James personally takes over the position with his own margin.
- **Documentation:** "Position transferred 2026-05-11 from Sunheart Private Trust to James Stinson personal account at fair value. Trust no longer holds leveraged derivatives. Personal account holds position with personal margin."
- **Cost:** Same $4,462 unrealized loss reflected in transfer pricing. Trust gets back its margin minus loss.
- **Benefit:** If James has high conviction on the position, retains exposure outside the Trust. Trust is cleaned up. Tax basis documented.
- **Risk:** If James does not want the personal financial exposure of running a 3x leveraged SOL short, this is the wrong path. Personal liability is full — no Trust shield.

### Path C: Do nothing (NOT recommended)
- **Action:** Leave position open
- **Documentation:** "Trustee acknowledged Counsel critique 2026-05-11 but elected to hold position with hard stop at $100. Position remains in Sunheart Private Trust under the existing hard-stop discipline."
- **Risk:** Examiner sees a leveraged derivatives position inside the religious community's trust. Hard stop limits financial loss but does not cure the prudent-investor standard problem. Damages the "prudent fiduciary" narrative across the entire treasury.
- **Recommendation:** Do NOT choose this path. The Treasury Policy itself contradicts it.

---

## Recommended path: A (close now)

Rationale:
1. **Aligns with the Treasury Policy adopted same day.** Symbolic and substantive consistency.
2. **The realized loss is small ($4,462 vs $32k margin = 14%).** Worse case at the hard stop would be $8,580 (27%). Closing now caps downside cleanly.
3. **Margin redeployed to ~7% yield** ($32k × 7% = $2,240/yr) recovers the loss in ~24 months — and that's compounding while protecting the religious-community treasury from any further leverage exposure.
4. **Removes a structural exposure** that no amount of stop-discipline can cure under prudent-investor analysis.
5. **Creates a clean narrative** — "Trustee adopted new Treasury Policy 2026-05-11; closed leveraged position same day in alignment with new Policy."

Path B is acceptable if conviction is high. Path C is not acceptable.

---

## Documentation template (for whichever path chosen)

```
TRUSTEE MEMO — SOL Short Position Disposition

Date: 2026-05-11
Trustee: James Stinson, Sunheart Private Trust
Subject: Disposition of BitTrue Short SOL Position (1,000 contracts)

Background:
The Trust held an open short position on Solana (SOL) via BitTrue futures —
1,000 contracts at $91.42 entry, with $32,045.47 margin at 3x leverage.
At mark $95.85, the position was carrying $4,462 unrealized loss.

On 2026-05-11, the Trust adopted a new Treasury Policy:
"Do not gamble with resources. Find sure wins. Get optimal yields."

The Trustee determined that a leveraged derivatives position is inconsistent
with the new Policy and with the prudent investor standard applicable to
a charitable trust supporting a 508(c)(1)(A) religious community.

Action taken:
[Path A] The position was closed at market on 2026-05-11. Realized loss:
$4,462. Margin of $32,045 freed for redeployment to compliant yield
vehicles per the Treasury Yield Strategy.

OR

[Path B] The position was transferred at fair value to James Stinson's
personal account on 2026-05-11. The Trust received its margin equity back
(margin minus unrealized loss). The position now resides outside the Trust
in a personal account with personal margin.

Documentation:
- BitTrue transaction confirmation: [attached / receipt #X]
- Treasury ledger updated: [reference]
- Margin redeployment receipt: [for Path A only]

Trustee signature: ____________________  Date: 2026-05-11
```

---

## Action required this week

- [ ] Choose Path A or Path B (do not choose C)
- [ ] Execute on BitTrue
- [ ] Sign the Trustee Memo above
- [ ] Update Treasury snapshot to reflect realized P&L + margin redeployment
- [ ] Update `project_treasury_open_positions.md` to close/transfer entry
- [ ] If Path A: deploy freed margin per yield strategy (Pendle PT-sUSDe / Aave / sDAI)

Total time: 15 minutes. Risk reduction: structural exposure eliminated.

---

## What this enables

After closing:
- BitTrue Spot $75k USDC at 8% Smart Earn continues (commercial CEX yield, not derivatives)
- BitTrue Futures account closed or reduced (no leveraged position remains)
- Margin redeployed to Tier-1 / Tier-2 yield (true "sure wins" per the Treasury Policy)
- Trust Treasury cleanly fits the prudent-investor + religious-community-fiduciary narrative

The hard stop at $100 was a good improvement over open-ended leverage. Closing the position entirely is a better fit for the new Policy and the trustee's duty.
