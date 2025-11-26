# 🎯 Mission Control v2.0

**Central mission management system with real-time tracking, claim management, and harvester integration.**

## Overview

Mission Control is the operational hub for the Full Potential AI system. It provides:

1. **Live Mission Board** - Visual grid showing all missions with real-time status
2. **Mission Details** - Full specs, claim buttons, starter kits
3. **Claim Tracking** - Who's working on what, when
4. **Status Management** - Track progress from open → claimed → submitted → completed
5. **Harvester Integration** - Automatic status updates when code is submitted

## Architecture

```
┌─────────────────┐
│  Mission Board  │ ← Users browse available missions
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Mission Detail  │ ← Full specs + CLAIM button
└────────┬────────┘
         │
         ↓ (claim)
┌─────────────────┐
│  Claims API     │ ← Tracks who claimed what
└────────┬────────┘
         │
         ↓ (work on code)
┌─────────────────┐
│   Harvester     │ ← Submit repo for review
└────────┬────────┘
         │
         ↓ (harvest complete)
┌─────────────────┐
│  Status API     │ ← Updates mission status
└────────┬────────┘
         │
         ↓ (refresh)
┌─────────────────┐
│  Mission Board  │ ← Shows "COMPLETED" ✅
└─────────────────┘
```

## Mission Lifecycle

1. **OPEN** - Mission created and visible on board
2. **CLAIMED** - User clicked "CLAIM & START MISSION"
3. **IN_PROGRESS** - User is actively working (manual update via API)
4. **SUBMITTED** - Code submitted to Harvester
5. **COMPLETED** - Harvest passed with score ≥ 60%
6. **BLOCKED** - Harvest failed or user reported blocker

## API Endpoints

### Mission Data

```bash
# Get all missions with live status
GET /api/missions

# Get single mission details
GET /api/mission/{mission_id}
```

### Claim Management

```bash
# Claim a mission
POST /api/claim
{
  "mission_id": "M001",
  "claimer_name": "Alex Chen",
  "claimer_email": "alex@example.com",  # optional
  "notes": "Starting work this week"     # optional
}
```

### Status Updates

```bash
# Update mission status
POST /api/status
{
  "mission_id": "M001",
  "status": "in_progress",  # open, claimed, in_progress, submitted, completed, blocked
  "updated_by": "Alex Chen",
  "notes": "Working on tests",
  "repo_url": "https://github.com/user/repo",  # optional
  "harvest_score": 85  # optional, set by Harvester
}
```

## Data Storage

All state is stored as JSON files (no database required):

```
data/
├── claims/
│   ├── M001.json
│   ├── M002.json
│   └── ...
└── status/
    ├── M001.json
    ├── M002.json
    └── ...
```

### Claim File Structure
```json
{
  "mission_id": "M001",
  "claimer_name": "Alex Chen",
  "claimer_email": "alex@example.com",
  "claimed_at": "2025-11-26T10:30:00",
  "notes": "Starting work this week"
}
```

### Status File Structure
```json
{
  "mission_id": "M001",
  "status": "submitted",
  "last_updated": "2025-11-26T15:45:00",
  "last_updated_by": "Alex Chen",
  "history": [
    {
      "status": "claimed",
      "timestamp": "2025-11-26T10:30:00",
      "updated_by": "Alex Chen",
      "notes": "Mission claimed"
    },
    {
      "status": "in_progress",
      "timestamp": "2025-11-26T12:00:00",
      "updated_by": "Alex Chen",
      "notes": "Working on tests"
    },
    {
      "status": "submitted",
      "timestamp": "2025-11-26T15:45:00",
      "updated_by": "Alex Chen",
      "notes": "Code submission via Harvester",
      "repo_url": "https://github.com/user/repo",
      "harvest_score": 85
    }
  ]
}
```

## Integration with Harvester

When a user submits code via the Harvester:

1. User fills out submission form with mission ID
2. Harvester runs quality checks (tests, security scan, etc.)
3. Harvester calls Mission Control: `POST /api/status`
4. Mission status updates to `submitted` → `completed` (or `blocked` if failed)
5. Status appears on Mission Board in real-time

## Deployment

### Local Development
```bash
cd SERVICES/mission-control
pip install -r requirements.txt
python3 app.py
# Visit http://localhost:8700
```

### Production Server
```bash
# On server
cd /root/FPAI_Cockpit
git pull origin main
bash DEPLOY_MISSION_CONTROL.sh
```

## URLs

- **Mission Board:** `https://fullpotential.ai/missions`
- **Mission Detail:** `https://fullpotential.ai/missions/mission/M001`
- **API Docs:** `https://fullpotential.ai/missions/docs`
- **Health Check:** `https://fullpotential.ai/missions/health`

## Configuration

### Environment Variables
```bash
# Optional: Override mission data paths
export MISSIONS_JSON="/path/to/missions.json"
export MISSIONS_MD_ROOT="/path/to/missions/markdown"
```

### Port Configuration
Default port: `8700`

To change, edit `app.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=YOUR_PORT)
```

## Monitoring

```bash
# Check service status
curl http://127.0.0.1:8700/health

# View logs
tail -f mission-control.log

# Check current claims
ls -la data/claims/

# Check mission statuses
ls -la data/status/
```

## Troubleshooting

### "Mission not found" error
- Ensure `missions.json` exists at the configured path
- Run mission feed generator: `python3 orchestration/tools/generate_mission_feed.py`

### Claims not saving
- Check write permissions on `data/claims/` directory
- Verify JSON payload format matches API spec

### Harvester not updating status
- Ensure Mission Control is running on port 8700
- Check Harvester logs for connection errors
- Verify mission ID matches exactly (case-sensitive)

## Future Enhancements

- [ ] Slack/Discord notifications on status changes
- [ ] Mission assignment suggestions based on skills
- [ ] Leaderboard showing completed missions per user
- [ ] Time tracking and velocity metrics
- [ ] Mission templates and bulk creation
- [ ] Integration with GitHub Issues

## Support

- **Issues:** Submit via Harvester feedback form
- **Docs:** `@SERVICES/mission-control/README.md`
- **API:** Visit `/docs` for interactive API documentation

