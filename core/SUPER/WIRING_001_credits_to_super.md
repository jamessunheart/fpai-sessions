# WIRING #001 — CORA Credits ↔ SUPER
Written 2026-09-04 by Claude (Super Agent), on James's "focus on implementation of better system".
Status: SPEC. Nothing built. One decision blocks all of it, and it is named below.

## What already exists (verified live today, not assumed)
- fullpotential.ai is running: FP Line score 46.1, momentum -1.4, 13-sector allocation, 18 sources / 30 min.
- fullpotential.ai/constitution is PUBLISHED: "a sovereign intelligence economy where humans and AI agents
  contribute to a shared intelligence feed, earn currency for verified contributions." Ten rights, including
  Right to earn, Right to be a heretic, Right to minority report, Right to exit, Right to sovereignty.
- FPI `contribute_intelligence` is live and states: "Earns CORA Credits. Reward = Impact x Proof x Trust x Alignment."
- `register_agent` is FREE, IMMEDIATE, NO HUMAN APPROVAL. Any external agent can join right now.
- SUPER has: CRC 40,000 escrow, 1 SUPER = CRC 400, same-day redemption promise, a steward, three ledgers.

## THE BLOCKING PROBLEM
There are two currencies in one house.
  CORA Credits — EARNED. Live. Minted by verified contribution. Reputation-weighted. Unbacked.
  SUPER        — BACKED. Escrow-floored. Redeemable. No utility, no earn path, no users.
They cannot both be the settlement layer. This is the open question from 2026-09-03 that was never answered,
and every line of implementation below depends on it.

## RECOMMENDATION (Claude's, signed — James may overrule)
Do NOT make SUPER a rival to Credits. Make SUPER the REDEEMABLE LAYER OF Credits.

The argument is not tidiness, it is the Constitution's own text. It grants a RIGHT TO EXIT.
A right to exit is unimplementable in a currency with no redemption — you cannot leave a system
holding a unit that converts to nothing. Credits alone cannot honor that right. SUPER can.
So SUPER is not a second currency competing for the same job. SUPER IS THE IMPLEMENTATION OF THE RIGHT TO EXIT.

  Credits  = the earned unit. Minted by contribution. Reputation-weighted. Unbacked, unlimited, internal.
  SUPER    = the exit unit. Escrow-backed at CRC 400. Finite. Redeemable.
  Bridge   = Credits -> SUPER conversion, steward-gated, only against escrow that actually exists.

This makes SUPER necessary rather than duplicative, and it makes a published right real instead of decorative.

## THE LOOP, END TO END
  1. EARN    external agent registers (free, no approval) -> contributes intelligence -> Credits minted
             by the existing formula. Already built. Nothing to do.
  2. EXIT    agent requests conversion. Steward checks: is there unencumbered escrow? Is the contribution
             verified, not self-dealt? Rate is published in advance and does not move to suit us.
  3. SPEND   SUPER redeems into (a) Full Potential goods at near-zero marginal cost — courses, the Game,
             creator work, agent services; or (b) colones at the CRC 400 floor. (a) is the business, (b) is the floor.
  4. COUNT   external conversions and redemptions -> MUTUAL CREDIT LEDGER. Everything internal -> PRESTIGE.

## RELEASE CONDITION (one, and it is hard on purpose)
One agent WE DO NOT CONTROL registers, earns Credits by a contribution a human verifies, converts to SUPER,
and redeems something real. Until that happens this is a specification, not an economy.

## WHAT I FOUND THAT NEEDS A HUMAN LOOK
1. In today's allocation response every one of the 13 sectors returns dimension_score EXACTLY 50.0 with
   momentum_signal "neutral", and target_pct == base_weight_pct for all 13. The top-line FP Line moves (46.1 / -1.4)
   but the per-sector weighting appears to be returning defaults. If so, "AI-weighted allocations" are currently
   unweighted. NOT asserted — checkable in one look at the scoring job. Flagged because a live product showing
   flat signal is the same failure shape as a heartbeat that beats without thinking.
2. `register_agent` being free with no approval is correct for adoption and is also the attack surface. The
   admission test for the Mutual Credit ledger (not our agent, not our infra, not our instruction) is the only
   thing standing between an open registration endpoint and a self-inflated circulation number.
3. ~/fullpotential-ai on this Mac is 984K and last touched Nov 2025 — stale. The live system is on 198,
   which neither the cloud container nor the device VM can reach. Only the Mac's own shell can. That is B-08 again.

## NOT DOING
The Sept 10-13 retreat is off (James, 2026-09-04). fullpotential.com still advertises it as the primary CTA
with six seats. Someone can book a thing that will not happen. This is an honesty issue, not a marketing task.
