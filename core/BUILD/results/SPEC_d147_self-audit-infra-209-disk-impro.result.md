# SPEC_d147_self-audit-infra-209-disk-impro Result

Status: done in working tree / awaiting review + merge.

Read-only host-209 disk-growth reporter added. The post-merge activation runs only
on `209.74.93.72`; off-target hosts append a skipped ledger row and do not run `df`
or `du`. On 209 it captures filesystem usage, ranks candidate directories, computes
growth against the prior JSON snapshot when available, writes JSON/Markdown reports,
and appends one ops-ledger row. Cleanup output is proposal-only and quarantine-first.

Tests:

- `python3 -B -m unittest tools.infra.test_report_disk_growth_209` (4 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/infra/report_disk_growth_209.py tools/infra/test_report_disk_growth_209.py`
- `bash -n core/BUILD/activate/SPEC_d147_self-audit-infra-209-disk-impro.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d147-registry.json`
- off-target CLI smoke with `FPAI_D147_HOST_IPS=10.0.0.5 python3 -B -m tools.infra.report_disk_growth_209 --repo-root . --ops-ledger /tmp/d147-ops-ledger.jsonl --record`
- ASCII check for new/touched d147 files
- `git diff --check`

Risk: this sandbox is not `209.74.93.72`, so no live directory sizes were collected
here. The first target-host run may treat all paths as new if no prior
`/opt/fpai-build/state/d147_disk_209_snapshot.json` exists; the second run will show
real deltas. The helper may report partial `du` warnings for permission-denied paths,
but still preserves available stdout.

Rollback: revert this branch. Runtime cleanup is limited to removing generated
read-only artifacts on 209:
`/opt/fpai-build/state/d147_disk_209_snapshot.json`,
`/opt/fpai-build/reports/d147_disk_209_report.json`, and
`/opt/fpai-build/reports/d147_disk_209_report.md`.
