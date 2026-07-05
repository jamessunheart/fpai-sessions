# SPEC d186 — Opportunity Intelligence Engine (the "what to build" loop + live scored portfolio)

**Why (James 2026-07-05, the missing layer):** the system answers "how do we build" (Loop 1, live) but not "what should we build" (Loop 2, missing). This builds Loop 2: a standing function that discovers, scores, ranks, and sequences opportunities so the Council allocates intelligence to the highest-leverage work instead of only draining a bug/feature queue. Absorbs/supersedes d178 (value-gap questions become this engine's scan). Doctrine: keystone §OPPORTUNITY INTELLIGENCE.

## Build
1. **Opportunity Portfolio table** (`brain_index.opportunities` or a JSON ledger): each row = an investment candidate with the 8-question fields (problem · who-pays · pain · can-AI-solve · prove-quickly · recurring · makes-us-smarter · unlocks-more) + numeric axes (pain, market, difficulty, time-to-revenue, compounding).
2. **Two scores per row:** **Opportunity Score** (how valuable could it become — pain×market×compounding discounted by difficulty+time) and **Allocation Score** (should we pursue NOW given current resources/attention). Sequence by both; a high-Opportunity/low-Allocation item parks, doesn't die.
3. **The daily Gap scan** (cron, cheap): "where has the gap between available AI capability and market adoption grown most since yesterday?" — pulls from cheap signals (the Council's own findings, recent proofs, known client pain, web/news if available) → proposes/updates opportunity rows. No fabrication — unknown fields stay blank, not guessed (P4).
4. **Feed the Council:** the Council's "pick THE ONE build" now selects from top-Allocation-Score opportunities, not just the pending spec queue. Realized outcomes (from the Capability-Created Ledger, d185) update each opportunity's actual-vs-expected, training the scorer.
5. **Surface:** `/opportunities` command + a weekly digest line = the top 5 by Opportunity Score and the top 3 by Allocation Score (do-now).

## Contract
$0 · reversible · honest-or-blank (no invented scores) · independent review · read/rank/propose only — never self-arms a build without the Council + Constitution Check gate.

## Done / Proof
The portfolio holds ≥5 real scored opportunities (incl. the current one: Resource Optimization Audit = the BBB/Savings-Split offer) · the daily Gap scan updates it · the Council picks its next build FROM the portfolio by Allocation Score · `/opportunities` returns the ranked list.
