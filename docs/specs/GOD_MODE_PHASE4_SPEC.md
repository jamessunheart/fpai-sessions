# 👁️ GOD MODE PHASE 4: The All-Seeing Eye

**Objective:** Expand visibility into the financial and computational bloodstream of the system.

---

## 1. 💰 TREASURY (Financial Command)
**Goal:** Real-time visibility of capital deployment.

### Features
1.  **Headlines:**
    -   Total Value Locked (TVL).
    -   24h PnL (Profit/Loss).
    -   Liquid Cash.
2.  **Positions Board:**
    -   List of active trades/yield farms.
    -   Columns: Asset, Protocol, Size, ROI, Risk Score.
3.  **Allocation Ring:**
    -   Visual breakdown (e.g., 60% Stable, 30% Blue Chip, 10% Degen).

### Data Source
-   **File:** `core/STATE/TREASURY.json`
-   **Structure:**
    ```json
    {
      "tvl": 405000.00,
      "pnl_24h": 1250.00,
      "allocation": {"stable": 60, "crypto": 40},
      "positions": [
        {"asset": "ETH", "protocol": "AAVE", "size": 50000, "apy": 0.04},
        {"asset": "USDC", "protocol": "Curve", "size": 240000, "apy": 0.12}
      ]
    }
    ```

---

## 2. 📊 METRICS HUD (System Health)
**Goal:** Real-time telemetry of the infrastructure.

### Features
1.  **Server Vitals:**
    -   CPU Usage (%).
    -   RAM Usage (%).
    -   Disk Space.
2.  **Network Pulse:**
    -   Active Connections.
    -   Latency to key APIs (OpenAI, Anthropic, Blockchain nodes).
3.  **Agent Heart rate:**
    -   "BPM" of the collective (heartbeats per minute).

### Implementation
-   **Backend:** Use `psutil` to read system stats. Broadcast via WebSocket `stats_update`.

---

## 3. 🔬 DEEP ASSEMBLY (Microscope)
**Goal:** Inspect the "Muscle" work in detail.

### Features
1.  **Log Stream:**
    -   Clicking an agent node opens a "Terminal" modal showing its specific logs.
2.  **File Inspector:**
    -   See the exact file being modified by an agent.

---

## 🚀 Implementation Plan

### Backend
-   [ ] `get_treasury_data()`: Read `TREASURY.json`.
-   [ ] `get_system_metrics()`: Use `psutil`.
-   [ ] Update `watch_system_state` loop to include metrics.

### Frontend
-   [ ] **Treasury View:** New tab with Cards and Lists.
-   [ ] **HUD:** Floating overlay or Top Bar expansion.
-   [ ] **Refinement:** Make the Graph node clickable for details.

---

## 🎨 Aesthetic
*   **Treasury:** Gold/Green accents. Money data in monospace.
*   **Metrics:** Small, dense, high-refresh charts (Sparklines).






