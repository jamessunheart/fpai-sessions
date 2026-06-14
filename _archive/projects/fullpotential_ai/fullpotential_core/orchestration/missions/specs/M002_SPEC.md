# Mission: Restore Dashboard Frontend (M002)

## Overview
- **Priority:** P1
- **Status:** SPEC_REVIEW
- **Owner:** Haythem / Apprentice
- **Estimated Time:** 1.5-2 hours
- **Difficulty:** Advanced
- **Mission Type:** 👤 Human-Required

## Constitution Alignment
- **Principle:** **Autonomy over Dependency** — restoring the UI returns situational awareness to the Owner without manual routing.
- **Regenerative Impact:** A live dashboard lets humans steer missions faster, preventing waste and amplifying mission throughput.

## Objective
Locate the missing dashboard UI source for Droplet #2 and prepare it for deployment.

## Background & Context
This mission is part of the Full Potential AI ecosystem. Completing it will help advance our goal of building regenerative systems that empower humanity.

# Mission: Restore Dashboard Frontend (M002)

- **Priority:** P1
- **Status:** OPEN
- **Owner:** Haythem / Apprentice
- **Constitution Principle:** **Autonomy over Dependency** — restoring the UI returns situational awareness to the Owner without manual routing.
- **Regenerative Impact:** A live dashboard lets humans steer missions faster, preventing waste and amplifying mission throughput.
- **Objective:** Locate the missing dashboard UI source for Droplet #2 and prepare it for deployment.
- **Files/Systems:** `droplets/hteam/droplet-2/frontend`, `docs/library/resources/docs/autonomous-research-agent/ui`, mission portal.



## Prerequisites
- [ ] Git installed and configured
- [ ] Access to the FPAI_Cockpit repository
- [ ] Node.js 18+ and npm installed
- [ ] SSH access to deployment server

## Step-by-Step Instructions

### Step 1: Setup & Preparation
**Goal:** Prepare your environment

```bash
# Clone/pull latest code
cd /path/to/FPAI_Cockpit
git pull origin main

# Create a working branch
git checkout -b mission-[MISSION_ID]
```

**Expected Result:** Fresh codebase ready for changes

### Step 2: Recover or rebuild the dashboard frontend assets (...
**Goal:** Recover or rebuild the dashboard frontend assets (React/Vue/etc.).

**Files involved:**
- `droplets/hteam/droplet-2/frontend`
- `docs/library/resources/docs/autonomous-research-agent/ui`
- `mission portal.`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 3: Commit a `package.json` (and lockfile) under `drop...
**Goal:** Commit a `package.json` (and lockfile) under `droplets/hteam/droplet-2/frontend/`.

**Files involved:**
- `droplets/hteam/droplet-2/frontend`
- `docs/library/resources/docs/autonomous-research-agent/ui`
- `mission portal.`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 4: Document build + deploy steps so ops can include t...
**Goal:** Document build + deploy steps so ops can include the UI in the next bundle.

**Files involved:**
- `droplets/hteam/droplet-2/frontend`
- `docs/library/resources/docs/autonomous-research-agent/ui`
- `mission portal.`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 5: Testing & Verification
**Goal:** Ensure everything works correctly

```bash
# Run automated tests
pytest -v

# Check for linting issues
rg -i "TODO|FIXME|XXX" --type py
```

**Success Criteria:**
- [ ] All tests pass
- [ ] No new linting errors
- [ ] Manual verification complete

### Step 6: Submission
**Goal:** Submit your work for review

1. Commit all changes:
   ```bash
   git add -A
   git commit -m "Complete mission [MISSION_ID]: [brief description]"
   git push origin mission-[MISSION_ID]
   ```

2. Go to https://fullpotential.ai/services/harvester

3. Fill in:
   - Your name
   - Select this mission
   - Paste your GitHub repo URL
   - Add any notes

4. Click Submit and wait for automated review


## Deliverables Checklist
- [ ] Recover or rebuild the dashboard frontend assets (React/Vue/etc.).
- [ ] Commit a `package.json` (and lockfile) under `droplets/hteam/droplet-2/frontend/`.
- [ ] Document build + deploy steps so ops can include the UI in the next bundle.
- [ ] Code pushed to GitHub
- [ ] Submitted via Harvester
- [ ] Score 80+ on automated review

## Resources
**Related Files:**
- `droplets/hteam/droplet-2/frontend`
- `docs/library/resources/docs/autonomous-research-agent/ui`
- `mission portal.`

**Documentation:**
- [Mission Hub](https://fullpotential.ai/missions)
- [Contribution Guide](https://fullpotential.ai/missions/contribute)
- [Harvester](https://fullpotential.ai/services/harvester)

**Help:**
- Ask questions by creating a GitHub issue
- Check existing mission completions for examples

## Acceptance Criteria
| Criteria | Required | How to Verify |
|----------|----------|---------------|
| Core objective met | ✅ | Manual review |
| Tests pass | ✅ | Automated via Harvester |
| No secrets committed | ✅ | Automated scan |
| Documentation updated | ⚠️ Nice-to-have | Manual review |

## Notes & Warnings
- ⚠️ Keep API endpoints aligned with `/dashboard/api/` once backend is live.
- ⚠️ Coordinate with registry/orchestrator teams before pointing to production data.

---
*Generated: 2025-11-26 20:48*
*Spec Status: DRAFT - Requires human review before publishing*
*Mission ID: M002*
