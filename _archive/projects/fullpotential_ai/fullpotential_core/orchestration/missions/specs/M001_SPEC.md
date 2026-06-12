# Mission: Activate Treasury (M001)

## Overview
- **Priority:** P0
- **Status:** SPEC_REVIEW
- **Owner:** Treasury Operator
- **Estimated Time:** 1-1.5 hours
- **Difficulty:** Advanced
- **Mission Type:** 👤 Human-Required

## Constitution Alignment
- **Principle:** **Optimization over Extraction** — every trade should expand shared capital rather than drain reserves.
- **Regenerative Impact:** Magnet simulation unlocks safe treasury growth experiments that can fund human + AI relief missions.

## Objective
Prime Magnet trading stack with Binance testnet keys and confirm vault automation.

## Background & Context
This mission is part of the Full Potential AI ecosystem. Completing it will help advance our goal of building regenerative systems that empower humanity.

# Mission: Activate Treasury (M001)

- **Priority:** P0
- **Status:** Ready for Owner Input
- **Owner:** Treasury Operator
- **Constitution Principle:** **Optimization over Extraction** — every trade should expand shared capital rather than drain reserves.
- **Regenerative Impact:** Magnet simulation unlocks safe treasury growth experiments that can fund human + AI relief missions.
- **Objective:** Prime Magnet trading stack with Binance testnet keys and confirm vault automation.
- **Files/Systems:** `droplets/hteam/droplet-3/`, `infra/secrets.vault.example.json`, `orchestration/tools/inject_vault.py`, `/opt/fpai/env/magnet.env`
- **Dependencies:** Registry + Orchestrator live, secrets vault template ready.



## Prerequisites
- [ ] Git installed and configured
- [ ] Access to the FPAI_Cockpit repository
- [ ] Python 3.10+ installed
- [ ] Binance testnet account and API keys
- [ ] Dependencies completed: Registry + Orchestrator live, secrets vault template ready.

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

### Step 2: Copy `infra/secrets.vault.example.json` to `infra/...
**Goal:** Copy `infra/secrets.vault.example.json` to `infra/secrets.vault.json` locally.

**Files involved:**
- `droplets/hteam/droplet-3/`
- `infra/secrets.vault.example.json`
- `orchestration/tools/inject_vault.py`
- `/opt/fpai/env/magnet.env`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 3: Insert Binance testnet API key/secret plus Redis U...
**Goal:** Insert Binance testnet API key/secret plus Redis URL.

**Files involved:**
- `droplets/hteam/droplet-3/`
- `infra/secrets.vault.example.json`
- `orchestration/tools/inject_vault.py`
- `/opt/fpai/env/magnet.env`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 4: Run `python orchestration/tools/inject_vault.py --...
**Goal:** Run `python orchestration/tools/inject_vault.py --target magnet` to populate `/opt/fpai/env/magnet.env`.

**Files involved:**
- `droplets/hteam/droplet-3/`
- `infra/secrets.vault.example.json`
- `orchestration/tools/inject_vault.py`
- `/opt/fpai/env/magnet.env`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 5: Signal ops to move Magnet to staging once env file...
**Goal:** Signal ops to move Magnet to staging once env file is populated.

**Files involved:**
- `droplets/hteam/droplet-3/`
- `infra/secrets.vault.example.json`
- `orchestration/tools/inject_vault.py`
- `/opt/fpai/env/magnet.env`

**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]

### Step 6: Testing & Verification
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

### Step 7: Submission
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
- [ ] Copy `infra/secrets.vault.example.json` to `infra/secrets.vault.json` locally.
- [ ] Insert Binance testnet API key/secret plus Redis URL.
- [ ] Run `python orchestration/tools/inject_vault.py --target magnet` to populate `/opt/fpai/env/magnet.env`.
- [ ] Signal ops to move Magnet to staging once env file is populated.
- [ ] Code pushed to GitHub
- [ ] Submitted via Harvester
- [ ] Score 80+ on automated review

## Resources
**Related Files:**
- `droplets/hteam/droplet-3/`
- `infra/secrets.vault.example.json`
- `orchestration/tools/inject_vault.py`
- `/opt/fpai/env/magnet.env`

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
- ⚠️ Do **not** commit `secrets.vault.json`.
- ⚠️ Confirm `/opt/fpai/env/magnet.env` permission stays `600`.
- ⚠️ Contact ops if registry JWT rotates; both registry + orchestrator must share the new value.

---
*Generated: 2025-11-26 20:48*
*Spec Status: DRAFT - Requires human review before publishing*
*Mission ID: M001*
