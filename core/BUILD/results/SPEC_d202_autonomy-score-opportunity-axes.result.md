# SPEC_d202_autonomy-score-opportunity-axes Result

## Status
Done in working tree. Do not push or merge from Codex.

## Files Changed
- `tools/allocation/opportunity_axis_scorer.py`
- `tools/allocation/test_opportunity_axis_scorer.py`
- `core/BUILD/activate/SPEC_d202_autonomy-score-opportunity-axes.sh`
- `core/BUILD/specs/SPEC_d202_autonomy-score-opportunity-axes.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`
- `core/BUILD/results/SPEC_d202_autonomy-score-opportunity-axes.result.md`

## Summary
Added an advisory Opportunity Portfolio axis scorer. It reads the configured
portfolio ledger, calls `claude -p` for rows missing `REQUIRED_DOMINO_AXES` (or
all rows with `--rescore-all`), validates/clamps all required axes to 0-10,
writes the axes back, and appends a JSONL audit row.

The deterministic `opportunity_engine.ranked()` remains the only scoring/ranking
source. The scorer only supplies the axes needed for the existing Opportunity
Score, Allocation Score, and Next Domino Score formulas to differentiate rows.

Added a guarded systemd activation script for a 6-hour cadence. It writes
`fpai-opportunity-axis-scorer.service` and `.timer`, uses the live
`/root/.config/fpai/allocation/opportunities.json` default ledger, logs to
`/root/.config/fpai/allocation/opportunity_axis_scores.jsonl`, and supports the
kill switch `/opt/fpai-build/.opportunity_axis_scorer_disabled`.

## Proof
- Unscored fixture opportunity receives all required axes, non-None ranked scores, scorer metadata, and an advisory log row.
- Complete rows are skipped unless `--rescore-all` is set.
- Ranking can pick `ai-voice-receptionist` over `assessment-funnel-delivery-proof` when its axes genuinely outscore funnel, proving the orchestrator is not locked to the first row.
- Activation script generates the expected service/timer in a temp unit dir without touching real systemd.

## Tests
- `bash -n core/BUILD/activate/SPEC_d202_autonomy-score-opportunity-axes.sh`
- `python3 -B -m unittest tools.allocation.test_opportunity_axis_scorer tools.allocation.test_opportunity_engine tools.build_loop.test_spot_topple_orchestrator`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/allocation/opportunity_axis_scorer.py tools/allocation/test_opportunity_axis_scorer.py`
- `FPAI_SYSTEMD_DIR=/tmp/... FPAI_REPO_ROOT=/tmp/repo FPAI_OPPORTUNITY_LEDGER=/tmp/opportunities.json FPAI_OPPORTUNITY_AXIS_SCORE_LOG=/tmp/axis.jsonl core/BUILD/activate/SPEC_d202_autonomy-score-opportunity-axes.sh`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d202_autonomy-score-opportunity-axes --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d202-registry-building.json`
- `git diff --check`

## Risks
- Live `claude -p` cadence proof was not run in this sandbox.
- The scorer is advisory and model-scored; axis values should be treated as first-pass ranking inputs, not verified market facts.
- The cadence rewrites axes with `--rescore-all`; disable with `/opt/fpai-build/.opportunity_axis_scorer_disabled` if James/Ember wants a manual review window.

## Rollback
Revert this branch. If activated live, run:

```bash
systemctl disable --now fpai-opportunity-axis-scorer.timer
rm -f /etc/systemd/system/fpai-opportunity-axis-scorer.service /etc/systemd/system/fpai-opportunity-axis-scorer.timer
systemctl daemon-reload
```

Runtime mitigation without rollback: touch
`/opt/fpai-build/.opportunity_axis_scorer_disabled`.

## Intent Solved
SPOT no longer has to default to the first opportunity when the live portfolio is
missing axes; the system can populate the axes required for real discernment.

## Downstream Intent Unlocked
Spot & Topple can choose the genuine smallest-domino-biggest-cascade, including
a non-funnel domino when its scored opportunity/cash/proof/leverage/reversibility
profile outranks funnel.
