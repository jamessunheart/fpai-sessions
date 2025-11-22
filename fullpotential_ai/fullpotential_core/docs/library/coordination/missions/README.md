# 🎯 Marketing Missions System

**Purpose:** Coordinate marketing/posting tasks across Claude Code sessions

**Location:** `/Users/jamessunheart/Development/docs/coordination/missions/`

---

## Mission Structure

Each mission is a JSON file with:
- **mission_id**: Unique identifier
- **title**: Short description
- **priority**: high/medium/low
- **status**: available/claimed/completed/failed
- **created_at**: ISO timestamp
- **claimed_by**: Session ID (when claimed)
- **claimed_at**: ISO timestamp (when claimed)
- **completed_at**: ISO timestamp (when completed)
- **instructions**: Detailed task description
- **success_criteria**: How to verify completion
- **resources**: Files/URLs needed

---

## Mission Lifecycle

1. **Created** - Mission file created with status "available"
2. **Claimed** - Session updates status to "claimed" and adds claimed_by
3. **In Progress** - Session works on mission
4. **Completed** - Session updates status to "completed" and adds completed_at
5. **Failed** - If mission fails, update status to "failed" with reason

---

## How to Use

### Claim a Mission
```bash
# List available missions
ls -la missions/ | grep available

# Read mission details
cat missions/mission-001-twitter-launch.json

# Claim it (update the file)
# Change status to "claimed"
# Add your session ID to claimed_by
# Add current timestamp to claimed_at
```

### Complete a Mission
```bash
# Update mission file
# Change status to "completed"
# Add current timestamp to completed_at
# Add results/metrics if applicable
```

### Report Mission Results
```bash
# Use session-send-message.sh to broadcast results
bash scripts/session-send-message.sh "broadcast" "MISSION COMPLETED" "..."
```

---

## Current Missions

See individual mission files in this directory.

All missions support the I MATCH soft launch:
**URL:** https://fullpotential.com/get-matched
**Product:** AI-powered service provider matching
**Services:** Executive Coaching | Church Formation | AI Development

---

## Mission Priority Guide

**High Priority (Do First):**
- Initial social media posts
- Reddit value commenting
- Warm network outreach

**Medium Priority (This Week):**
- Product Hunt launch
- Content creation
- Community engagement

**Low Priority (Nice to Have):**
- Advanced tactics
- Long-form content
- Partnership outreach

---

**Created:** 2025-11-15
**For:** I MATCH Soft Launch Campaign
