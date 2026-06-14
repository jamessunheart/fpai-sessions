# 🧠 GOD MODE PHASE 3: Brain & Voice Upgrade

**Objective:** Transform static placeholders into high-leverage command interfaces.

---

## 1. 🧠 THE BRAIN (Strategy Command)
**Goal:** Visual management of the Autonomous Assembly Line.

### Features
1.  **Live Kanban Board**
    -   **Columns:**
        -   `📥 INTENT` (New ideas, unassigned)
        -   `⚙️ BUILDING` (Active claims, Muscle working)
        -   `✅ DEPLOYED` (Completed missions)
    -   **Data Source:**
        -   `INTENT`: Files in `docs/coordination/intents/`
        -   `BUILDING`: Files in `docs/coordination/claims/` (matched to intents)
        -   `DEPLOYED`: Logged completions.

2.  **Interactive Mission Creation**
    -   **"New Mission" Button:** Opens a modal.
    -   **Fields:** Objective, Priority (Score), Description.
    -   **Action:** Generates `intent.json`.

3.  **Drag & Drop (Future)**
    -   Dragging `INTENT` -> `BUILDING` triggers the Executor (via priority score update).

### Visuals
-   **Cards:** Glass-morphism panels.
-   **Indicators:**
    -   Green Pulse = Active Build.
    -   Red Border = Failed/Blocked.
    -   Progress Bar = Completion %.

---

## 2. 💬 THE COMM LINK (Chat Console)
**Goal:** A "Command Line" for natural language control.

### Features
1.  **Rich Message Stream**
    -   **System Broadcasts:** `[SYS]` prefix, distinct color.
    -   **Agent Reports:** `[MUSCLE]`, `[BRAIN]` avatars.
    -   **Alerts:** High-priority errors in Red.

2.  **Slash Commands (Quick Actions)**
    -   `/status` -> Returns system health.
    -   `/stop` -> Emergency Stop.
    -   `/clear` -> Clears chat view.

3.  **Input Experience**
    -   Auto-focus on load.
    -   "Matrix" typography.
    -   History navigation (Up/Down arrows).

---

## 🛠️ Technical Implementation

### Backend (`main.py`)
-   [ ] `get_kanban()`: Aggregates Intents + Claims into a board structure.
-   [ ] `create_intent()`: Endpoint to write new mission files.

### Frontend (`App.jsx` + Components)
-   [ ] `KanbanBoard.jsx`: Grid layout with mapping logic.
-   [ ] `MissionCard.jsx`: The individual item view.
-   [ ] `CreateMissionModal.jsx`: Form for new work.
-   [ ] `ChatConsole.jsx`: Enhanced message rendering.

---

## 🎨 Aesthetic
*   **Brain:** Deep Purple/Blue gradients.
*   **Chat:** Monospace, high contrast, terminal green/amber accents.

