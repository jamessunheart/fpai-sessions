# Human Review Checklist

This checklist is adapted from patterns in `docs/library/coordination/missions/MISSIONS_INDEX.md`, `mission-007-daily-monitoring.json`, and `docs/library/coordination/MEMORY/PRINCIPLES.md`.

## Pre-Flight
- [ ] Read the associated mission brief and confirm status bucket (open / in-progress / done)
- [ ] Confirm no secrets or personal credentials are required; if they are, escalate instead of proceeding
- [ ] Pull latest main branch and sync `missions.md`

## Review Steps
1. **Context:** Skim related specs / SOPs (`specs/*`, `docs/library/coordination/missions/*`) so you understand intent.
2. **Action:** Execute the numbered steps in the mission file.
3. **Evidence:** Capture terminal output, screenshots, or links proving completion.
4. **Regression Scan:** Run `rg` or relevant tests to ensure no unintended side effects.

## Post-Review
- [ ] Update the mission file with outcome + timestamp
- [ ] Add a note under the relevant row in `missions.md`
- [ ] If additional work is needed, either reopen the mission or spawn a follow-up in `open/`

## Reporting Format
```
Date: 2025-11-21
Reviewer: <name/handle>
Mission: <link to file>
Outcome: ✅ / ⚠️
Notes: <summary + file list>
```

Keep this template lightweight so humans can move fast while preserving the audit trail the coordination specs expect.
