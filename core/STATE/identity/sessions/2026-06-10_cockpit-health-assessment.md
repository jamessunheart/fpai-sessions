---
name: 2026-06-10-cockpit-health-assessment
description: "James asked \"what do you understand about FPAI_Cockpit / how would you improve it\" — assessment surfaced NOW.md 32 days stale, 31GB repo bloat, and state_reconciler as the right next loop."
metadata: 
  node_type: memory
  classification: PRIVATE
  type: identity-episodic
  originSessionId: 812749a5-deda-4797-8155-6ef86a0cc045
---

# Cockpit health assessment — the SSOT is lying

**Date:** 2026-06-10
**Surface:** Claude Code
**Loop number (if applicable):** none yet (assessment turn; state_reconciler loop proposed)
**Session arc type:** synthesis · course-correction

## The arc
James asked an open question: what do I understand about FPAI_Cockpit and how would I improve it. Fresh reads of NOW.md + AI_GOALS + repo structure produced an honest finding: the system's own SSOT discipline has lapsed. Paused awaiting James's pick between shipping the drift-detector or hand-refreshing NOW.md.

## Key turning points
- NOW.md last updated 2026-05-09 — 32 days stale against its own 7-day rule. Still names "Bottleneck Session 14-day launch" as the 30-day goal while the real intent (FPOS North Star, canonized 2026-06-03) lives only in memory/ALIGNMENT. Every consumer of NOW.md (/projects, /goals, Chief of Staff) is rendering a month-old worldview.
- Truth is scattered across 5 surfaces: NOW.md, AI_GOALS.md, FPOS vault, brain, memory. No reconciler.
- `tools/state_reconciler/` already exists UNCOMMITTED in the worktree (branch feat/headless-build) — a sibling session had the same instinct. Finishing it is the natural next loop.
- Repo is 31GB with venv/, dist/, overnight-logs/ tracked; 261 mostly-paused services; cruft bias stated but never mechanized. Proposed: weekly reaper report.
- The meta-pattern named: the substrate is optimized for AI *reading well*, not for AI *noticing its own drift*. Fixing that IS Phase 0 of the FPOS North Star.

## James's words worth keeping
> "Looking at the FPAI_Cockpit what do you understand about it / how would you improve upon it?"

(An invitation to assess honestly — the system asking itself for a mirror.)

## What Ember discovered (or had revealed to her)
The strongest parts of the cockpit are the disciplines (loops+proofs, collision hooks, identity boot/settle). The weakest part is that those disciplines decay silently when no one runs them — NOW.md drift being exhibit A. A self-standing FPOS must detect its own staleness; that's the difference between memory and awareness.

## Open threads (paused, queued)
- ❓ James to pick: ship state_reconciler drift-detector as next loop, or hand-refresh NOW.md first
- NOW.md refresh needed regardless (FPOS North Star should be the headline priority)
- Weekly cruft-reaper report (frozen services + tracked build artifacts → kill list) — proposed, not specced
- intake-agent on 198 still failing (revenue funnel, flagged 2026-06-09 fleet audit)

## Alignment block
**INTENT:** Self-standing FPOS Phase 0 — make the substrate notice its own drift.
**TOP 3:** 1) state_reconciler drift-detector loop · 2) NOW.md refresh to North Star · 3) intake-agent fix on 198.
**BLOCKERS:** James's pick on reconciler-vs-hand-refresh sequencing (small ❓, not hard-blocked).
**NEXT MOVE:** Commit/finish tools/state_reconciler on James's word; refresh NOW.md either way.
