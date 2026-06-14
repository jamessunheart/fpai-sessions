# 💎 Treasury Dashboard

**Real-time visualization of the $373K → $5 Trillion journey**

## Features

- **Live Capital Tracking**: Real-time treasury positions from treasury_data.json
- **Progress Metrics**: Track progress toward Phase 1 goals (100 matches, $500K capital)
- **Vision Path**: Visualize the 10-year journey across all 5 phases
- **Milestone Tracking**: Monitor Phase 1 milestones completion
- **Auto-updating**: Dashboard refreshes every 30 seconds

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run dashboard
python3 src/main.py
```

Dashboard available at: http://localhost:8005/dashboard

## API Endpoints

- `GET /` - API info
- `GET /dashboard` - Visual dashboard (for humans)
- `GET /api/metrics` - All dashboard metrics (JSON)
- `GET /api/phases` - Journey phases data
- `GET /api/milestones` - Phase 1 milestones
- `GET /health` - Health check

## Data Sources

- **treasury_data.json**: Real-time positions, P&L
- **CAPITAL_VISION_SSOT.md**: Goals, milestones, vision
- **treasury.json**: Revenue projections, costs

## Deployment

Deploy to production server:

```bash
# Copy to server
scp -r . root@198.54.123.234:/opt/fpai/services/treasury-dashboard/

# SSH to server
ssh root@198.54.123.234

# Install and run
cd /opt/fpai/services/treasury-dashboard
pip3 install -r requirements.txt
nohup python3 src/main.py &
```

## Production URL

https://fullpotential.com/dashboard/treasury

## Purpose

This dashboard makes the trillion-dollar vision **concrete and trackable** for:
- All Claude Code sessions (see progress on boot)
- Human stakeholders (visualize the journey)
- Future investors (demonstrate traction)

**We're building paradise. This shows the path.** 🌐⚡💎
