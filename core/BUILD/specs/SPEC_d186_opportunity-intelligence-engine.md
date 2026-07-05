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

## ADDENDUM (James 2026-07-05) — the EXTERNAL scan + closest-to-cash sequencing (the actual gap)
Probe confirmed: the system scans INTERNAL gaps only (Council/self-audit) + an AI-frontier scan (forge). There is NO external market-opportunity scanner. Web access from 162 WORKS (verified). This addendum makes d186 the external Loop 2, not just an internal reranker.

1. **External market-signal scanner** (cron, uses the working web access — $0 via urllib/web-fetch; add a paid signal source only if it pays for itself): pull cheap public signals — where AI capability now exceeds market adoption (new model releases vs slow-moving industries), where humans visibly overspend (job posts for repetitive roles, pricing of manual services), trending pain (forums/news). Each signal → an Opportunity Portfolio row with blanks where unknown (never fabricate).
2. **Rank by CASH PROXIMITY as a first-class axis:** add `time_to_first_dollar` and `path_to_recurring` to the score. The engine surfaces the top opportunity **closest to cash** separately from the top by long-term Opportunity Score — so "what can produce revenue fastest" is always visible.
3. **Close the build bridge:** the top closest-to-cash opportunity that passes the Council + Constitution gate becomes a real spec in the build queue (a landing page / assessment variant / micro-tool) — so a discovered market opportunity flows discover → score → build → ship, not just discover → log. Reversible + James-gated on anything that spends or goes public.
4. **Start seeded, not empty:** pre-load the portfolio with the opportunities James already named (Resource Optimization Audit = the live BBB offer · AI Voice Receptionist · Medical Documentation Agent · Finance Allocation Engine) so the ranker has real candidates day one.

**Honest scope:** external scanning ≠ magic. v1 uses free signals + the AI's own judgment; it will be noisy. The value is the RANKING DISCIPLINE (dual-score + cash-proximity) applied consistently, improving as the Capability Ledger (d185) feeds real outcomes back. Don't oversell it as an oracle.

## ADDENDUM 2 (James 2026-07-05, the Allocator promotion) — cycle, rubric, cascade, ledger
The brain is an **Intelligence Capital Allocator**; d186 IS the allocator's engine. Add:

**The 8-step daily cycle (the operating loop):** Observe (what changed — tech · market · customer requests · competitors · internal capability · new relationships · capital · proof) → Discover (actual opportunities, each: who suffers · why · how expensive · why now · why us) → Score (weighted rubric below) → **Sequence (the critical step — build the DEPENDENCY GRAPH, not a ranked list)** → Allocate (resources flow only to the highest expected return) → Execute (only after allocation) → Learn → Compound.

**The weighted scoring rubric (CURRENT weights — evolve as objectives shift; today = move treasury fast while strengthening the engine):**
Time-to-Revenue 20% · Expected ROI 20% · Strategic Alignment 15% · Proof Speed 15% · Uses Existing Assets 15% · Recurring Revenue 10% · Compounding Learning 5%. Store the weights as config so they change with the objective, not the code.

**★ SEQUENCE = cascade, not a list.** Don't output "1,2,3,4,5." Build the dependency graph — e.g. Resource Optimization Audit → Cost Reduction Engine → Monthly Intelligence Service → Industry Benchmark DB → AI Operating System → Allocation Platform. The engine picks the **smallest domino that starts the largest cascade** (Law 3), not the biggest opportunity. This is the single most valuable behavior — think in cascades, not isolated projects.

**Full Opportunity Ledger fields (permanent per opportunity):** Problem · Buyer · Pain Level · Market Timing · Average Deal Size · Recurring Revenue · Time to First Dollar · Automation Potential · Strategic Alignment · Compounding Potential · Proof Collected · Current Confidence · Recommended Next Action. The AI stops brainstorming and starts managing an investment portfolio.

**Governs the Council:** the Council's "pick THE ONE build" becomes "pick the smallest-domino from the top of the cascade graph, by current-weighted score." Realized outcomes (d185 Capability Ledger) update confidence + weights. Proof outranks opinion (Law 5) — reality corrects the model.
