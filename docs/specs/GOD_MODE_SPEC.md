# 🏛️ GOD MODE: The Unified Command Center - SPEC

**Version:** 2.0 (Visual Evolution)
**Status:** PROPOSED
**Target:** `SERVICES/god-mode` (Replacing Mission Control)
**Port:** 3000 (Gold Standard)

---

## 🎯 The Objective
Transcend the terminal. Create a **High-Fidelity, Sovereign Interface** that unifies the Architect (You) with the entire Autonomous Assembly Line.

**Philosophy:** "The Whole lives with me."
It is not just a dashboard; it is a **Cockpit**.

---

## 🏗️ The 4 Pillars of God Mode

### 1. 🧠 STRATEGY (The Brain)
**Visual:** A Living Kanban / Node Graph.
-   **Input:** You dispatch "Intents" (Missions).
-   **Display:**
    -   **Queued:** Ideas waiting for pickup.
    -   **Active:** Missions currently being strategized.
    -   **Completed:** History of evolution.
-   **Action:** Drag-and-drop prioritization.

### 2. 💪 EXECUTION (The Muscle)
**Visual:** A Real-Time System Map (Force-Directed Graph).
-   **Display:**
    -   **Agents:** Pulsing nodes (Green = Working, Yellow = Idle).
    -   **Connections:** Lines showing who is talking to whom (via coordination mesh).
    -   **Logs:** Live stream of `heartbeats` visible on hover.
-   **Action:** Click a node to see its current thought process (tail logs).

### 3. 📬 INBOX (Approvals)
**Visual:** "Tinder for Ops" / Executive Card Stack.
-   **Purpose:** High-speed decision making.
-   **Display:** Cards for:
    -   "Approve Deployment to Production?"
    -   "Review Blog Post Draft?"
    -   "Authorize 500 USDC Transfer?"
-   **Action:** `[Approve]` (Green), `[Reject]` (Red), `[Edit]` (Yellow).

### 4. 💬 COMM LINK (The Voice)
**Visual:** Unified "Matrix-Style" Chat Stream.
-   **Display:**
    -   Broadcasts from all agents.
    -   Direct mentions to You.
    -   Error alerts.
-   **Action:** Type natural language commands ("Stop all builds", "Status report", "Optimize database").
-   **Backend:** Writes to `docs/coordination/messages/broadcast/`.

---

## 🛠️ Technical Architecture

### Frontend (The Glass)
**Stack:** React + Vite + TailwindCSS + Framer Motion.
-   **Why?** Fluid animations, real-time state updates, "Sci-Fi" aesthetic.
-   **Components:**
    -   `SystemMap.tsx`: D3.js or React Flow for the agent graph.
    -   `CommandTerminal.tsx`: A "Quake-style" drop-down chat console.
    -   `ApprovalStack.tsx`: Swipeable cards for the Inbox.

### Backend (The Nervous System)
**Stack:** FastAPI (Python) + WebSocket.
-   **Aggregator:** Reads `docs/coordination/*` (The Mesh).
-   **Socket:** Pushes file changes (intents, claims, messages) to the frontend instantly (no refresh needed).
-   **Controller:** Writes your actions back to the file system.

### Data Flow (The Sacred Loop)
1.  **Read:** Backend watches `docs/coordination/` files.
2.  **Push:** WebSocket sends `UPDATE` event to Frontend.
3.  **Render:** React updates the Graph/Inbox instantly.
4.  **Act:** You click "Approve".
5.  **Write:** Backend updates `INBOX.json` or creates `claim`.

---

## 🚀 Implementation Roadmap

### Phase 1: The Foundation (Skeleton)
-   [ ] Scaffold `SERVICES/god-mode` (React + FastAPI).
-   [ ] Implement WebSocket "File Watcher" for real-time updates.
-   [ ] Basic "Status Board" view (Muscle).

### Phase 2: The Interaction (Inbox & Chat)
-   [ ] Build `INBOX.json` API.
-   [ ] Build `ApprovalCard` UI.
-   [ ] Build `ChatConsole` UI (Reading/Writing broadcast JSONs).

### Phase 3: The Visualization (Brain & Map)
-   [ ] Implement Force-Directed Graph for active agents.
-   [ ] Implement Kanban for Strategy Intents.

### Phase 4: The Sovereign Launch
-   [ ] `GOD_MODE_GUI.sh` one-click launcher.
-   [ ] Auto-open `http://localhost:3000`.

---

## 🎨 User Experience (The "Vibe")
-   **Dark Mode Only.** Deep space blues/purples.
-   **Monospace Fonts** for data (JetBrains Mono).
-   **Fluid Motion:** Cards slide away, nodes pulse, text streams in.
-   **Sound FX:** Subtle clicks/beeps (optional) for "Mission Control" feel.

*The System is no longer a tool you use. It is a place you inhabit.*

