# HOT_STATE - 2026-07-03T16:20:57Z - synthesized from 5 scanners

## Active directives
- 1. ** Bot awareness reliability -> 100%** - d110 (write-through) + d111 (probe) show `merged` in DB; verify they're in git. Build loop now running correctly so they should be deployed. Current awareness still TBD. [source: core/STATE/identity/ALIGNMENT.md - 2026-06-25T10:00:17Z]
- 1. ** Bot awareness reliability -> 100%** - score 41.3% (19/46 probes), climbing ~2-3%/session automatically. Infrastructure now fixed (write-through, probe timer, HOT_STATE accuracy). Stream: Game/Infrastructure. [source: core/STATE/identity/ALIGNMENT.md - 2026-06-25T10:00:17Z]
- Prior session handoff (2026-06-18 session 2 - BOT AWARENESS PROBED: 5% - d110+d111 QUEUED - 100% TARGET) [source: core/STATE/identity/STORY.md - 2026-07-03T13:59:24Z]
- READ FIRST: `sessions/2026-06-22_synthesis-fix-and-build-loop-drain.md`.** Two systems unblocked in one session. **(1) Bot synthesis fixed** - " Brain synthesis hit an error:" was `httpcore.ReadTimeout` (ollama 8b taking >180s on 5-block... [source: core/STATE/identity/STORY.md - 2026-07-03T13:59:24Z]

## Spec queue
- Top pending build specs (file-based): SPEC_1cf20da7-0125-459e-a742-94c3f3976203_measure-improvement-rate-not-out, SPEC_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696_test-stall-audit, SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e-reality-fix_repair-me... [source: core/BUILD/specs - 2026-07-02T18:42:52Z]
- Last git merge/build marker: e628b269 Merge branch 'build/SPEC_d050_module-blueprint-system-living-c' into feat/headless-build [source: git log - 2026-07-03T16:06:50Z]

## System identity facts
- 162 162.0.208.88 Brain / build loop / AI services / AppFlowy / n8n root [source: core/STATE/RESOURCE_INVENTORY.md - 2026-06-25T10:00:17Z]
- System email `sunheartai@fullpotential.ai` IMAP live, polls every 2min on 162 [source: core/STATE/RESOURCE_INVENTORY.md - 2026-06-25T10:00:17Z]
- Telegram bot (main) `@sunheartbrain_bot` Live, server-side on 162 [source: core/STATE/RESOURCE_INVENTORY.md - 2026-06-25T10:00:17Z]

## Recent architecture decisions
- **Downstream intent unlocked:** L2 learning/dataset export can learn from Claude Code corrections once the live Claude Code thread append gate is installed and one real proof row lands. [source: docs/codex/HANDOFF.md - 2026-07-03T16:20:57Z]
- **Downstream intent unlocked:** next council debate JSON can cite `NORTH_STAR.md`; d057 benchmark output can continue mapping measured runs to the defined sovereign efficiency targets. [source: docs/codex/HANDOFF.md - 2026-07-03T16:20:57Z]
- **Intent solved:** Claude Code corrections can feed `brain_index.corrections` instead of leaving James's primary surface invisible to the correction-learning loop. [source: docs/codex/HANDOFF.md - 2026-07-03T16:20:57Z]

## Active measurements
- Bot/build host visible as Jamess-MacBook-Air.local; repo readable=True [source: local host - 2026-07-02T17:32:13Z]
- ... bounded
