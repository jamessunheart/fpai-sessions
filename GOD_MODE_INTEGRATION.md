# GOD MODE INTEGRATION SPECIFICATION
**Separation of Concerns: The Architect vs. The Hive**

## 1. CONCEPTUAL MODEL

### 🏛️ GOD MODE (The Architect's Sanctum)
*   **User:** YOU (The Architect).
*   **Access:** Exclusive, Biometric/Secure Key.
*   **Visibility:** Total (Can see Mission Control, Logs, Treasury, System State).
*   **Function:** High-level decision making, overrides, "Nuke" button, Treasury allocation.
*   **Integration:** "Ingests" the Inbox from Mission Control but presents it in a simplified "Zen" interface.

### 🚀 MISSION CONTROL (The Hive's Bridge)
*   **Users:** AI Agents (Apprentices), Human Delegates, PMs.
*   **Access:** Role-based (Public/Internal with Auth).
*   **Visibility:** Limited to active missions, status boards, and public queues.
*   **Function:** Coordination, Reporting, Handoffs.
*   **Role:** It is the "working floor" dashboard.

---

## 2. ARCHITECTURE

```mermaid
graph TD
    Architect[YOU] -->|Biometric/Auth| GodMode[GOD MODE UI (Port 8888)]
    
    subgraph "The Airlock"
        InboxJSON[core/STATE/INBOX.json]
    end
    
    subgraph "The Hive"
        MissionControl[Mission Control (Port 8080)]
        Agents[AI Swarm]
        Humans[Delegates]
    end
    
    GodMode -.->|Reads/Overrides| InboxJSON
    MissionControl -->|Writes Requests| InboxJSON
    MissionControl -->|Reads Status| InboxJSON
    
    Agents -->|Report Progress| MissionControl
    Agents -->|Request Approval| InboxJSON
```

## 3. THE INTEGRATION LOGIC

### A. The "Filter" (Your Inbox)
*   **Source:** `INBOX.json` (Shared State).
*   **God Mode View:**
    *   Shows *only* items tagged `requires: architect` or `sensitivity: high`.
    *   Everything else (peer review, standard QA) stays in Mission Control for Delegates/AI to handle.
    *   **UI:** "3 Decisions Pending" (Zen Mode).

### B. The "Shadow" (Monitoring)
*   God Mode has a "Periscope" view into Mission Control.
*   You can watch the Hive work without them seeing you.
*   You can "Veto" any active mission from God Mode, which sends a `STOP` signal to the Orchestrator.

---

## 4. IMPLEMENTATION PLAN

### Phase 1: The Separation (NOW)
1.  **Rename Port 8080 Service:** Keep it as "Mission Control" (The Working Dashboard).
2.  **Create "God Mode" Service (Port 8888):**
    *   New lightweight service `SERVICES/god-mode`.
    *   Strict Authentication (Different password/key).
    *   Simplified UI: "The Red Phone" + "The Ledger" + "The Filtered Inbox".

### Phase 2: The Routing
*   Update `orchestrator.py` to tag tasks:
    *   `level: 1` -> Auto/Log.
    *   `level: 2` -> Mission Control (Delegate can approve).
    *   `level: 3` -> **God Mode ONLY** (Treasury > $1k, Deploy to Prod, Constitution Change).

### Phase 3: The Interface
*   **Mission Control:** Shows "Waiting for Architect" for Level 3 tasks.
*   **God Mode:** Shows "Action Required" card.

---

## 5. DATA STRUCTURE UPDATE (`INBOX.json`)

```json
{
  "tasks": [
    {
      "id": "1",
      "title": "Deploy Droplet",
      "level": 2,  // Goes to Mission Control
      "status": "pending"
    },
    {
      "id": "2",
      "title": "Transfer $50k",
      "level": 3,  // Goes to GOD MODE
      "status": "pending"
    }
  ]
}
```

