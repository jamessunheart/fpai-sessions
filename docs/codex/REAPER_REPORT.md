# Cruft Reaper Report

*Generated: `2026-06-10T11:31:17+00:00` · repo: `/Users/jamessunheart/FPAI_Cockpit`*

🔴 **REPORT ONLY. James approves any deletion, stop, archive, untrack, or .gitignore edit.**

## Scan Settings

- stale service threshold: `90d`
- oversized path threshold: `512.0 MB`
- systemd evidence: systemctl unavailable on this host

## Ranked Kill-List Candidates

| Rank | Candidate | Reason | Evidence | Suggested action | Score |
|---:|---|---|---|---|---:|
| 1 | `.claude` | `size` | 1.1 GB >= threshold 512.0 MB; last commit age 1d | review for archive/untrack split after James approval | 1087.32 |
| 2 | `SERVICES` | `size` | 770.8 MB >= threshold 512.0 MB; last commit age 1d | review for archive/untrack split after James approval | 779.39 |
| 3 | `SERVICES/mission-control/venv` | `tracked-artifact` | 1268 tracked artifact file(s); last commit age 192d; size 47.8 MB | untrack after James approval; add ignore rule separately | 149.87 |
| 4 | `overnight-logs` | `tracked-artifact` | 2 tracked artifact file(s); last commit age 200d; size 14.2 KB | untrack after James approval; add ignore rule separately | 0.32 |
| 5 | `.archive/deprecated/coordination-2025-11/overnight-logs` | `tracked-artifact` | 1 tracked artifact file(s); last commit age 41d; size 101 B | untrack after James approval; add ignore rule separately | 0.15 |
| 6 | `_archive/projects/fullpotential_ai/fullpotential_core/docs/library/coordination/overnight-logs` | `tracked-artifact` | 1 tracked artifact file(s); last commit age 30d; size 101 B | untrack after James approval; add ignore rule separately | 0.13 |
| 7 | `_archive/projects/fullpotential_ai/fullpotential_core/orchestration/logs` | `tracked-artifact` | 2 tracked artifact file(s); last commit age 30d; size 14.3 KB | untrack after James approval; add ignore rule separately | 0.13 |

## .gitignore Suggestions

```gitignore
logs/
overnight-logs/
venv/
```

_Suggestion only. This report did not edit `.gitignore`._

## Guardrails

- No files were deleted.
- No services were stopped or disabled.
- No files were untracked.
- No `.gitignore` changes were applied.
