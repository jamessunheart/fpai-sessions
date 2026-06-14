# 🚨 Quick Reference: Alerts System

**Status:** ✅ LIVE on Production (198.54.123.234)
**Date:** 2026-04-30

---

## 🎯 Three New Services

| Service | Port | Purpose | URL |
|---------|------|---------|-----|
| **Alerts** | 8766 | Multi-channel delivery | http://198.54.123.234:8766 |
| **Chief of Staff** | 8107 | Intelligent filtering | http://198.54.123.234:8107 |
| **Proactive Monitor** | 8108 | Service health checks | http://198.54.123.234:8108 |

---

## 🔌 Integration APIs

### Send a Notification
```bash
curl -X POST http://198.54.123.234:8766/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "recipient": "default",
    "message": "Your alert message",
    "priority": "normal"
  }'
```

### Send an Intelligent Signal
```bash
curl -X POST http://198.54.123.234:8107/signal \
  -H "Content-Type: application/json" \
  -d '{
    "source": "your-service",
    "type": "alert",
    "title": "Revenue drop detected",
    "description": "Details here",
    "urgency_hint": "urgent"
  }'
```

### Check System Status
```bash
curl http://198.54.123.234:8108/status  # See all monitored services
curl http://198.54.123.234:8107/urgent  # See urgent signals
```

---

## ⚙️ Configuration

### Decision Filter Keywords
Edit on server: `/opt/fpai/services/chief-of-staff/.env`
```
DECISION_FILTER_KEYWORDS=revenue,booking,conversion,user,payment,zen village,retreat,proof,clarity,error,critical,down
```

### Add Service to Monitoring
Edit on server: `/opt/fpai/services/proactive-monitor/.env`
```
MONITORED_SERVICES="""
your-service:8XXX:critical
"""
```

### Telegram Bot
- Bot: @sunheartbrain_bot
- Connected to: Sunheart Brain
- Credentials: `/opt/fpai/services/alerts/.env`

---

## 🚫 DO NOT

1. ❌ Create duplicate notification systems - use alerts (8766)
2. ❌ Modify ports without coordination
3. ❌ Change Telegram credentials - connected to Sunheart Brain
4. ❌ Stop these services without announcement

---

## ✅ DO

1. ✅ Integrate your service with proactive-monitor
2. ✅ Send signals through Chief of Staff for filtering
3. ✅ Use decision filter keywords for your alerts
4. ✅ Read `ALERTS_SYSTEM_HANDOFF.md` for full details

---

## 📚 Full Documentation

**Handoff:** `docs/coordination/ALERTS_SYSTEM_HANDOFF.md`
**Service READMEs:**
- `SERVICES/alerts/README.md`
- `SERVICES/chief-of-staff/README.md`
- `SERVICES/proactive-monitor/README.md`
**User Guide:** `SERVICES/alerts/TELEGRAM_ACCESS_GUIDE.md`
**Registry:** `docs/coordination/SERVICE_REGISTRY.md` (updated)

---

**Questions?** Check the handoff doc first, then coordinate via session messages.
