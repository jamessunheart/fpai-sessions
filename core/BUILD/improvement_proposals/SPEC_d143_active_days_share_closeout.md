# SPEC_d143 Work Order - Active Days Share Closeout Experiment

## Purpose

Improve the weakest measured conversion, `active_days_share`, without gaming the metric or activating production automation.

Baseline from the queued d143 metabolism prompt: `9/14` days with commits, value `0.642857`, target `1.0`, health `0.6429`.

## Single Experiment

Run a 14-day OFF-by-default daily closeout experiment:

- Flag: `FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT=0` by default.
- Lane: experiment only.
- Owner action when explicitly enabled: each local workday ends with one reviewable closeout packet if meaningful buildstream work happened that day.
- Closeout packet shape: a small commit-ready repo artifact that records the day, one shipped or reviewable buildstream change, tests run, and the next measurement check.
- Hard stop: no packet is created for empty work, pure metric padding, production deploys, outreach, secrets, money movement, or irreversible actions.

This is one change: make "daily closeout packet" the experiment-lane default for days that already had real buildstream work but risk ending without a commit.

## OFF Flag Behavior

When `FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT` is unset or set to `0`, nothing runs and no files are written.

When set to `1`, the experiment may be run manually or by a reviewed local-only helper in a later build. This work order does not install a timer, push a branch, merge code, or deploy production.

## Acceptance Criteria

- Exactly one experiment is proposed: daily closeout packet for real buildstream work.
- The experiment remains OFF by default behind `FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT=0`.
- No production deploy, push, merge, outreach, secrets access, service control, or money movement is part of this work order.
- A closeout packet is valid only when it cites real repo work and a test or explicit reason tests were not run.
- A valid packet is reviewable and reversible as a normal repo diff.
- The experiment records a `feature_outcome` row after the measurement window with baseline, observed value, delta, verdict, and notes on whether commits represented real work.

## Measurement Plan

Baseline:

- Metric: `active_days_share`
- Source: `tools/metrics/conversion_snapshot.py` via `git log`
- Baseline value: `9/14 = 0.642857`
- Window: the 14 days before d143

Observation:

- Run `python3 -B tools/metrics/conversion_snapshot.py` after 14 calendar days of the enabled experiment.
- Read the new `active_days_share` value from `~/.config/fpai/metrics/conversion_latest.json`.
- Compare observed value against baseline.
- Audit the commits in the same 14-day window and count how many were meaningful buildstream or proof artifacts.

Verdict rules:

- `improved`: observed value is at least `11/14` and at least 90% of active-day commits are meaningful buildstream or proof artifacts.
- `flat`: observed value is `9/14` or `10/14`, or meaningful-commit share is below 90%.
- `regressed`: observed value is below `9/14`.
- `invalid`: the improvement came mainly from empty commits, production pushes, unreviewed deploys, outreach, secrets access, money movement, or other prohibited activity.

Ledger row to append after observation:

```json
{"event":"feature_outcome","metric_name":"active_days_share","spec_id":"SPEC_d143_metabolism-active-days-share-im","baseline":0.642857,"observed":"<fill after 14 days>","delta":"<observed - baseline>","verdict":"<improved|flat|regressed|invalid>","detail":"14-day OFF-flag closeout experiment; audit meaningful commit share before verdict"}
```

## Rollback

Disable or leave unset `FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT`.

Revert this work-order file, the d143 result file, the d143 registry entry, the d143 handoff entry, and any later helper that implements the experiment. Delete any unmerged closeout packet diffs created by the experiment. Do not rewrite shared git history.

## Review Gate

James/council review remains required before any go-live. Production activation is explicitly out of scope for d143.
