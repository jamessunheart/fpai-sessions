# GPU Manager v2.0 - Actually Smart This Time

## What This Is

A **UNIFIED** GPU management system that replaces the broken dual-system (GPU Hunter + GPU Watchdog) that caused $57/day in runaway costs.

## Key Differences from Old System

| Old System | New System |
|------------|------------|
| Two competing systems (Hunter + Watchdog) | ONE unified manager |
| Hunter: $100/day budget, Watchdog: $30/day | ONE budget: $20/day |
| Watchdog checked wrong endpoint | Checks CORRECT endpoints |
| Scale up every 2 min, scale down every 15 min | Balanced intervals |
| No rate limiting | Max 3 GPUs/hour |
| Soft limits only | HARD circuit breakers |
| Always enabled | Disabled by default - must explicitly enable |

## Safety Features

### Circuit Breakers (HARD STOPS)
- **Emergency cost stop**: If daily cost > $25, DESTROY ALL
- **Emergency count stop**: If GPU count > 15, DESTROY EXCESS
- **Rate limit**: Max 3 new GPUs per hour
- **Lock file**: Prevents multiple instances

### Scaling Logic
```
IF daily_cost > emergency_limit:
    → EMERGENCY SHUTDOWN (destroy all)

ELIF utilization < 20%:
    → Scale DOWN (release most expensive idle GPU)

ELIF utilization > 70% AND under_budget AND under_max_gpus:
    → Scale UP (rent cheapest available)

ELSE:
    → Do nothing (system balanced)
```

## Operating Modes

| Mode | Behavior |
|------|----------|
| `monitor_only` | Just watch and log - NO scaling actions |
| `scale_down_only` | Only release GPUs - NEVER acquire new ones |
| `full_auto` | Full automatic scaling (up and down) |

**Default: `monitor_only`** - You must explicitly enable more aggressive modes.

## Configuration

### Environment Variables
```bash
# Required
export VASTAI_API_KEY="your-api-key"

# Optional overrides
export GPU_MANAGER_ENABLED=true
export GPU_MANAGER_MODE=scale_down_only
export GPU_DAILY_BUDGET=20
export GPU_MAX_COUNT=10
```

### Config File (`config.py`)
All settings are in ONE file with sensible defaults:
- Budget: $20/day hard limit
- Max GPUs: 10
- Scale down at < 20% utilization
- Scale up at > 70% utilization
- Check interval: 60 seconds

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Full status including all GPUs |
| `/cost` | GET | Detailed cost breakdown |
| `/history` | GET | Action history |
| `/config` | GET | Current configuration |
| `/emergency-stop` | POST | DESTROY ALL GPUs immediately |
| `/release-idle` | POST | Release idle GPUs |
| `/set-mode/{mode}` | POST | Change operating mode |

## Usage

### 1. Start in Monitor-Only Mode (Safe)
```bash
export VASTAI_API_KEY="your-key"
export GPU_MANAGER_ENABLED=true
export GPU_MANAGER_MODE=monitor_only

python main.py
```

### 2. Check Status
```bash
curl http://localhost:8450/status
```

### 3. If Everything Looks Good, Enable Scale-Down
```bash
curl -X POST http://localhost:8450/set-mode/scale_down_only
```

### 4. Emergency Stop
```bash
curl -X POST http://localhost:8450/emergency-stop
```

## File Structure

```
gpu-manager/
├── config.py       # ALL configuration in one place
├── manager.py      # Core management logic
├── main.py         # FastAPI service
├── requirements.txt
└── README.md
```

## Deployment

### On Secondary Server (162.0.208.88)
```bash
cd /opt/fpai/services/gpu-manager
pip install -r requirements.txt

# Start in safe mode first
GPU_MANAGER_ENABLED=true \
GPU_MANAGER_MODE=monitor_only \
VASTAI_API_KEY="your-key" \
python main.py
```

### Systemd Service
```ini
[Unit]
Description=GPU Manager v2
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/fpai/services/gpu-manager
Environment=VASTAI_API_KEY=your-key
Environment=GPU_MANAGER_ENABLED=true
Environment=GPU_MANAGER_MODE=scale_down_only
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## IMPORTANT: Disable Old Systems First!

Before deploying this, make sure to disable the old broken systems:

```bash
# On secondary server
pkill -f gpu_hunter
pkill -f gpu_watchdog
mv /opt/fpai/ai-brain/v2/gpu_hunter_daemon.py /opt/fpai/ai-brain/v2/gpu_hunter_daemon.py.DISABLED
```

## Monitoring Endpoints

The manager checks these endpoints for REAL utilization:
- `http://162.0.208.88:8400/stats` - GPU Bridge
- `http://162.0.208.88:8101/stats` - AI Brain

If these endpoints don't respond, the manager assumes **IDLE** and scales down (safe default).

## History

This system was created after the old dual-system caused:
- 46 GPUs to accumulate
- $57/day in costs ($1,711/month)
- $25+ charges multiple times per day

The root causes were:
1. GPU Hunter acquiring GPUs every 2 minutes
2. GPU Watchdog checking the wrong endpoint
3. No coordination between systems
4. Soft limits that didn't actually limit anything

This new system fixes all of those issues.
