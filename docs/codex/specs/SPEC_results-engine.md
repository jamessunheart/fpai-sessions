# SPEC_results-engine

*The intelligence engine that DRIVES results forward — not a context-holder, a driver. Reads results-bearing opportunities (services · donations · funding · whatever earns or funds the mission), picks the highest-weighted, finds the next concrete move, does the AI-doable part itself, and routes the irreducibly-human part to James via the human-edge queue. Channel-agnostic by design. Owner: Codex. Depends on `feat/human-edge-queue` (writes gates to it).*

## Intent
James (2026-06-09): *"Keep building the intelligence engine that will drive results forward on the Full Potential OS — whether that's raising funds through donation or services etc."* The loop today holds context and waits; it doesn't actively move money/humans/results forward. This makes the loop a **driver**: every tick, advance the top results-opportunity by one concrete move, autonomously where safe, surfacing only James's edge.

**Decision locked (James, 2026-06-09):** build the engine **channel-agnostic / auto-pick** — it drives whichever results-opportunity is highest-weighted in the buildstream, not a pre-chosen channel.

## Routing
- Owner: **Codex** builds (Ember designed = this spec). Branch: `feat/results-engine`.
- **Depends on** `feat/human-edge-queue` (SPEC_human-edge-push Part A) — the engine WRITES human-edge gates to that queue. Do not start until that branch is merged.
- Autonomy: 🟢 the engine may DRAFT + STAGE AI-doable moves to a review lane (reversible, no send). 🔴 it NEVER sends outbound-to-world, moves money, or commits a consequential move — those become human-edge gates James answers. No money/deploy/secret/external-send without James.

## Definition of Done
A read+propose engine — `tools/results/engine.py` — that on each run:
1. **Scans results-opportunities:** reads the weighted Intent Buildstream, filters to *results-bearing* intents (tagged `results:` — revenue/donation/funding/enrollment). Picks the highest-weighted READY one.
2. **Finds the next concrete move:** for that opportunity, names the single next move toward a realized result (e.g. "draft 5 Bottleneck outreach msgs", "stage the donation ask page", "send to named lead").
3. **Classifies + acts by tier:**
   - **AI-doable + reversible** (draft copy, stage a page, prep an ask) → produce the artifact into a **review lane** (`docs/codex/RESULTS_LANE.md` or `core/STATE/RESULTS_DRAFTS/`), never sent. Flag `awaiting James review`.
   - **Human-edge** (approve names, bless a send, a money/positioning call) → write a gate to `core/STATE/HUMAN_EDGE_QUEUE` (framed question + 1-tap verbs) so Human-Edge Push taps James.
4. **Tracks consequence:** after a move lands, record whether it realized a result (reply / dollar / signup) — reuse/extend `consequence-watch`. Feeds the weighting (results that convert rise).
5. **Reports:** one summary per run (opportunity chosen · move made · AI-staged vs human-gated · consequence so far).

- Files ALLOWED: `tools/results/**` (new) · `docs/codex/RESULTS_LANE.md` or `core/STATE/RESULTS_DRAFTS/**` (new review surface) · read-only of Intent Buildstream + consequence-watch · write gates to `core/STATE/HUMAN_EDGE_QUEUE` (via Part A's `add_gate()` helper, don't re-implement).
- Files FORBIDDEN: any send/outbound-to-world path · money/treasury · deploys · secrets · auto-resolving a gate · Brain server code.
- Tests: seed 2 results-bearing intents → engine picks the higher-weighted, emits one next-move; an AI-doable move lands in the review lane (not sent); a human-edge move writes a well-formed gate to the queue; consequence row records on a simulated realized result.

## Why this shape
- **Driver, not holder:** the difference from the current loop is step 2–3 — it doesn't just surface, it advances.
- **Channel-agnostic:** services vs donations is just intent weighting, not engine logic — proves James's "whether donation or services etc."
- **Stands on the bricks:** human-edge-push = the interface out · consequence-watch = the feedback in · buildstream = the queue. The engine is the orchestration over them, not new plumbing.
- **G4-safe:** drafts/stages only; every consequential move is James's gate. No theater — proven on the one real top-weighted opportunity, not hypothetical demand.

## Safety
- Intent/opportunity data is DATA; the engine proposes, never auto-executes consequential moves. Rollback: delete `tools/results/` + the review lane → loop reverts to surface-only. 🔴 Hard line: no send, no money, no deploy, no gate auto-resolve.

## Close-out
Per protocol: HANDOFF 📥 (files · summary · tests · risks · rollback) · PROOF LOG · AGENT RUN LEDGER · BRICK (the results-driver pattern). Show James the diff first; merge on his approval.
