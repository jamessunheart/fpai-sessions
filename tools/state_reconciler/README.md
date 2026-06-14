# State Reconciler

Repo-side helpers for noticing drift between the Full Potential OS state
surfaces. These tools report and gate; they do not auto-fix SSOTs.

## Drift Detector

Dry-run, writes nothing:

```bash
python3 -B tools/state_reconciler/cron.py --dry-run --json
```

Write the repo mirror report and open a deduped human-edge gate only when a
hard freshness threshold is crossed:

```bash
python3 -B tools/state_reconciler/cron.py --write-report --json
```

Print the non-installed schedule snippet:

```bash
python3 -B tools/state_reconciler/cron.py --schedule
```

## Non-Installed Schedule Snippet

James/Ember can install this later after reviewing the diff:

```cron
# Daily at 07:10 local time.
10 7 * * * cd /Users/jamessunheart/FPAI_Cockpit && /usr/bin/env python3 -B tools/state_reconciler/cron.py --write-report
```

Do not install this from a Codex build run. Installation is a live background
job decision.

