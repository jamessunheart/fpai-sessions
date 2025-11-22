# Mission: Mission Portal Sync

- **Status:** In-Progress
- **Priority:** P1 (High)
- **Assigned Role:** Ops Coordinator (with portal access)
- **Reference Docs:**
  - `docs/library/coordination/missions/MISSIONS_INDEX.md`
  - `docs/library/coordination/UNIFIED_EMPIRE_COMMAND.md`

## Objective
Mirror the new on-disk mission taxonomy (open → in-progress → done) inside the external mission portal so apprentices see the same queue.

## Current State
- Markdown system live under `orchestration/missions/`
- Portal still shows legacy "DO_THIS_NOW" backlog
- Webhooks documented inside `docs/library/coordination/missions/mission-007-daily-monitoring.json`

## Required Actions
1. Export current `missions.md` dashboard (see root of this folder).
2. Update portal categories / statuses to match (`open`, `in-progress`, `done`).
3. Schedule nightly sync leveraging `orchestration/scripts/backup-to-github.sh` or portal API.
4. Record completion evidence (screenshots or API response) inside `missions.md`.

## Deliverable
- Portal and repo show identical mission lists.
- Timestamped note inside `missions.md` confirming sync + next review date.
