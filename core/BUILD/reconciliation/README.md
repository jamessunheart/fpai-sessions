# Curator reconciliation — repo ↔ live fork audit · 2026-07-02

## The problem

`SERVICES/sunheart-brain/curator/` (repo, built by the build loop) and
`/opt/sh-brain-src/curator/` (live bot) have forked. The deploy bridge
(`tools/deploy/deploy_curator_slice.sh`) is additive-only, so diverged files
**never converge** — every hand-patch to live and every merged-but-undeployed
spec widens the gap.

## Fork inventory (2026-07-02)

| File | Repo | Live | Diff | Direction of truth |
|---|---|---|---|---|
| tgbot.py | 5028L | 5292L | 1398 lines | BOTH — repo has outreach layer (pairing guard, public context pack, becoming capture, public answer synthesis); live has ops layer (status/cost/correct commands, treasury memory, TTS, d020 status fix) |
| decisions.py | 306L | 516L | 816 lines | LIVE ahead (live has features repo lacks) |
| build_context.py | 626L | 354L | 387 lines | REPO ahead (session_progress, richer insights) — live has minimal working insight injection |
| llm.py | 180L | 308L | 214 lines | LIVE ahead |
| telegram.py | 228L | 255L | 54 lines | LIVE ahead |
| live_system_status.py | 241L | 202L | 42 lines | REPO ahead (has _liveness_summary; both have git-log merge fix) |
| corrections.py | 333L | 303L | 35 lines | REPO slightly ahead |

Full unified diffs in this directory: `<file>.repo-vs-live.diff`.

## Files repo-only (built, never deployed — additive, ship via bridge --apply)

attention.py · daily_value_check.py · decision_agent.py · graph_memory.py ·
liveness_status.py · users.py · voice_pipeline.py

## Files live-only (never committed)

conversation_memory.py — port INTO repo.

## Reconciliation plan (queued as d138)

1. Per file, produce a merged version that is a strict superset of both
   behaviors (repo outreach layer + live ops layer), with tests.
2. Land merged versions in the repo — repo becomes canonical.
3. Deploy via bridge (files now identical → future deploys are clean copies).
4. Add a drift alarm: nightly diff repo-vs-live; any divergence surfaces to TG.

Rule going forward: **no hand-patches to /opt/sh-brain-src** — fix in repo,
deploy via bridge.
