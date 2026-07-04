# Self-Improvement Swarm — Cadence Design

_The loop that pairs the swarm (find) with the build loop (fix). James, 2026-07-04:
"queue the swarm to run as the self-build queue builds, until no more corrections are
found — match build-queue capacity without overwhelming." This is that, made robust._

## The loop
```
  probe (swarm find) → rank top-N by severity → constitution_check gate → queue as decisions
     → build loop fixes them ($0, 10min) → VERIFY the fix live → queue near-empty + system changed?
     → re-probe → ... → K rounds with no new HIGH/MED finding → DORMANT (the coherence signal)
```
The controller paces **find-rate to fix-rate**: it does not re-probe until the last batch
is built and verified. Find never outruns fix. No backlog pile-up.

## The rules (what makes it not-overwhelm and actually converge)
1. **Change-gated trigger** — re-probe only when (a) queue is low AND (b) the repo changed
   materially since the last probe (git-diff / merged-spec delta). Re-probing an unchanged
   system burns ~1.8M tokens for nothing. (Council's proven pattern.)
2. **Meter top 3–5 by severity** per round — not all 34. The rest re-surface next round.
3. **Converge on "dry for K rounds, HIGH/MED only"** → go dormant. Not literal zero (a
   self-evolving system always has a low-sev nit). Dormant = the system is coherent right now.
4. **Verify the fix LIVE before re-probing** — "merged" is not "fixed" (the merged≠live gap).
   The loop confirms the weakness is actually gone, else it re-finds or false-closes.
5. **Facet rotation on dryness** — when the fixed 8 lenses go quiet, rotate to new probe
   angles (completeness-critic); dryness = "these lenses clean," not "done."
6. **Budget ceiling** — per-round + daily token cap; the swarm is expensive, cap the burn.

## Sequencing (prove before automate — P1 + "prove once, then schedule")
The swarm's last run dropped its findings at the rank stage (now fixed but unverified).
**Do NOT wire the cadence around an unproven pipe.**
- ☐ **Gate 1:** one clean end-to-end proving run (find → rank → non-empty intent stream → queue).
- ☐ **Gate 2:** build the cadence controller (change-gate + top-N + verify-live + budget cap).
- ☐ **Gate 3:** James enables the timer (scheduling = persistence, harness-gated → his hand).

Output-only until Gate 3: the swarm surfaces intents through `constitution_check → decisions`;
the human/daemon owns arming the build pipeline.
