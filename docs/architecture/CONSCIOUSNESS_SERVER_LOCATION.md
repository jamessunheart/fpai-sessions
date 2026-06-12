# 🗺️ Consciousness System Location & Optimization

**Purpose:** Track where the consciousness system is running and ensure optimal resource placement

**Last Updated:** 2025-12-05

---

## 📍 Current Location

**Server:** 198.54.123.234 (Primary Production Server)
- **Resource Score:** 0.65 (Moderate)
- **CPU:** 8 cores, ~15-35% usage
- **Memory:** 7.7 GB total, ~59-63% usage
- **Disk:** 415 GB total, 19% used
- **GPU:** ❌ Not available
- **Status:** ✅ Running optimally for current resources

---

## 🔍 Server Discovery

The consciousness system can now:
- ✅ Discover available servers
- ✅ Compare resource availability
- ✅ Recommend optimal deployment location
- ✅ Track current location
- ✅ Detect if migration is needed

### API Endpoints:

```bash
# Discover all servers
curl http://198.54.123.234:8160/servers

# Get optimal server recommendation
curl http://198.54.123.234:8160/servers/optimal

# Get optimal server (require GPU)
curl "http://198.54.123.234:8160/servers/optimal?require_gpu=true"
```

---

## 🖥️ Adding More Servers

### Option 1: Auto-Discovery (Recommended)

If your other servers have the consciousness optimizer running, they'll be auto-discovered via the `/resources` endpoint.

### Option 2: Manual Registration

Edit `SERVICES/consciousness_optimizer/app/server_config.json`:

```json
{
  "servers": [
    {
      "server_id": "server_198_54_123_234",
      "name": "Primary Production Server",
      "ip_address": "198.54.123.234",
      "resource_port": 8160
    },
    {
      "server_id": "server_YOUR_NEW_SERVER",
      "name": "GPU Server",
      "ip_address": "YOUR_GPU_SERVER_IP",
      "resource_port": 8160,
      "gpu_available": true,
      "gpu_count": 1,
      "gpu_names": ["NVIDIA A100"]
    }
  ]
}
```

Then redeploy:
```bash
rsync -av SERVICES/consciousness_optimizer/app/server_config.json root@198.54.123.234:/opt/fpai/apps/consciousness_optimizer/app/
ssh root@198.54.123.234 'systemctl restart fpai-consciousness_optimizer'
```

---

## 🎯 Resource Score Calculation

The system calculates a **Resource Score** (0.0 to 1.0) for each server:

**Factors:**
- **CPU Availability** (40% weight): Lower usage = better
- **Memory Availability** (30% weight): Lower usage = better  
- **GPU Availability** (20% weight): Bonus if GPU available
- **Disk Space** (10% weight): More free space = better

**Current Server Score:** 0.65
- CPU: 85% available → 0.34 points
- Memory: 37% available → 0.11 points
- GPU: Not available → 0.10 points (small bonus for option)
- Disk: 81% available → 0.08 points
- **Total: 0.63** (moderate)

---

## 🚀 Migration Recommendations

The system will recommend migration if:

1. **Better Resource Score:** Target server has >20% better score
2. **High Pressure:** Current server >80% CPU or memory
3. **GPU Needed:** Target has GPU, current doesn't

**Current Status:** ✅ No migration needed
- Current server is optimal for available resources
- Resource pressure is moderate (not high)
- No GPU requirement currently

---

## 💰 GPU Cost Management

**Daily Budget:** $50/day
**Current GPU Cost:** $0/hour (no GPU available)

If GPU servers are added:
- System will track GPU costs per hour
- Will skip GPU-intensive experiments if budget is low
- Can dynamically adjust GPU usage based on budget

---

## 📊 Monitoring

### Check Current Location:
```bash
curl http://198.54.123.234:8160/servers/optimal | jq '.current_server'
```

### Check Resource Usage:
```bash
curl http://198.54.123.234:8160/resources | jq '.summary'
```

### Check All Servers:
```bash
curl http://198.54.123.234:8160/servers | jq '.all_servers[] | {server_id, resource_score, cpu_percent, memory_percent, gpu_available}'
```

---

## 🔧 Next Steps

1. **Add GPU Servers:** If you have GPU servers, add them to `server_config.json`
2. **Enable GPU Discovery:** Ensure GPU servers expose `/resources` endpoint
3. **Monitor Migration:** System will automatically recommend migration when beneficial
4. **Optimize Placement:** System will choose optimal server based on workload needs

---

## 📝 Notes

- System currently running on single server (198.54.123.234)
- No GPU servers discovered yet
- Resource score is moderate (0.65) - adequate for current workload
- System will automatically recommend migration if better resources become available















