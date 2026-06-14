# 🚀 Deploy Mission Control v2.0 Now

## Quick Start (2 Minutes)

### On Your Local Machine

```bash
# 1. Commit the changes
git add .
git commit -m "feat: Mission Control v2.0 - Complete mission tracking system with claim management and harvester integration"
git push origin main
```

### On Your Server

```bash
# 2. SSH into server
ssh root@198.54.123.234

# 3. Navigate to workspace
cd /root/FPAI_Cockpit

# 4. Pull latest code
git pull origin main

# 5. Run one-command deployment
bash DEPLOY_MISSION_CONTROL.sh
```

**That's it!** The script handles everything automatically.

---

## What the Deployment Script Does

```
📦 Installing Mission Control dependencies...
   ✓ fastapi, uvicorn, pydantic, jinja2

📁 Creating data directories...
   ✓ data/claims/
   ✓ data/status/

⏸️  Stopping old services...
   ✓ Killed mission-control (port 8700)
   ✓ Killed harvester (port 8055)

📦 Updating Harvester dependencies...
   ✓ Added requests library

🎯 Starting Mission Control (Port 8700)...
   ✓ Mission Control healthy

🚜 Starting Harvester (Port 8055)...
   ✓ Harvester healthy

🌐 Updating Nginx configuration...
   ✓ Nginx reloaded

✅ DEPLOYMENT COMPLETE!
```

---

## Verification Commands

```bash
# 1. Check services are running
curl http://127.0.0.1:8700/health
curl http://127.0.0.1:8055/health

# 2. Check public URLs
curl https://fullpotential.ai/missions
curl https://fullpotential.ai/missions/api/missions

# 3. View logs
tail -f /root/FPAI_Cockpit/SERVICES/mission-control/mission-control.log
tail -f /root/FPAI_Cockpit/SERVICES/harvester/feedback.log
```

---

## Test the Complete Flow

### Step-by-Step Test

1. **Open the Mission Board**
   ```
   Visit: https://fullpotential.ai/missions
   ```
   **Expected:** See a tactical grid of missions with status badges

2. **Click on Mission M001**
   ```
   Click any mission card
   ```
   **Expected:** Full mission spec appears with claim button

3. **Claim the Mission**
   ```
   Fill out:
   - Name: Test User
   - Email: test@example.com (optional)
   Click: "CLAIM & START MISSION"
   ```
   **Expected:** Success message → page reloads → "Claimed by Test User" appears

4. **Check API**
   ```bash
   curl https://fullpotential.ai/missions/api/mission/M001 | jq
   ```
   **Expected:** JSON shows `"status": "claimed"` and claim_info with your name

5. **Submit Code (Simulation)**
   ```
   Click: "SUBMIT CODE" button
   ```
   **Expected:** Redirects to harvester with mission M001 pre-selected

6. **Go Back to Board**
   ```
   Visit: https://fullpotential.ai/missions
   ```
   **Expected:** M001 card shows "CLAIMED" badge and your name

---

## If Something Goes Wrong

### Service Won't Start

```bash
# Check logs
tail -50 /root/FPAI_Cockpit/SERVICES/mission-control/mission-control.log

# Check port availability
fuser 8700/tcp
fuser 8055/tcp

# Manually restart
cd /root/FPAI_Cockpit/SERVICES/mission-control
pkill -f "mission-control/app.py"
python3 app.py &
```

### Can't Access from Web

```bash
# Test locally first
curl http://127.0.0.1:8700/health

# If that works, check nginx
sudo nginx -t
sudo systemctl reload nginx

# Check firewall
ufw status
```

### Missing Dependencies

```bash
cd /root/FPAI_Cockpit/SERVICES/mission-control
pip3 install -r requirements.txt

cd /root/FPAI_Cockpit/SERVICES/harvester
pip3 install -r requirements.txt
```

### JSON Files Not Saving

```bash
# Check permissions
ls -la /root/FPAI_Cockpit/SERVICES/mission-control/data/

# Create directories if missing
mkdir -p /root/FPAI_Cockpit/SERVICES/mission-control/data/claims
mkdir -p /root/FPAI_Cockpit/SERVICES/mission-control/data/status
chmod 755 -R /root/FPAI_Cockpit/SERVICES/mission-control/data/
```

---

## URLs Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Mission Board | https://fullpotential.ai/missions | Main dashboard |
| Mission Detail | https://fullpotential.ai/missions/mission/M001 | Individual mission |
| API - All Missions | https://fullpotential.ai/missions/api/missions | JSON data |
| API - Single Mission | https://fullpotential.ai/missions/api/mission/M001 | JSON details |
| Harvester | https://fullpotential.ai/services/harvester | Code submission |
| Health Check (MC) | https://fullpotential.ai/missions/health | Status check |
| Health Check (Harvester) | https://fullpotential.ai/services/harvester/health | Status check |

---

## Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| Mission Control | 8700 | Mission management & APIs |
| Harvester | 8055 | Code submission & review |
| Landing Page | 3001 | Main website |
| Master Dashboard | 3005 | Admin dashboard |
| Admin Gate | 8888 | Password setup |

---

## What You Get After Deployment

### Mission Board Features
✅ Live tactical grid showing all missions  
✅ Real-time status badges (OPEN, CLAIMED, COMPLETED)  
✅ Priority indicators (P0, P1, P2)  
✅ Shows who's working on what  
✅ Auto-refreshes every 30 seconds  

### Mission Detail Page
✅ Complete markdown spec rendering  
✅ Claim button (if not taken)  
✅ Submit code button (if claimed by you)  
✅ Status history timeline  
✅ Syntax-highlighted code blocks  

### Claim System
✅ One-click claiming  
✅ Prevents duplicate claims  
✅ Tracks claimer info  
✅ Timestamps all actions  

### Harvester Integration
✅ Auto-updates mission status on submission  
✅ Passes harvest scores back to missions  
✅ Real-time progress streaming  
✅ Complete feedback loop  

### APIs
✅ Get all missions with live status  
✅ Get individual mission details  
✅ Claim missions programmatically  
✅ Update status manually or automatically  

---

## Success Criteria

After deployment, you should be able to:

1. ✅ Visit `/missions` and see mission cards
2. ✅ Click a mission and see full specs
3. ✅ Claim a mission and see your name appear
4. ✅ See status badge change to "CLAIMED"
5. ✅ Click "SUBMIT CODE" and arrive at harvester
6. ✅ Submit a repo and watch real-time harvest
7. ✅ Return to board and see "COMPLETED" status

If all 7 work → **System is live and operational** 🎯

---

## Next Actions

After successful deployment:

1. **Test End-to-End:** Run through the complete user flow
2. **Generate Missions:** Use `generate_mission_package.py` for new missions
3. **Invite Builders:** Share `/missions` URL with apprentices
4. **Monitor Activity:** Watch the board populate with claims and completions
5. **Collect Feedback:** See what users love and what needs improvement

---

## Documentation

- **This Guide:** `DEPLOY_NOW.md`
- **User Flow:** `MISSION_CONTROL_GUIDE.md`
- **Implementation Details:** `MISSION_CONTROL_V2_SUMMARY.md`
- **Service Docs:** `SERVICES/mission-control/README.md`

---

**Ready?** Run the deploy commands above and watch Mission Control come to life! 🚀

