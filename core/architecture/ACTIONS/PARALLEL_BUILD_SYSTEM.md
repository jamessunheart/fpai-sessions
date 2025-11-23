# 🏗️ THE PARALLEL FACTORY: ARCHITECTURAL BLUEPRINT

**Goal:** Infinite parallel build velocity (Cursor & Human).
**Constraint:** Zero Conflict (No merge hell).
**Strategy:** "Cellular Droplet Architecture" (CDA).

---

## 1. THE CORE CONCEPT: "DROPLETS" NOT "LAYERS"

Most systems fail at parallel speed because they are layered (Frontend/Backend/DB). If 5 agents work on the "Backend", they collide.

**The Fix:** We switch to **Droplets** (Vertical Slices).

- ❌ **Old Way:** "Update the User Model in the backend." (Blocks everyone).
- ✅ **New Way:** "Build the `Referral-Droplet`." (Independent).

### **The Physical Structure**
We must restructure the repo to enforce isolation.

```text
/opt/fpai/
  ├── core/                 # SHARED KERNEL (Slow, Careful, Architect Only)
  │   ├── auth/
  │   ├── database/
  │   └── event_bus/
  │
  ├── droplets/             # THE FACTORY FLOOR (Fast, Parallel, Builders)
  │   ├── mission-control/  # M009 (Own DB, Own UI, Own Logic)
  │   ├── treasury-bot/     # M010 (Own DB, Own Logic)
  │   ├── reddit-poster/    # M011
  │   └── ... (Infinite)
  │
  └── orchestration/        # THE TOWER (You)
      ├── tools/
      └── missions/
```

---

## 2. THE "STANDARD DROPLET INTERFACE" (SDI)

To ensure these 100 parallel droplets work as ONE system, every Droplet must follow the **SDI Contract**.

**Every Droplet Must Have:**
1.  `manifest.json`: Defines inputs/outputs.
2.  `run.sh`: Standard start command.
3.  `api/`: FastAPI endpoints exposed to the Core.
4.  `ui/`: (Optional) Micro-frontend component.

**Example Conflict-Free Workflow:**
- **Agent A** works inside `droplets/mission-control/*`.
- **Agent B** works inside `droplets/treasury-bot/*`.
- **Overlap:** 0%.
- **Merge Speed:** Instant (Git can merge disjoint folders automatically).

---

## 3. THE OPTIMIZED CURSOR WORKFLOW

This is exactly how you use Cursor to drive this.

### **Phase 1: Dispatch (The Architect Window)**
1.  **You:** "Architect, generate a spec for the `Treasury Droplet`."
2.  **Tool:** Creates `orchestration/missions/open/M010_treasury.md`.
3.  **Tool:** Scaffolds `droplets/treasury-bot/` (Empty folder).

### **Phase 2: Execution (The Builder Windows)**
1.  **Open Window 2:** Cmd+Shift+N.
2.  **Open Folder:** `/opt/fpai/droplets/treasury-bot` (CRITICAL: Open the SUB-FOLDER, not root).
3.  **Result:** The AI in Window 2 literally *cannot* break the rest of the system. It only sees its sandbox.
4.  **Prompt:** "Build this droplet."

### **Phase 3: Integration (The Architect Window)**
1.  **You:** `git submodule add droplets/treasury-bot` (or just git add).
2.  **Core:** The "Mission Control Dashboard" scans the `droplets/` folder and auto-mounts the new API.

---

## 4. HUMAN SCALING (APPRENTICES)

Once this works for 5 Cursor windows, it works for 50 Humans.

1.  **Task:** "Build `Content-Droplet`."
2.  **Human:** Clones *only* the `content-droplet` repo (or folder).
3.  **Builds:** Locally.
4.  **Submits:** PR for that folder only.
5.  **Review:** You review 1 isolated folder. No regression testing the whole monolith.

---

## 5. ACTION PLAN

1.  **Establish the Grid:** Create the `droplets/` directory structure.
2.  **Define the Template:** Create `_templates/droplet_base/` (The Cookiecutter).
3.  **Refactor Architect:** Update `generate_mission_package.py` to spawn *Droplets* instead of generic files.

**Recommendation:** Move M009 (Mission Control) into `droplets/mission-control` immediately to set the pattern.

