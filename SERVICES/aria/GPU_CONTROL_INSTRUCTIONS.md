# GPU Control Instructions for Aria

## Overview

You have access to GPU fleet management via the GPU Manager API.

**Endpoint:** `http://162.0.208.88:8450`

## Available Commands

### 1. Check Status
```
GET http://162.0.208.88:8450/status
```
Returns: running GPUs, daily cost, budget remaining, mode

**When to use:** When user asks about GPU costs, status, or resources

### 2. Release Idle GPUs (Safe)
```
POST http://162.0.208.88:8450/release-idle
```
Returns: number of GPUs released

**When to use:** 
- User asks to save money
- User asks to reduce GPU usage
- Costs seem high for no reason

### 3. Emergency Stop (Destroy All)
```
POST http://162.0.208.88:8450/emergency-stop
```
Returns: number destroyed

**When to use:**
- User says "stop all GPUs" or "emergency"
- Costs are out of control
- User is panicking about spending

### 4. Change Mode
```
POST http://162.0.208.88:8450/set-mode/{mode}
```
Modes:
- `monitor_only` - Just watch, no actions
- `scale_down_only` - Release idle GPUs only (CURRENT, SAFE)
- `full_auto` - Full automation

**When to use:**
- User wants to enable/disable auto-scaling
- User wants more control

### 5. View Cost History
```
GET http://162.0.208.88:8450/cost
```
Returns: hourly and daily cost breakdown

## Example Responses

### User: "What's the GPU status?"
```
Checking GPU fleet status...

Currently running: 3 GPUs
Daily cost: $5.50
Budget: $14.50 remaining of $20/day
Mode: scale_down_only (auto-releases idle GPUs)

All GPUs:
- GTX 1080 @ $0.055/hr (idle)
- RTX 2070 @ $0.08/hr (active)
- Tesla T4 @ $0.15/hr (idle)
```

### User: "Release the idle GPUs"
```
Releasing idle GPUs...

Released 2 GPUs:
- GTX 1080 (was $0.055/hr)
- Tesla T4 (was $0.15/hr)

1 GPU remaining (RTX 2070 - active)
New daily cost: $1.92
```

### User: "Stop all GPU spending NOW"
```
⚠️ EMERGENCY STOP activated.

Destroyed all 3 GPUs.
Daily cost now: $0.00

The GPU Manager will prevent new GPUs from being created 
(mode: scale_down_only).
```

## Safety Notes

1. **scale_down_only mode** (current) is safe - it won't create new GPUs
2. **Budget limit is $20/day** - hard enforced
3. **Emergency stop at $25/day** - automatic circuit breaker
4. **Max 10 GPUs** allowed

## Python Integration

If you need to call these programmatically:

```python
from app.gpu_control import GPUControl, gpu_status

gpu = GPUControl()
status = await gpu.get_status()
print(status.summary())

# Or quick functions:
print(await gpu_status())  # Human-readable status
```

