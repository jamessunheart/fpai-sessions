# ASSEMBLY LINE STANDARD OPERATING PROCEDURE (SOP)

## THE FACTORY MODEL

This SOP defines the flow of work from ideation to production in the FPAI Factory.

### PHASE 1: ARCHITECT QUEUES MISSION
- The **Architect** (Human or AI High-Level Planner) defines the objective.
- A **Mission** is created and logged in the `missions/` directory.
- Requirements are broken down into discrete tasks in the **Orchestrator**.

### PHASE 2: APPRENTICE BUILDS IN SATELLITE REPO
- An **Apprentice** (AI Builder) claims the task.
- Work is performed in a designated **Satellite Repo** (isolated environment).
- This ensures the Core remains stable and clean during rapid iteration.
- Tests are written and passed locally in the satellite.

### PHASE 3: SYSTEM HARVESTS
- Once the Apprentice signals completion, the **System** engages the Airlock.
- **Tool:** `orchestration/tools/harvest_repo.py` (or similar) is executed.
- The system pulls the code from the Satellite Repo into a staging area in the Core.
- Context and structure are mapped to the Core's standards.

### PHASE 4: SYSTEM VERIFIES & DEPLOYS
- **Verification:** Automated tests run in the Core environment to ensure integration stability.
- **Review:** (Optional) A Reviewer checks for compliance with the Constitution.
- **Deployment:** Upon success, the code is merged to `main` and deployed to active services.
- **Cycle Complete:** The system updates the Registry and is ready for the next Mission.
