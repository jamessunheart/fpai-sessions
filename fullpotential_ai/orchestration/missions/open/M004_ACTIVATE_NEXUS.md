# Mission: Activate Nexus Optimizer (M004)

- **Priority:** P2 (Strategic Evolution)
- **Status:** OPEN
- **Owner:** Suresh / AI Builder
- **Objective:**
  1. Deploy Droplet #13 (Nexus) in the refreshed /opt/fpai layout.
  2. Implement `optimizer_loop.py` with:
     - Agent A: reads system state, treasury balance, and mission log.
     - Agent B: drafts improvement missions (e.g., "Rebalance Portfolio").
  3. Pipe proposals into Town Crier (ALERTS.md + future Slack) for human validation.

## Deliverables
- Nexus service online with health-checked `/optimizer/health` endpoint.
- `optimizer_loop.py` scheduled (cron/systemd) with clear run cadence.
- Generated missions show up in `/orchestration/missions/open/` using proper naming + metadata.

## Notes
- Keep Agent prompts under the Constitutional limits; Aggressive experimentation must remain sandboxed.
- Coordinate with Treasury (M001) to avoid conflicting key usage.
