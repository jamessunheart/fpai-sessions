# SPEC_d105_bandwidth-ledger-measures-recove Result

## Status
Done in working tree. Not pushed, merged, deployed, installed, or live-migrated.

## Files Changed
- `tools/bandwidth/__init__.py`
- `tools/bandwidth/routing_log.py`
- `tools/bandwidth/weekly_report.py`
- `tools/bandwidth/schema.sql`
- `tools/bandwidth/test_routing_log.py`
- `tools/bandwidth/test_weekly_report.py`
- `tools/router/route.py`
- `SERVICES/sunheart-brain/curator/jobs/digest.py`
- `core/STATE/BANDWIDTH_LEDGER.md`
- `core/BUILD/signals/bandwidth_ledger.json`
- `core/BUILD/signals/bandwidth_ledger.md`
- `core/BUILD/cron/fpai-bandwidth-ledger.service`
- `core/BUILD/cron/fpai-bandwidth-ledger.timer`
- `core/BUILD/specs/SPEC_d105_bandwidth-ledger-measures-recove.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d105_bandwidth-ledger-measures-recove.result.md`
- `docs/codex/HANDOFF.md`

## Summary
Added a private bandwidth ledger that measures recovered capacity from T1-handled routing decisions and tracks week-over-week T1 completion rate. `tools/bandwidth/routing_log.py` logs routing decisions without blocking callers, honors `BANDWIDTH_LEDGER_DISABLE=1`, appends to a repo JSONL fallback by default, and only writes to `brain_index.routing_log` when `BANDWIDTH_LEDGER_DB_WRITE=1` plus a DSN are explicitly configured.

`tools/bandwidth/weekly_report.py` aggregates routing rows by ISO week and task type, computes current vs previous T1 rate, estimates recovered T3-equivalent decisions/minutes, names current leak task types, and writes JSON/Markdown/state reports. The first generated repo report is `NO_DATA` because this branch has no live routing ledger history yet; it does not fabricate a trend.

Wired `tools/router/route.py` to log route outcomes best-effort: T1/completed for `draft-spec` and `route-build`, T3/escalated for gate/bless/escalation paths, and no write during router dry runs. Added a digest section that reads `core/STATE/BANDWIDTH_LEDGER.md` when present, plus reviewed weekly systemd timer artifacts. No timer was installed.

## Tests
- `python3 -B -m unittest tools.bandwidth.test_routing_log tools.bandwidth.test_weekly_report`
- `python3 -B -m unittest tools.router.test_route`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/bandwidth/__init__.py tools/bandwidth/routing_log.py tools/bandwidth/weekly_report.py tools/bandwidth/test_routing_log.py tools/bandwidth/test_weekly_report.py tools/router/route.py SERVICES/sunheart-brain/curator/jobs/digest.py`
- `bash -n core/BUILD/cron/fpai-bandwidth-ledger.service core/BUILD/cron/fpai-bandwidth-ledger.timer`
- `python3 -m tools.bandwidth.weekly_report`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/BUILD/signals/bandwidth_ledger.json`
- `git diff --check`

## Risks
- The live `brain_index.routing_log` migration was not applied in this sandbox; `tools/bandwidth/schema.sql` is a reviewed artifact for post-merge application.
- The first report is `NO_DATA` until real routing rows accumulate. Unit tests prove the week-over-week and recovered-capacity math with fixture evidence.
- Digest integration only surfaces the generated state file when present; it does not send a separate report or activate a timer.
- The T3-equivalent minute estimate is a simple default of 20 minutes per T1-completed routing decision; adjust later if measured operator-time data becomes available.

## Rollback
Revert the d105 files listed above. If the timer is installed later, disable/remove `fpai-bandwidth-ledger.timer` and `fpai-bandwidth-ledger.service`. If the schema is applied live and a full rollback is needed, export wanted rows first and then drop `brain_index.routing_log`.

## Intent Solved
The system now has a deterministic private ledger and weekly report path for seeing whether routing work is graduating to T1 instead of silently consuming higher-tier attention.

## Downstream Intent Unlocked
After merge and schema/timer activation, the build loop can compare week-over-week T1 completion rate and recovered T3-equivalent capacity before deciding which task classes should graduate to cheap local routing next.
