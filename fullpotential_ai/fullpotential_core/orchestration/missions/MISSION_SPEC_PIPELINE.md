# Mission Spec Pipeline

## Overview

Every mission must go through the **Spec Pipeline** before being published to the Mission Hub. This ensures contributors have clear, actionable instructions to succeed.

## Two Entry Points

### 🤖 AI-Generated Missions
AI identifies needs from codebase analysis, user feedback, or system monitoring:
```
AI detects need → Creates brief → Auto-generates spec → Human reviews → Publish
```

### 👤 Human-Submitted Missions  
Humans submit ideas through Mission Hub or directly:
```
Human submits idea → AI generates spec → Human reviews → Publish
```

**Both paths converge at spec generation** - every mission gets a complete, actionable spec.

## Pipeline Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   BRIEF     │ -> │  SPEC GEN   │ -> │   REVIEW    │ -> │  PUBLISH    │ -> │   LIVE      │
│             │    │             │    │             │    │             │    │             │
│ AI or Human │    │ AI expands  │    │ Human       │    │ Move to     │    │ Visible on  │
│ idea        │    │ into full   │    │ validates   │    │ open/       │    │ Mission Hub │
│             │    │ spec        │    │ & refines   │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     drafts/           specs/            specs/             open/           Mission Hub
```

## ⏱️ Time Constraint

**Missions must be completable in 1-4 hours.** This ensures:
- Contributors can finish in a single work session
- Progress is visible and frequent
- Large tasks get broken into manageable pieces

| Time Estimate | Guideline |
|---------------|-----------|
| ~30 min | Simple fix, config change |
| 1 hour | Small feature, bug fix |
| 1.5-2 hours | Standard mission |
| 2-3 hours | Complex feature |
| 3-4 hours | Maximum single mission |
| 4+ hours | **Split into multiple missions** |

## Stage 1: BRIEF (drafts/)

**Who:** Anyone (AI or human)
**Location:** `orchestration/missions/drafts/`

A brief is a quick capture of a mission need. Minimum requirements:
- Title
- One-line objective
- Why it matters (regenerative impact)

**Example Brief:**
```markdown
# Mission: Fix Login Bug

**Objective:** Users can't log in on mobile Safari
**Impact:** Blocking 30% of potential users
**Priority:** P0
```

## Stage 2: SPEC GENERATION (specs/)

**Who:** AI (with human oversight)
**Location:** `orchestration/missions/specs/`
**Tool:** `orchestration/tools/generate_mission_spec.py`

The spec generator expands briefs into complete specs:

```bash
# Generate spec from brief
python orchestration/tools/generate_mission_spec.py M007

# Output: orchestration/missions/specs/M007_SPEC.md
```

Generated specs include:
- ✅ Step-by-step instructions
- ✅ Prerequisites checklist
- ✅ Success criteria
- ✅ Estimated time & difficulty
- ✅ Related files/resources
- ✅ Troubleshooting tips

## Stage 3: HUMAN REVIEW (specs/)

**Who:** Mission Coordinator / Technical Lead
**Location:** `orchestration/missions/specs/`

Before publishing, a human must:

1. **Verify accuracy** - Are the steps correct?
2. **Fill gaps** - Add missing details AI couldn't infer
3. **Test feasibility** - Can someone actually complete this?
4. **Check alignment** - Does it serve the Constitution?

**Review Checklist:**
- [ ] Objective is clear and achievable
- [ ] All prerequisites are listed
- [ ] Steps are in logical order
- [ ] Commands are tested and work
- [ ] Success criteria are measurable
- [ ] Time estimate is realistic
- [ ] No sensitive info exposed

## Stage 4: PUBLISH (open/)

**Who:** Mission Coordinator
**Location:** `orchestration/missions/open/`

Once approved:

```bash
# Move spec to open/
mv specs/M007_SPEC.md open/M007_FIX_LOGIN_BUG.md

# Update missions.json (auto-generated or manual)
python orchestration/tools/sync_missions.py
```

## Stage 5: LIVE (Mission Hub)

**Who:** Contributors
**Location:** https://fullpotential.ai/missions

The mission is now visible on the Mission Hub and can be claimed by contributors.

---

## Spec Quality Standards

### Must Have
- [ ] Clear, one-sentence objective
- [ ] At least 3 step-by-step instructions
- [ ] Testable success criteria
- [ ] Estimated time
- [ ] Difficulty level
- [ ] Related files/resources

### Should Have
- [ ] Prerequisites checklist
- [ ] Troubleshooting section
- [ ] Example code/commands
- [ ] Links to documentation

### Nice to Have
- [ ] Video walkthrough
- [ ] Reference to similar completed missions
- [ ] Multiple approaches/solutions

---

## Quick Commands

```bash
# Create a new mission brief
echo "# Mission: [TITLE]

**Objective:** [What needs to be done]
**Impact:** [Why it matters]
**Priority:** P0|P1|P2|P3
" > orchestration/missions/drafts/M00X_BRIEF.md

# Generate spec from brief
python orchestration/tools/generate_mission_spec.py M00X

# Review spec
cat orchestration/missions/specs/M00X_SPEC.md

# Publish (after review)
mv orchestration/missions/specs/M00X_SPEC.md orchestration/missions/open/

# Sync to Mission Hub
python orchestration/tools/sync_missions.py
```

---

## Mission Lifecycle Summary

| Stage | Status | Location | Who |
|-------|--------|----------|-----|
| Draft | `DRAFT` | `drafts/` | Anyone |
| Spec Generated | `SPEC_REVIEW` | `specs/` | AI |
| Under Review | `SPEC_REVIEW` | `specs/` | Human |
| Published | `OPEN` | `open/` | Coordinator |
| Claimed | `CLAIMED` | Mission Hub | Contributor |
| In Progress | `IN_PROGRESS` | Mission Hub | Contributor |
| Submitted | `SUBMITTED` | Harvester | Contributor |
| Completed | `COMPLETED` | `done/` | Verified |

---

*This pipeline ensures every mission is clear, complete, and actionable before contributors see it.*

