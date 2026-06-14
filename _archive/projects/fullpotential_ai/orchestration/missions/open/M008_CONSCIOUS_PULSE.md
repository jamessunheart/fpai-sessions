# M008 – Activate Conscious Pulse Daemon

- **Mission ID:** M008_CONSCIOUS_PULSE  
- **Title:** Activate Conscious Pulse Daemon  
- **Priority:** P2 (Autonomy)  
- **Owner:** I PROACTIVE / Consciousness Core  
- **Status:** OPEN  

---

## Objective

Install the **Conscious Pulse “Heartbeat” daemon** that runs every 15 minutes so the system keeps itself honest by:

- Polling `/self/state` to understand current load + health.  
- Surfacing unresolved commitments from `/memory/open-loops`.  
- Triggering `/memory/reflect` for fresh insights.  
- Posting any “Realizations” to the Town Crier channel (`ALERTS.md`).

---

## Targets

1. **Create `conscious_pulse.py` daemon**
   - Location: `fullpotential_core/orchestration/tools/conscious_pulse.py` (or equivalent ops/tools directory).
   - Responsibilities:
     - Run an infinite loop with configurable interval (default: 15 minutes).
     - Use environment variables or config to know:
       - Base URL for I PROACTIVE (e.g., `http://localhost:8400` or remote IP).
       - Paths for logs and alerts (e.g., `docs/coordination/ALERTS.md`).

2. **The Pulse Loop (every 15 minutes)**
   - On each tick:
     1. **Self-State Check**
        - `GET /self/state`
        - Log a compact snapshot to a rotating log (e.g., `PULSE_LOG.md` or JSON file).
     2. **Open Loops Scan**
        - `GET /memory/open-loops?limit=50`
        - Identify **stale loops** (e.g., age > N hours/days once timestamps are tracked).
     3. **Reflection Trigger**
        - `POST /memory/reflect`
        - Receive reflection payload (active projects, open loop count, sample loops).

3. **Town Crier – Realizations to ALERTS.md**
   - Detection rule (V1 heuristic):
     - If reflection shows:
       - `total_open_loops` above a threshold (e.g., > 10), or
       - A project with many episodes / loops and no recent revenue,
     - Then append an entry to `ALERTS.md`:
       - Timestamp.
       - Short “Realization” sentence (e.g., “System heavily focused on I MATCH, many open loops, no revenue recorded in last N reflections.”).
       - Link to relevant endpoints (e.g., `/self/state`, `/memory/open-loops`).
   - Ensure this is **append-only** and safe if the daemon crashes/restarts.

---

## Implementation Notes

- **Runtime:**  
  - V1 can be a simple long-running Python process launched via `tmux`, systemd, or a cron-style wrapper script (`*/15 * * * * curl ...` as a minimal variant).
- **Safety:**  
  - Time out HTTP calls and handle failures gracefully (log and continue; never exit the loop on transient errors).
- **Configurability:**  
  - Interval, alert thresholds, and target URLs should be configurable via env vars or a small config file (`pulse_config.json`).

---

## Definition of Done

1. `conscious_pulse.py` runs and logs at least one full pulse cycle without error:
   - Successfully hit `/self/state`, `/memory/open-loops`, `/memory/reflect`.
2. `ALERTS.md` exists and receives entries when reflection crosses configured thresholds.
3. Pulse interval and thresholds can be adjusted **without code changes** (via config/env).
4. Documented start/stop instructions (e.g., `README` section or `scripts/start_pulse.sh`) so the daemon can be reliably operated on any deployment.



