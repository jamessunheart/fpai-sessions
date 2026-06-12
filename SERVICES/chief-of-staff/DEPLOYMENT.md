# Chief of Staff Service - Deployment Guide

## 🎯 Purpose
Executive intelligence layer that filters noise and shows what matters.
Applies 30-day decision filter and routes signals by urgency.

## 📍 Server Location
**Primary Server:** 198.54.123.234
**Port:** 8107
**Service Name:** fpai-chief-of-staff

## ⚠️ Prerequisites
**MUST deploy alerts service first!**
Chief of Staff depends on fpai-alerts running on port 8766.

## 🚀 Deployment Steps

### 1. Ensure Alerts Service is Running
```bash
ssh root@198.54.123.234
systemctl status fpai-alerts
curl http://localhost:8766/health
```

### 2. Deploy to Production
```bash
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/chief-of-staff/deploy
./deploy.sh production
```

### 3. Verify Health
```bash
ssh root@198.54.123.234
curl http://localhost:8107/health
```

## 📊 Service Endpoints

- **Health:** http://198.54.123.234:8107/health
- **Dashboard:** http://198.54.123.234:8107/dashboard
- **Docs:** http://198.54.123.234:8107/docs
- **Process Signal:** POST http://198.54.123.234:8107/signal
- **Urgent Items:** http://198.54.123.234:8107/urgent
- **Status:** http://198.54.123.234:8107/status

## 🔧 Maintenance

### View Logs
```bash
journalctl -u fpai-chief-of-staff -f
```

### Restart
```bash
systemctl restart fpai-chief-of-staff
```

### Stop
```bash
systemctl stop fpai-chief-of-staff
```

## 🔗 Integration

Other services should send signals to:
```bash
POST http://localhost:8107/signal
{
  "source": "service-name",
  "type": "error" | "metric" | "event",
  "title": "Signal title",
  "description": "Signal description",
  "data": { ... },
  "urgency_hint": "urgent" | "important" (optional)
}
```

## 📈 Signal Categories

The service categorizes signals using the 30-day decision filter:

- 🔴 **URGENT** - Telegram alert NOW (revenue blockers, critical errors)
- 🟡 **IMPORTANT** - Daily digest (non-critical issues)
- 🟢 **AUTO** - Logged only (already handled)
- 📊 **CONTEXT** - Logged only (doesn't serve 30-day goals)

## 🎯 Decision Filter

**Core Question:** "Does this serve proof / revenue / clarity / ease for core offer in 30 days?"

**Keywords:**
- revenue, booking, conversion, user, payment
- zen village, retreat
- proof, clarity
- error, critical, down

**Urgency Thresholds:**
- Revenue drop > 20%
- Error rate > 5%
- Uptime < 95%

## 📝 Notes

- Connects to Alerts Service (port 8766) for notification delivery
- Sends to @sunheartbrain_bot (Telegram with Brain context)
- Dashboard auto-refreshes every 30 seconds
- Stores last 10,000 signals in memory
- 90-day retention period
