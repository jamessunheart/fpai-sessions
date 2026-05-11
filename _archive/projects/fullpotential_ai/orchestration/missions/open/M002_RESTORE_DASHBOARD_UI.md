# Mission: Restore Dashboard Frontend (M002)

- **Priority:** P1
- **Status:** OPEN
- **Owner:** Haythem / Apprentice
- **Constitution Principle:** **Autonomy over Dependency** — restoring the UI returns situational awareness to the Owner without manual routing.
- **Regenerative Impact:** A live dashboard lets humans steer missions faster, preventing waste and amplifying mission throughput.
- **Objective:** Locate the missing dashboard UI source for Droplet #2 and prepare it for deployment.
- **Files/Systems:** `droplets/hteam/droplet-2/frontend`, `docs/library/resources/docs/autonomous-research-agent/ui`, mission portal.

## Deliverables
1. Recover or rebuild the dashboard frontend assets (React/Vue/etc.).
2. Commit a `package.json` (and lockfile) under `droplets/hteam/droplet-2/frontend/`.
3. Document build + deploy steps so ops can include the UI in the next bundle.

## Notes
- Keep API endpoints aligned with `/dashboard/api/` once backend is live.
- Coordinate with registry/orchestrator teams before pointing to production data.
