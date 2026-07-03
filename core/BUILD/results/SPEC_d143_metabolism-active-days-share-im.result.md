# SPEC_d143_metabolism-active-days-share-im Result

- Status: done in working tree
- Summary: Forged exactly one reversible experiment-lane improvement for `active_days_share`: an OFF-by-default 14-day daily closeout packet experiment behind `FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT=0`. The work order records the d143 baseline (`9/14`, `0.642857`), acceptance criteria, rollback, and a measurement plan that reruns `tools/metrics/conversion_snapshot.py` after 14 days and logs a `feature_outcome` verdict only after auditing that commits represented real buildstream/proof work.
- Files changed: `core/BUILD/improvement_proposals/SPEC_d143_active_days_share_closeout.md`; `tools/build_loop/test_d143_work_order.py`; `core/BUILD/specs/SPEC_d143_metabolism-active-days-share-im.md`; `core/BUILD/results/SPEC_d143_metabolism-active-days-share-im.result.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`
- Tests: `python3 -B -m unittest tools.build_loop.test_d143_work_order`; `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/test_d143_work_order.py`; `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d143-registry.json`; `git diff --check`
- Guardrails: artifact/work-order only; experiment lane; default OFF flag; no timer install; no production deploy; no push; no merge; no outreach; no secrets; no service control; no money movement.
- Risks: This does not itself improve the metric until James/council explicitly enables or implements the experiment and a later reviewed closeout helper or manual ritual produces real commits. It can still become metric gaming if closeout packets are allowed without meaningful work, so the verdict requires a meaningful-commit audit.
- Rollback: revert the listed files. Runtime mitigation is to leave `FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT` unset or `0`; no live activation exists in this build.
- Intent solved: d143's metabolism answer is converted into one concrete, reversible, reviewable work order instead of another parked prompt.
- Downstream intent unlocked: after review, the experiment can run for 14 days and produce a real `feature_outcome` row comparing active-day share against the d143 baseline.
