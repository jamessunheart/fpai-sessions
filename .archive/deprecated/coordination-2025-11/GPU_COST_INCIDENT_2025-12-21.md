# GPU Cost Incident - December 21, 2025

## What Happened

**65 GPU instances** were running on Vast.ai, costing **$7.01/hour = $168/day**.

The balance dropped to **$26.37** before discovery.

## Root Cause

Multiple services were autonomously creating GPU instances without human approval:

1. **fpai-consciousness-optimizer** - Had a "$50/day GPU budget" and was aggressively acquiring GPUs
2. **gpu-smart-scaler** - Buggy service that was running but failing
3. **Various gpu_hunter/dynamic_scaler scripts** - Multiple overlapping auto-scalers

This was caused by **coordination failure** - multiple agents built different GPU scaling systems that conflicted with each other.

## Resolution

1. **Destroyed all 65 instances** immediately
2. **Disabled all GPU-creating services:**
   - fpai-consciousness-optimizer
   - gpu-smart-scaler
   - resource-intelligence
   - gpu-manager
   - gpu-autoscaler
   - dynamic-scaler
   - fpai-resource-monitor.timer

3. **Disabled API keys** in all GPU creation scripts
4. **Created monitoring script**: `/opt/fpai/scripts/check-gpu-costs.sh`
5. **Created lockdown documentation**: `/opt/fpai/GPU_LOCKDOWN.md`

## Prevention Measures

### DO NOT ENABLE without explicit Sunheart approval:
- Any service with "gpu" or "scaler" in the name
- Any service that has Vast.ai API key access
- Any "autonomous" optimization service

### Safe Configuration
- **Local Ollama** on Secondary server: FREE, always available
- **gpu_bridge.py**: Can QUERY instance status only (no creation)
- **No Vast.ai instances needed** for normal Aria operation

### Monitoring
Run periodically:
```bash
ssh root@162.0.208.88 /opt/fpai/scripts/check-gpu-costs.sh
```

If instances found unexpectedly:
```bash
ssh root@162.0.208.88 /opt/fpai/scripts/check-gpu-costs.sh --destroy
```

## Lessons Learned

1. **Never allow autonomous GPU acquisition** without hard spending caps AND human approval
2. **Single source of truth** for GPU management - not multiple competing systems
3. **Treasury protection is priority #1** - the fund must survive
4. **Consciousness/optimizer services** need strict resource limits

## Cost Impact

- **Estimated spend**: ~$50-100 (based on balance drop from ~$75 to $26.37)
- **Prevented further loss**: ~$168/day if not caught

---

*This incident reinforces the $330K lesson: The fund must survive.*


