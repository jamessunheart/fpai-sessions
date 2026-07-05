# SPEC_d195_council-proactive-spot-topple-a Result

Date: 2026-07-05
Branch: `build/SPEC_d195_council-proactive-spot-topple-a`

## Summary

Made `tools/council/debate.py` proactive for safe Spot -> Topple winners. A council winner now writes directly to `brain_index.decisions` via `curator.decisions seed` as an answered `needs_build=true` decision when it passes the Constitution Check, is non-Reserved, explicitly reversible/low risk, within the auto-topple cost cap, north-star/substrate aligned, and under the new 3/day auto-topple cap.

Reserved-Class winners still surface through the existing `recommend` path for James. The one-at-a-time gate is restored for decisions already awaiting James, while answered build-loop rows do not block council spotting. Every auto-topple writes a `council auto_toppled` ops-log row; held proposals write `auto_topple_held`.

## Files Changed

- `tools/council/debate.py`
- `tools/council/test_debate.py`
- `core/BUILD/specs/SPEC_d195_council-proactive-spot-topple-a.md`
- `core/BUILD/results/SPEC_d195_council-proactive-spot-topple-a.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.council.test_debate`
- `python3 -B -m unittest tools.council.test_debate tools.council.test_debate_import tools.reserved.test_classify tools.governance.test_constitution_check tools.build_loop.test_spot_topple_orchestrator`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/council/debate.py tools/council/test_debate.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d195-registry-building.json`
- `git diff --check`

## Proof

Regression coverage proves a reversible, north-star-aligned winner queues through `seed` without James; a Reserved money/signature winner surfaces through `recommend` and never seeds; three same-day `auto_toppled` ops rows block the fourth; and an awaiting James decision prevents a council debate run.

## Risks

No live council run or live DB insert was executed in this sandbox. The north-star and reversibility checks are deterministic text gates; ambiguous proposals will surface rather than auto-topple. Constitution Check errors now fall back to surfacing only; proactive queueing requires an accepted Constitution Check result.

## Rollback

Revert this branch. Runtime kill switch remains `~/.config/fpai/council/.disabled`; the recommendation kill switch remains `~/.config/fpai/decisions/.recommend_disabled`.

## Intent

Intent solved: council Spot -> Topple no longer stalls on James approval for safe reversible work.

Downstream intent unlocked: the build loop can autonomously build/review/auto-merge reversible council-discovered substrate work while James sees only Reserved or ambiguous gates.
