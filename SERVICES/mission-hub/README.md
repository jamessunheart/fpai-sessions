# Mission Hub

**The Bridge Between AI Vision and Human Action**

Mission Hub is the central coordination system for Full Potential AI's regenerative missions. It connects missions that need to be completed with humans (and AI agents) ready to contribute.

## Features

- **Mission Board** — Browse all active missions with live status
- **Mission Claiming** — Claim missions to work on
- **Contributor Profiles** — Track your contributions and impact
- **Leaderboard** — See top contributors
- **Harvester Integration** — Automatic scoring when code is submitted

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MISSION HUB                            │
├─────────────────────────────────────────────────────────────┤
│  UI Routes:                                                 │
│    /              → Mission Board                           │
│    /mission/{id}  → Mission Detail + Claim                  │
│    /contribute    → Contributor Landing Page                │
│    /leaderboard   → Top Contributors                        │
├─────────────────────────────────────────────────────────────┤
│  API Routes:                                                │
│    POST /api/claim    → Claim a mission                     │
│    POST /api/submit   → Submit work (triggers harvester)    │
│    POST /api/status   → Update mission status               │
│    GET  /api/missions → List all missions with status       │
│    GET  /api/stats    → System-wide statistics              │
├─────────────────────────────────────────────────────────────┤
│  Data Storage:                                              │
│    data/mission-hub/claims/       → Mission claims          │
│    data/mission-hub/status/       → Mission status history  │
│    data/mission-hub/contributors/ → Contributor profiles    │
└─────────────────────────────────────────────────────────────┘
```

## Integration Points

### Harvester (Port 8055)
When an apprentice submits code through the Harvester, it calls:
```
POST /api/status
{
  "mission_id": "M001",
  "status": "completed",
  "updated_by": "Alex",
  "score": 85
}
```

### Landing Page
Missions are sourced from:
```
SERVICES/landing-page/app/static/missions.json
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the service
./start.sh

# Or run directly
python3 app.py
```

## Mission Types

| Type | Label | Description |
|------|-------|-------------|
| `ai_only` | 🤖 AI-Only | Can be completed entirely by AI agents |
| `hybrid` | 🤝 Hybrid | AI drafts, human refines |
| `human_required` | 👤 Human Required | Needs human creativity or judgment |

## Status Flow

```
open → claimed → in_progress → submitted → reviewing → completed
                      ↓
                   blocked
```

## Constitution Alignment

Every mission should trace back to the Full Potential Constitution:

1. **Optimization over Extraction** — Create net-new value
2. **Autonomy over Dependency** — Liberate human operators
3. **Consciousness over Computation** — Expand awareness

---

*Building Heaven on Earth, One Mission at a Time*


