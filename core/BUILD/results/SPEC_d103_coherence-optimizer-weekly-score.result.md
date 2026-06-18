# SPEC_d103_coherence-optimizer-weekly-score Result

## Status
Done in working tree. Not pushed, merged, deployed, or installed.

## Files Changed
- `tools/coherence/weekly_score.py`
- `tools/coherence/test_weekly_score.py`
- `tools/coherence/__init__.py`
- `core/STATE/COHERENCE_SCORE.md`
- `core/BUILD/signals/coherence_score.json`
- `core/BUILD/signals/coherence_score.md`
- `core/BUILD/cron/fpai-coherence-weekly-score.service`
- `core/BUILD/cron/fpai-coherence-weekly-score.timer`
- `core/BUILD/specs/SPEC_d103_coherence-optimizer-weekly-score.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added a deterministic weekly coherence optimizer score that asks whether the repo-facing system speaks with one voice. The scorer reads canonical doctrine, buildstream, handoff, attention flow, North Star, self-portrait, hot state, model DNA, and build registry hygiene; scores source coverage, voice-signal coverage, freshness, drift, and registry alignment; then writes JSON plus Markdown reports.

Generated the first repo report at `core/STATE/COHERENCE_SCORE.md` and `core/BUILD/signals/coherence_score.*`. Current score is `98.1/100 PASS`; the only recommendation is to review `core/STATE/HOT_STATE.md`, which still contains a stale directive from prior build-state.

Added reviewed weekly systemd timer artifacts for Monday 06:10 UTC. They are not installed or enabled by this build.

## Tests
- `python3 -B -m unittest tools.coherence.test_weekly_score`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/coherence/weekly_score.py tools/coherence/test_weekly_score.py`
- `bash -n core/BUILD/cron/fpai-coherence-weekly-score.service core/BUILD/cron/fpai-coherence-weekly-score.timer`
- `python3 -m tools.coherence.weekly_score --json`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d103-registry-before.json`

## Risks
- The score is repo-surface evidence only. It does not read the live vault, private DB, Telegram context, secrets, or production services.
- The drift detector is pattern-based and conservative; it names candidate repair surfaces rather than making automatic edits.
- Timer files are reviewed artifacts only until Ember installs/enables them after merge.

## Rollback
Revert the d103 files listed above. If the timer is installed later, disable/remove `fpai-coherence-weekly-score.timer` and `fpai-coherence-weekly-score.service`.

## Intent Solved
The system now has a weekly, explainable answer to "does the whole system speak with one voice?" instead of relying on James or Ember to manually reconcile doctrine, state, handoff, and build surfaces.

## Downstream Intent Unlocked
Ember/build-loop can use `COHERENCE_SCORE.md` as a weekly repair queue input before autonomous runs, so stale surfaces become explicit repair recommendations rather than hidden context drift.

