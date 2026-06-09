# Alerts Service - Deployment Guide

## 🎯 Purpose
Centralized notification service for all FPAI services.
Handles Telegram, SMS delivery with rate limiting and queuing.

## 📍 Server Location
**Primary Server:** 198.54.123.234
**Port:** 8766
**Service Name:** fpai-alerts

## 🚀 Deployment Steps

### 1. Deploy to Production
```bash
cd /Users/jamessunheart/FPAI_Cockpit/SERVICES/alerts/deploy
./deploy.sh production
```

### 2. Update Credentials on Server
SSH to server and update the .env file:
```bash
ssh root@198.54.123.234
cd /opt/fpai/services/alerts
nano .env
```

Update these values:
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
- `TELEGRAM_STEWARD_CHAT_ID` - Your Telegram chat ID
- `TWILIO_ACCOUNT_SID` - (Optional) Twilio SID for SMS
- `TWILIO_AUTH_TOKEN` - (Optional) Twilio token for SMS
- `TWILIO_PHONE_NUMBER` - (Optional) Twilio phone number

### 3. Restart Service
```bash
systemctl restart fpai-alerts
systemctl status fpai-alerts
```

### 4. Verify Health
```bash
curl http://localhost:8766/health
```

## 📊 Service Endpoints

- **Health:** http://198.54.123.234:8766/health
- **Docs:** http://198.54.123.234:8766/docs
- **Send Notification:** POST http://198.54.123.234:8766/send
- **Queue Status:** http://198.54.123.234:8766/queue

## 🔧 Maintenance

### View Logs
```bash
journalctl -u fpai-alerts -f
```

### Restart
```bash
systemctl restart fpai-alerts
```

### Stop
```bash
systemctl stop fpai-alerts
```

## 🔗 Integration

Other services should send notifications to:
```bash
POST http://localhost:8766/send
{
  "channel": "telegram",
  "recipient": "default",
  "message": "Your message here",
  "priority": "normal"
}
```

## 📝 Notes

- This service should be deployed BEFORE chief-of-staff
- Port 8766 chosen to avoid conflict with credits-gateway (8765)
- Connected to @sunheartbrain_bot for context-aware notifications
