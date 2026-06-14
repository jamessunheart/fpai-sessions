# Proactive Monitor Service

## 🎯 Purpose

**Makes your Chief of Staff PROACTIVE instead of reactive.**

Continuously monitors critical services and automatically sends signals to Chief of Staff when issues are detected. Chief of Staff filters the signals and alerts you via Telegram only for what matters.

## 🔄 How It Works

```
Every 5 minutes:
  Proactive Monitor checks services
    ↓
  Detects: fp-index down
    ↓
  Sends signal to Chief of Staff
    ↓
  Chief of Staff: "This is critical! Alert immediately"
    ↓
  Alerts Service sends to Telegram
    ↓
  You get notification on @sunheartbrain_bot
```

## 📊 What It Monitors

### Services:
- **fp-index** (8550) - Critical
- **alerts** (8766) - Critical
- **chief-of-staff** (8107) - Critical
- **credits-gateway** (8765) - High priority
- **whaletrack-magnet** (8600) - High priority

### Detects:
- ❌ Service down (not responding)
- ⏱️ Timeouts (> 10 seconds)
- 🐌 Slow responses (> 2 seconds)
- 🐢 Very slow responses (> 5 seconds)

## 🚀 Deployment

```bash
cd deploy
./deploy.sh production
```

## 📍 Production URLs

- Health: http://198.54.123.234:8108/health
- Status: http://198.54.123.234:8108/status
- Docs: http://198.54.123.234:8108/docs

## 🛠️ Configuration

Edit `.env` to change:
- **CHECK_INTERVAL_SECONDS** - How often to check (default: 300 = 5 min)
- **MONITORED_SERVICES** - Which services to monitor
- **RESPONSE_TIME_SLOW_THRESHOLD** - When to alert for slowness

## 📝 Examples

**Check status:**
```bash
curl http://198.54.123.234:8108/status
```

**Trigger immediate check:**
```bash
curl -X POST http://198.54.123.234:8108/check/now
```

**View service history:**
```bash
curl http://198.54.123.234:8108/history/fp-index
```

## 🎯 Integration

Works seamlessly with:
- **Chief of Staff** (8107) - Sends signals here
- **Alerts Service** (8766) - Used by Chief for delivery
- **Your Telegram** (@sunheartbrain_bot) - Final destination

## ⚡ Benefits

**Before:** Reactive - you find out about problems when users complain
**After:** Proactive - you know about problems before users do

The monitor runs 24/7, checking services every 5 minutes, and only bothers you when Chief of Staff determines it's important based on your 30-day decision filter.
