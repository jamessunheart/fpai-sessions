# AI-Managed Treasury — Architecture v0.1

**Drafted:** 2026-05-19
**Driver:** James asked "Is there a way AI can more effectively manage treasury that's both secure and effective.. friction slows execution"
**Canonical context:** [[reference-treasury-ssot]] · [[reference-alignment-frame]] · [[feedback-just-execute-reversible]]

## The problem this solves

Friction in treasury → unexecuted yield → opportunity cost compounding. Current state has ~$16k USDC idle for weeks because each deploy requires James's soul-time (read state, pick venue, sign tx, wait for bridge, confirm). The James-Hour rubric ([[reference-james-hour]]) shows: treasury ops scoring low on Compound × Irreducibility × Fun. Should be near-zero James soul-time. Currently isn't.

**Goal:** Reduce James's monthly treasury soul-time to ~10 minutes (digest review + occasional 1-tap approvals) while maintaining strong security posture.

## The 4-layer architecture

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: COLD RESERVE (~60-70% of treasury)             │
│ • Hardware wallet (Ledger/Trezor) or true cold storage  │
│ • USDC bulk + any BTC bulk                              │
│ • James-only multi-sig (could include Cheyenne as 2/2)  │
│ • AI: READ-ONLY via public address monitoring           │
│ • Moves OUT require physical James + ceremony           │
├─────────────────────────────────────────────────────────┤
│ LAYER 2: CEX POSITION (~30% · existing Bitrue)          │
│ • Status quo — already producing yield                  │
│ • Don't grow (76% concentration is the cap)             │
│ • AI: READ-ONLY via API key (no withdraw permission)    │
│ • Diversification work tracked separately               │
├─────────────────────────────────────────────────────────┤
│ LAYER 3: OPERATING WALLET (~10-15% · ~$10-15k initial)  │
│ • ERC-4337 smart account                                │
│ • Implementation: Coinbase Smart Wallet OR Safe         │
│ • Session keys for Treasurer AI agent                   │
│ • Hard caps: $2k/tx · $5k/day · allowlisted protocols   │
│ • 24h delay on >$1k moves (James can cancel)            │
├─────────────────────────────────────────────────────────┤
│ LAYER 4: TREASURER AI AGENT                             │
│ • `.claude/agents/treasurer.md`                         │
│ • Monitors yields continuously                          │
│ • Auto-rebalances within L3 session-key bounds          │
│ • Weekly digest to James                                │
│ • Push notifications for big-move approvals             │
└─────────────────────────────────────────────────────────┘
```

## Allowlist (protocols Treasurer AI may interact with)

Battle-tested, audited, established protocols only:

**Lending:** Morpho · Aave V3 · Compound V3
**Fixed yield:** Pendle (PT only · no LP)
**LST staking:** JitoSOL · Lido stETH · Coinbase cbETH · Marinade mSOL
**Stablecoin LP (audited pools only):** Curve 3pool · Uniswap V3 (USDC/USDT 1bps)
**Bridges:** Across · Stargate · native L2 bridges (Base, Optimism, Arbitrum)
**DEX:** Uniswap V3 · 1inch aggregator (for swaps within allowlist)

**Explicitly NOT on allowlist:**
- New protocols (<12 months live + significant TVL)
- Looped vault strategies (yield tier-3 skip per [[reference-treasury-yield-strategy]])
- Wrapped wrapped wrapped tokens (composability risk)
- Centralized stablecoins beyond USDC + USDT
- Algorithmic stablecoins
- Anything with peg risk

Adding to the allowlist requires James review + Counsel sanity-pass.

## Session-key hard limits

| Limit | Cap |
|---|---|
| Per-transaction | $2,000 |
| Daily | $5,000 |
| Weekly | $20,000 |
| Single-protocol exposure | 40% of L3 wallet |
| Delay before execution (moves >$1k) | 24 hours |
| Allowlist | Above only |
| Session key expiry | Auto-expires every 30 days; James re-grants |

## Auto-pause triggers

Treasurer AI immediately pauses all activity if:
- Any allowlisted protocol gets exploited (monitored via DeFiSafety + RektNews + audit firm RSS)
- Smart contract risk audit flag changes to critical
- Stablecoin de-peg event (USDC/USDT >1% off peg)
- Macro flash event (ETH/BTC > -20% in 24h)
- Anomaly in AI session-key behavior (unexpected gas spend pattern)

Resume requires James 1-tap approval.

## The mobile-approval flow (when James needs to be looped in)

1. Treasurer AI proposes move > threshold
2. 24-hour delay starts
3. Telegram push notification (via existing `@sunheartbrain_bot`) OR Safe mobile app
4. James gets summary: "Move $3k USDC from Morpho 4.2% → Aave V3 5.1%. Net +$27/yr. Approve / Defer / Reject."
5. One tap → execute or cancel
6. Logged to weekly digest

5 seconds, not 5 minutes.

## Tool stack — what to actually build

| Component | Tool | Cost | Notes |
|---|---|---|---|
| Smart account | **Coinbase Smart Wallet** (recommended) OR Safe | Free | CSW is simpler; Safe is multi-sig native |
| Session keys | ZeroDev OR Privy | Free tier covers usage | Production-ready 2025 |
| AA infrastructure | Alchemy AA OR Pimlico | Pay-per-tx | Gas sponsorship optional |
| Yield discovery | DeFiLlama Yields API | Free | Live opportunity scanning |
| Mobile push | Telegram `@sunheartbrain_bot` (existing!) | Free | Already wired |
| Treasurer AI | `.claude/agents/treasurer.md` | Free (within Anthropic plan) | Already specced |
| Monitoring | Tenderly Alerts OR custom | Free tier | Set up post-deploy |

**Total stack cost: ~$0 baseline + gas + tx fees (estimate <$20/mo).**

## Phase plan

### Phase A — TODAY (still pending)
- Sign Phase 1 yields manually: JitoSOL stake (~$650/yr) + Morpho USDC (~$700/yr)
- ~$1,350/yr add to baseline
- No infrastructure changes
- **One James-soul-time event:** 5 min of MetaMask + Trust Wallet sigs

### Phase B — M1 (June 2026)
- Set up Coinbase Smart Wallet (~$10-15k operating capital)
- James signs once to seed + grant session key
- Treasurer AI activates in Phase B mode
- AI handles allowlist rebalances autonomously within bounds
- **James-soul-time:** ~30 min initial setup + ~5 min/week weekly digest review

### Phase C — M2-3
- Treasurer AI runs continuously
- Weekly digest becomes routine
- First Counsel sanity-pass on tax/reporting implications
- **James-soul-time:** ~10 min/week

### Phase D — M4+
- Trust-tier 4 escalation if Phase B-C error-free
- Session-key limits raised within risk policy
- AI handles wider scope; James monthly review only
- **James-soul-time:** ~10 min/month

End-state ratio:
- Today: ~30 min per individual deploy × variable frequency
- Phase D: ~10 min per month total
- ~30× reduction in soul-time tax

## Honest risks (named, not buried)

- 🟡 **ERC-4337 ecosystem still maturing.** Production for ~2 years; major implementations audited; some edge cases at margins. Mitigation: stay with Coinbase Smart Wallet (well-tested) + battle-tested protocols.
- 🟡 **Hot wallet ~$10-15k = real loss if compromised.** Mitigation: stay small, audited protocols, auto-pause, monitoring.
- 🟡 **Session-key risk.** If compromised, attacker gets $5k/day cap × time-to-detect. Mitigation: short expiry, anomaly detection, James-cancellable.
- 🟡 **Stablecoin de-peg risk** (USDC depeg precedent March 2023). Mitigation: cap stablecoin LP exposure, auto-pause on depeg.
- 🟡 **Smart contract risk concentrates yield.** Mitigation: allowlist of audited only, max 40% single-protocol.
- 🔴 **Cold reserve compromise = total loss.** Mitigation: hardware wallet + physical security + 2/2 multi-sig with Cheyenne (optional).

## What James does and doesn't do in this architecture

**James DOES:**
- Approve allowlist additions (rare, ~quarterly)
- 1-tap approve moves >$5k (push notification)
- Weekly digest review (~5 min/week → ~10 min/month at Phase D)
- Cold-reserve moves (rare, physical ceremony)
- Strategic policy pivots (yield-first vs growth-first allocation, etc.)

**James DOESN'T:**
- Deploy idle balances (Treasurer auto-handles within L3)
- Rebalance yields (Treasurer auto-handles within L3)
- Bridge funds (Treasurer auto-handles within L3)
- Check daily positions (digest covers it)
- Construct prompts to AI about treasury (Treasurer is presence-aware per the village local mission)

This is the friction collapse.

## Related

- `.claude/agents/treasurer.md` — the agent specced for this work
- [[reference-treasury-ssot]] — SSOT read sequence
- [[feedback-treasury-ssot-discipline]] — discipline rule
- [[project-treasury-open-positions]] — live state
- [[reference-treasury-yield-strategy]] — yield tiers
- [[feedback-yield-first-dont-risk-bank]] — current policy
- [[reference-james-hour]] — soul-time function this preserves
- [[reference-alignment-frame]] — function this serves
