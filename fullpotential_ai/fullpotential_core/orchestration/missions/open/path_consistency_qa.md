# Mission: Path Consistency QA

- **Status:** Open
- **Priority:** P0 (Critical)
- **Human Role:** Technical Editor / QA Reviewer
- **Refer to:** `docs/library/coordination/missions/MISSIONS_INDEX.md` for cadence + reporting norms

## Objective
Verify that every human-facing instruction reflects the new unified paths (`agents/services/`, `core/applications/`, `droplets/*`). Flag and fix any regressions that slipped past the automated sweep.

## Scope & Files
- `docs/guides/`
- `docs/status/`
- `orchestration/tools/*.sh`
- `orchestration/scripts/*.sh`
- Any Markdown surfaced in Git diffs that reference operational paths

## Steps
1. Follow the review checklist in `orchestration/missions/templates/human_review_checklist.md`.
2. Use `rg -n "fullpotential" docs orchestration` to spot stale absolute paths.
3. Update references (or open a PR/issue) when you find anything outside the canonical tree.
4. Log findings + actions in `missions.md` under the "Updates" note.

## Deliverable
- Updated files (or documented issues) proving no instructions reference legacy service paths or backup repo names.
- Reviewer notes appended in the mission dashboard.
