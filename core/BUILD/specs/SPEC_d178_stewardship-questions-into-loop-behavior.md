# SPEC d178 — Convert stewardship doctrine from Principle → Behavior (the loop self-asks)

**Why (GPT insight, James relay 2026-07-04):** today's doctrine (Stewardship Constitution · Value Arbitrage · Intelligence Law) is Insight→Principle — a lens in the boot spine, not yet a behavior. Capability only grows when the loop EXECUTES the principle automatically. The 24h test (LEARNING_METRICS) is the gauge. This spec builds the behavior.

## Build
1. **The self-asked questions, each cycle.** Wire into the council/metabolism loop (`tools/council/debate.py` + `tools/metabolism/nightly.py`) a standing pre-pass that answers, from live system state, the six stewardship questions:
   - What resources are currently idle? (scan: subscriptions, servers, unused code, dormant agents — cross-ref BURN_REGISTRY + RESOURCE_INVENTORY)
   - Where is the largest unrealized Value Gap right now? (perceived vs realizable)
   - Which available opportunity has the highest expected return on allocation?
   - What proof could the system generate today?
   - Has any decision-class earned greater autonomy (maturity ladder promotion)?
   - Is there a better allocation than the one currently running?
2. **Feed the answers into the existing selector** — the council already picks THE ONE build; this makes it pick against the value-gap frame, not just the pending queue. Output: a ranked "value-gap opportunities" list the council allocates from.
3. **Run the 24h capability test as a metric.** Daily: did the system make an allocation today that a yesterday-version wouldn't have, attributable to a principle? Log to LEARNING_METRICS. Surface in fpos-health.
4. **Close the loop to the ledger** — each closed value-gap → an Allocation Ledger row (proof), which is simultaneously the trust ledger (per keystone v1.4).

## Contract
$0 · reversible (loop pre-pass behind a flag) · read-only scans + queue proposals only (never self-arms prod/money — Constitution Check gates) · independent review. This is the behavior layer that makes every prior doctrine drop actually raise capability.

## Done / Proof
The nightly loop emits a value-gap opportunity list + self-answers the 6 questions from real state · one cycle picks a build BECAUSE it closed the largest value gap (logged) · the 24h capability metric appears in LEARNING_METRICS with ≥1 real "better-because-of-yesterday" allocation.
