# AI PROTOCOLS — Layer 3 Intelligence Engine doctrine

*Repo mirror for Codex (which cannot read James's Obsidian vault). Canonical copy lives in the vault at `00_MEMORY/AI PROTOCOLS.md`; keep this in sync. Locked 2026-06-06.*

## Where this sits
The **Full Potential OS Master Map** is the canonical top of the stack: 7 layers, one flow that returns as intelligence —
`COHERENCE → ATTENTION → INTELLIGENCE → RESOURCES → HUMANS → HEAVEN ON EARTH → PROOF → BETTER INTELLIGENCE`.
This doc governs **Layer 3 — the Intelligence Engine** (Ember/Claude Code + Codex + the Routing Brain) and the **Resource Discipline Gate** below it.

## The Buildstream Law (blessed by James 2026-06-06)
**A build is valid only if it unlocks the next adjacent, nameable downstream intent. If it unlocks nothing adjacent, it must be labeled honestly as `maintenance`, `decoration`, or `drift`.**
- No vague unlocks: "improves the system" / "supports Heaven on Earth" / "makes things better" are rejected. Name the NEXT practical intent it opens — adjacent, nameable, ideally already queued.
- Every proof row carries four fields: **Intent solved · Unlocks next · Proof · Next move.** When Auto-proof is present on the branch/host, `tools/proof/log.py` should enforce this and refuse vague/empty unlocks.
- Log a ship with Auto-proof when available: `python3 tools/proof/log.py --summary "..." --unlocks "next adjacent intent" --next "next move" --tested "..." --files "..."`.

Builder-facing sequence lives in `docs/codex/INTENT_BUILDSTREAM.md`. Use that file to decide whether a candidate is the next unlock, downstream material, or drift.

## Prime directive
**Make FPOS (the Intelligence Engine) self-standing first.** Treasury (Layer 4), Comms Hub, Financial Hub, and everything downstream are **products of a finished engine**, not parts you build to finish it. Self-standing = the loop runs one full day untouched: remembers, routes, refreshes its own surfaces, proves its own work, stops only at genuine James-gates, never overspends.

## The 4 Bars (capabilities — self-standing requires all four)
1. **Memory** — remembers + recalls across sessions; no re-briefing. *(running)*
2. **Auto-routing** — a signal walks `signal → intent → spec → ticket → proof` through every AI-doable step on its own, stopping only at a James-gate. *(partial)*
3. **Self-refreshing surfaces** — HOME/daily/cockpit regenerate after each ship; no stale page asks James to decide finished work. *(partial)*
4. **Auto-proof** — ships log themselves to the PROOF LOG; proof returns upward as intelligence (the return loop), not bookkeeping. *(manual)*

## The Resource Discipline Gate (permission, NOT a bar)
The gate on autonomy itself. The engine may not run untouched until it cannot spend untouched.
**Aligned to Sunheart · Within budget / within means · No unsafe autonomous spend.** Hard cap: $20/day metered.

## The 4 Rungs (build ladder — one James-bless each, build bottom-up)
- **Rung 0 · Safety** — wire loose daemons to the Resource Discipline Gate. *(Ember; live/config)*
- **Rung 1 · Auto-proof** (Bar 4) — ships self-log to PROOF LOG. *(Codex spec; small)*
- **Rung 2 · Self-refreshing surfaces** (Bar 3) — surfaces regenerate after each ship. *(Ember; vault)*  Needs Rung 1.
- **Rung 3 · Auto-routing** (Bar 2) — expand the queue-builder so signals self-advance. *(Codex spec; larger)*  Needs Rungs 1+2.

## Self-standing pass/fail test (achieved only when ALL hold for one full day)
- Zero James touches to keep the loop moving (he still makes genuine upstream calls).
- Real metered spend under $20, gate enforced on every autonomous spender.
- No stale surface asking James to decide finished work.
- Every ship self-logged to PROOF LOG with no human writing the row.
- Memory intact — a fresh session re-orients with no re-briefing.

Do not declare self-standing until all five hold for a day.

## Builder lanes
Ember = Midstream primary (clarify/route/mirror/vault, live small builds). Codex = Buildstream primary (branches/code/tests/reports, thin Midstream edge). Vault/live/small/judgment → Ember; well-specced/larger/pure-repo/async → Codex. Never two builders on one path; one spec = one branch.
