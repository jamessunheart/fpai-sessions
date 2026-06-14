# ⚡ THE FACTORY MODEL: PARALLEL EXECUTION GUIDE

**Goal:** Build at light speed by running multiple autonomous "cells" simultaneously.
**Role:** You are the "Mission Controller" (Orchestrator).
**Constraint:** No overlap (files touched by Cell A must not be touched by Cell B).

---

## 1. THE WORKFLOW (CELLULAR PARALLELISM)

Instead of one linear chat, use **Multiple Windows** as independent workers.

### **WINDOW 1: ORCHESTRATION (The Tower)**
- **Role:** Planning, generating missions, merging code.
- **Tools:** `generate_mission_package.py`, Git.
- **Action:**
  1. Run: `python3 orchestration/tools/generate_mission_package.py "Build Feature X"`
  2. Review: Check `orchestration/missions/open/M00X_...md`.
  3. **Dispatch:** Assign to a new window.

### **WINDOW 2, 3, 4...: THE BUILDERS (The Cells)**
- **Role:** Execution only. Focused on ONE mission.
- **Setup:**
  1. Open New Window: `Cmd + Shift + N` (Mac) / `Ctrl + Shift + N` (Win).
  2. Open Folder: Open the project root (same for all).
  3. **Composer (Cmd + I):** Drag the Mission File (`M00X.md`) into the chat.
  4. **Prompt:** "You are Builder M00X. Read this mission file. Execute Step 1."

---

## 2. AVOIDING CONFLICTS (The Golden Rule)

To run 5 paths at once, they must not touch the same wires.

**✅ SAFE Parallel Pairs:**
- **Cell 1:** "Build Frontend Login Page" (`frontend/pages/login.tsx`)
- **Cell 2:** "Build Backend Auth API" (`backend/auth.py`)
- **Cell 3:** "Write Documentation" (`docs/`)
- **Cell 4:** "Create Marketing Script" (`orchestration/tools/`)

**❌ DANGEROUS Parallel Pairs:**
- **Cell 1:** "Refactor User Model"
- **Cell 2:** "Add field to User Model"
- *(Both touch `models.py` → Merge Conflict Hell)*

**Your Job as Controller:** Ensure M001 and M002 target different files.

---

## 3. MERGING (The Heartbeat)

When a Cell finishes:
1. **Cell Window:** "I have finished M00X."
2. **Cell Window:** `git add . && git commit -m "Complete M00X"`
3. **Orchestration Window:** `git pull` (or merge the branch).
4. **Close Cell Window.**

---

## 4. MISSION CONTROL (New!)

We are building **Mission M009** (Mission Control Dashboard) to visualize this.
It will show you:
- 🟢 M001: In Progress (Files: `frontend/*`)
- 🟢 M002: In Progress (Files: `backend/*`)
- 🔴 M003: Blocked (Conflict with M001)

**Start M009 now to build this visualization.**

