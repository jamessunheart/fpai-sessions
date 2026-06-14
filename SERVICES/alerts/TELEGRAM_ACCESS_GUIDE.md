# 📱 Telegram Access Guide

## How to Access Your Proactive Monitoring System

### 🤖 Your Bot: @sunheartbrain_bot

**Telegram Setup:**
- Bot Username: `@sunheartbrain_bot`
- Your Chat ID: `8514069423`
- Bot Connection: Integrated with Sunheart Brain (all your memories and conversations)

### 📬 What You'll Receive

#### 1. Immediate Urgent Alerts (🔴)

When critical issues are detected that match your 30-day decision filter:

```
🔴 URGENT - fp-index service is down

Service not responding - this is a critical service

Impact: Revenue tracking and core functionality offline
Action needed: Check service immediately

Source: proactive-monitor
Time: 2026-04-30 19:15:00 UTC
```

**Triggers for Urgent Alerts:**
- Service down with "critical" priority
- Keywords detected: revenue, booking, payment, zen village, critical, down, error
- Revenue drop > 20%
- Error rate > 5%
- Uptime < 95%

#### 2. Daily Digest (9am) (🟡)

Important but non-urgent items aggregated once per day:

```
🟡 Daily Summary - 5 Important Items

1. credits-gateway slow response (3.2s avg)
2. whaletrack-magnet 3 timeouts yesterday
3. System load at 75% (approaching threshold)
...
```

#### 3. Auto-Handled Events (🟢)

Items that were automatically handled (for your awareness):

```
🟢 Auto-Handled - Database backup completed
Automated backup successful - no action needed
```

### 🔔 Check Your Telegram Now

Open Telegram and search for `@sunheartbrain_bot`. You should see:

1. **Earlier alert** from 19:15 UTC today (system deployment)
2. **Verification message** just sent (system status check)

### 📊 System Status

**Services Running on Production (198.54.123.234):**

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| Alerts | 8766 | ✅ Running | Delivers notifications to Telegram/SMS |
| Chief of Staff | 8107 | ✅ Running | Filters signals with 30-day decision criteria |
| Proactive Monitor | 8108 | ✅ Running | Checks services every 5 minutes |

**Monitored Services:**
- fp-index (8550) - Critical
- alerts (8766) - Critical
- chief-of-staff (8107) - Critical
- credits-gateway (8765) - High priority
- whaletrack-magnet (8600) - High priority

### 🔄 How It Works

```
Every 5 minutes:
  Proactive Monitor checks all services
    ↓
  Detects: fp-index response time > 5s (very slow)
    ↓
  Sends signal to Chief of Staff
    ↓
  Chief applies 30-day filter:
    "Does this impact proof/revenue/clarity/ease for core offer?"
    ↓
    Contains keyword "critical"? → YES
    ↓
  Chief categorizes as: 🔴 URGENT
    ↓
  Sends to Alerts Service
    ↓
  Alerts delivers to Telegram
    ↓
  You get notification on @sunheartbrain_bot
    ↓
  You take action or delegate
```

### 🎯 Decision Filter Keywords

Your Chief of Staff watches for these keywords:

**Business Impact:**
- revenue
- booking
- conversion
- payment
- user

**Zen Village Retreat:**
- zen village
- retreat

**Quality Signals:**
- proof
- clarity

**Critical Issues:**
- error
- critical
- down

### 📱 Current Access Methods

**1. Passive Notifications (Active Now)**
- You receive alerts automatically in @sunheartbrain_bot
- No commands needed - just wait for alerts

**2. Interactive Commands (Not Yet Implemented)**

Potential future commands you could use:
- `/status` - See current system status
- `/urgent` - List all urgent items now
- `/health` - Check all services health
- `/digest` - Get current day's digest
- `/configure` - Adjust alert preferences

**Would you like interactive commands added?** Let me know.

### 🧪 Test the System

**Option 1: Trigger a Real Alert**

