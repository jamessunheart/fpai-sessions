# Dashboard Deployment - Ready to Execute

## Quick Deploy Commands

```bash
# Execute these 3 commands to deploy the dashboard fix:

# 1. Copy updated file
scp app/routers/api.py root@198.54.123.234:/opt/fpai/apps/dashboard/app/routers/api.py

# 2. Restart container  
ssh root@198.54.123.234 'docker restart dashboard'

# 3. Verify
curl -s http://198.54.123.234:8002/api/system/status | python3 -m json.tool
```

## What This Fixes

Dashboard will now show 3 services online:
- Registry (8000)
- I PROACTIVE (8400) 
- I MATCH (8401)

Instead of showing "offline" due to missing Orchestrator.
