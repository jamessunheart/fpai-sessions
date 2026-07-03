# HOT_STATE - 2026-07-03T16:08:36Z - synthesized from 5 scanners

## Active directives
- -> **Flywheel directive landed.** System was optimizing performance (specs merged), not improvement rate. James named it: "The system improves when you show up." Three specs queued to close the feedback layer: d130 (daily value check TG)... [source: core/STATE/identity/ALIGNMENT.md - 2026-07-03T15:37:17Z]
- 1. ** Bot awareness reliability -> 100%** - score 41.3% (19/46 probes), climbing ~2-3%/session automatically. Infrastructure now fixed (write-through, probe timer, HOT_STATE accuracy). Stream: Game/Infrastructure. [source: core/STATE/identity/ALIGNMENT.md - 2026-07-03T15:37:17Z]
- 2. ** Bot awareness -> 100%** - 88% historical, this probe FAIL. Probe now targets correct 7-day window. Session_insights now wired to live bot for first time. Stream: Game/Infrastructure. [source: core/STATE/identity/ALIGNMENT.md - 2026-07-03T15:37:17Z]
- Prior session handoff (2026-06-18 session 2 - BOT AWARENESS PROBED: 5% - d110+d111 QUEUED - 100% TARGET) [source: core/STATE/identity/STORY.md - 2026-07-03T15:37:17Z]

## Spec queue
- 127 specs merged total. Latest: f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a46 (SPEC_f57b8fb5-4b47-4a3d-aa59-9a1d4ea89a4). Recent: f15b6f33-3073-4b44-8ef3-f03dd76a24b0, d37302c6-8b88-48d7-ba6a-cc2855d376dd, d144 [source: brain_index.decisions - now]
- Specs in build pipeline (answered, not merged): d142, d134, d130, d049, 2e8b3441-1ea4-4c7d-a6cd-47f799aa2696 [source: brain_index.decisions - now]
- 1 decisions awaiting James answer [source: brain_index.decisions - now]

## System identity facts
- 162 162.0.208.88 Brain / build loop / AI services / AppFlowy / n8n root [source: core/STATE/RESOURCE_INVENTORY.md - 2026-06-17T22:59:57Z]
- System email `sunheartai@fullpotential.ai` IMAP live, polls every 2min on 162 [source: core/STATE/RESOURCE_INVENTORY.md - 2026-06-17T22:59:57Z]
- Telegram bot (main) `@sunheartbrain_bot` Live, server-side on 162 [source: core/STATE/RESOURCE_INVENTORY.md - 2026-06-17T22:59:57Z]

## Recent architecture decisions
- claude_code/decision: James directive: auto-merge reversible builds, no TG ask - Only BLOCKED (RC=2) or real merge conflicts surface to James. Flagged+reversible builds auto-merge silently. Directive 2026-06-18. [source: brain_index.session_insights - 2026-06-18 17:11:43.999902+00]
- claude_code/decision: Bot awareness reliability target: 100%, measure continuously - Score was 5% (0/8 correct, 3 hallucinations). d110+d111+d112 built. Probe every 2h + after every write. [source: brain_index.session_insights - 2026-06-18 17:11:44.001225+00]
- claude_code/decision: System email: sunheartai@fullpotential.ai (IMAP live, 162) - Outreach email is sunheartai@fullpotential.ai. Previous bot answer emerald@luminari.com was a hallucination. [source: brain_index.session_insights - 2026-06-18 17:11:44.001878+00]

## Active measurements
- ... bounded