Stop a critical service and watch the alert come through:

```bash
ssh root@198.54.123.234 "systemctl stop fpai-alerts"
# Wait ~1 minute (next monitoring cycle)
# Check your Telegram - you should get urgent alert
# Restart: ssh root@198.54.123.234 "systemctl start fpai-alerts"
```

**Option 2: Send a Test Signal**

```bash
curl -X POST http://198.54.123.234:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "type": "test",
    "title": "Test Urgent Alert",
    "description": "This is a test of the urgent alert system with revenue keyword",
    "urgency_hint": "urgent"
  }'
```

### 📍 Service URLs

**Public Endpoints:**
- Alerts Health: http://198.54.123.234:8766/health
- Alerts Docs: http://198.54.123.234:8766/docs
- Chief of Staff Health: http://198.54.123.234:8107/health
- Chief of Staff Docs: http://198.54.123.234:8107/docs
- Proactive Monitor Health: http://198.54.123.234:8108/health
- Proactive Monitor Status: http://198.54.123.234:8108/status
- Proactive Monitor Docs: http://198.54.123.234:8108/docs

### 🔐 Credentials (Server Location)

All credentials are stored on the production server:

```bash
# View Telegram credentials
ssh root@198.54.123.234 "cat /opt/fpai/services/alerts/.env | grep TELEGRAM"
```

**Current Configuration:**
- TELEGRAM_BOT_TOKEN: 8667866626:AAERNEXSZAT5d9wI-baaLn0RdpJCTdrPTLs
- TELEGRAM_STEWARD_CHAT_ID: 8514069423

### 💡 Tips

1. **Check History:** Scroll up in @sunheartbrain_bot to see all past alerts
2. **Mute Non-Urgent:** You can mute the bot and only check daily digest manually
3. **Context Aware:** Since bot is connected to Sunheart Brain, it has context of your past conversations
4. **Filter Tuning:** Edit `/opt/fpai/services/chief-of-staff/.env` on server to adjust keywords

### 🚨 Troubleshooting

**Not Receiving Alerts?**

1. Check bot is working:
```bash
curl https://api.telegram.org/bot8667866626:AAERNEXSZAT5d9wI-baaLn0RdpJCTdrPTLs/getMe
```

2. Check services are running:
```bash
ssh root@198.54.123.234 "systemctl status fpai-alerts fpai-chief-of-staff fpai-proactive-monitor"
```

3. Check recent alerts were sent:
```bash
ssh root@198.54.123.234 "journalctl -u fpai-alerts -n 20"
```

4. Send test message:
```bash
python3 /tmp/send_telegram_test.py
```

**Services Down?**

```bash
# Check status
ssh root@198.54.123.234 "systemctl status fpai-proactive-monitor"

# View logs
ssh root@198.54.123.234 "journalctl -u fpai-proactive-monitor -n 50"

# Restart
ssh root@198.54.123.234 "systemctl restart fpai-proactive-monitor"
```

### 📞 Manual Alert

Want to send yourself a manual alert?

```bash
curl -X POST http://198.54.123.234:8766/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "recipient": "default",
    "message": "This is a manual test alert",
    "priority": "normal"
  }'
```

---

## ✅ Quick Verification Checklist

- [ ] Open Telegram
- [ ] Search for `@sunheartbrain_bot`
- [ ] See verification message just sent
- [ ] See earlier alerts from today
- [ ] Bot is working ✅

## 🎯 Summary

**You now have:**
- ✅ Automated service monitoring every 5 minutes
- ✅ Intelligent filtering (30-day decision criteria)
- ✅ Telegram alerts to @sunheartbrain_bot
- ✅ Three services running 24/7 on production
- ✅ Context-aware bot connected to Sunheart Brain

**What happens next:**
- System monitors continuously
- You get alerted only for important issues
- Chief of Staff filters the noise
- You stay on top of what matters for Zen Village retreat and revenue
