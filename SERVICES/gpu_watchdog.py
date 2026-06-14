#!/usr/bin/env python3
"""
⚠️ DEPRECATED - DO NOT USE ⚠️

This GPU Watchdog is DEPRECATED. It was part of a broken dual-system
that caused $57/day in runaway costs (46 GPUs running idle).

PROBLEMS WITH THIS SYSTEM:
1. Checked localhost:8400 but GPU Bridge is at 162.0.208.88:8400
2. Ran every 15 min but GPU Hunter ran every 2 min (acquired faster than released)
3. No coordination with GPU Hunter
4. Soft limits that didn't actually stop anything

USE INSTEAD: SERVICES/gpu-manager/ (v2.0 - unified, safe)

The new GPU Manager v2.0 has:
- ONE unified system (not two competing)
- Correct endpoint checking
- Hard circuit breakers
- Rate limiting
- Disabled by default

---

OLD DESCRIPTION (for reference):
GPU WATCHDOG - Smart scaling that keeps cheap GPUs, releases expensive idle ones.
Reads config from gpu_config.json - edit that file to change behavior.
Runs every 15 minutes via systemd timer.

SECURITY: API key loaded from environment variable VASTAI_API_KEY
"""
import os
import requests
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(message)s",
    handlers=[
        logging.FileHandler("/var/log/gpu_watchdog.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# SECURITY FIX: Load API key from environment, not hardcoded
VASTAI_API_KEY = os.environ.get("VASTAI_API_KEY", "")
CONFIG_FILE = Path("/opt/fpai/ai-brain/v2/gpu_config.json")
STATE_FILE = Path("/var/log/gpu_watchdog_state.json")
ALERTS_FILE = Path("/var/log/gpu_alerts.json")

def load_config():
    """Load config from JSON file."""
    try:
        return json.loads(CONFIG_FILE.read_text())
    except:
        logger.warning("Config file not found, using defaults")
        return {
            "cost_thresholds": {"cheap_gpu_max": 0.06, "expensive_gpu_min": 0.15},
            "scaling_limits": {"min_gpus": 3, "soft_max_gpus": 10, "hard_max_gpus": 20, "soft_daily_cost": 15.0, "hard_daily_cost": 30.0},
            "utilization": {"idle_threshold": 5, "min_requests_per_gpu_hour": 10},
            "behavior": {"keep_cheap_gpus": True, "auto_release_expensive_when_idle": True, "alert_on_soft_limits": True}
        }

def get_instances():
    """Get all Vast.ai instances."""
    try:
        r = requests.get(
            f"https://console.vast.ai/api/v0/instances/?api_key={VASTAI_API_KEY}",
            timeout=15
        )
        return r.json().get("instances", [])
    except Exception as e:
        logger.error(f"Failed to get instances: {e}")
        return []

def get_gpu_bridge_stats():
    """Get utilization stats from GPU Bridge."""
    try:
        r = requests.get("http://localhost:8400/stats", timeout=5)
        data = r.json()
        return {
            "total_requests": data.get("total_requests", 0),
            "uptime_hours": data.get("uptime_hours", 1),
        }
    except Exception as e:
        logger.warning(f"Could not get GPU Bridge stats: {e}")
        return None

def calculate_utilization(stats, gpu_count):
    """Calculate requests per GPU per hour."""
    if not stats or gpu_count == 0:
        return 0, 0
    
    total_reqs = stats.get("total_requests", 0)
    uptime = stats.get("uptime_hours", 1)
    
    requests_per_hour = total_reqs / uptime if uptime > 0 else 0
    requests_per_gpu_hour = requests_per_hour / gpu_count if gpu_count > 0 else 0
    
    return requests_per_hour, requests_per_gpu_hour

def stop_instance(inst_id):
    """Stop a single instance."""
    try:
        r = requests.delete(
            f"https://console.vast.ai/api/v0/instances/{inst_id}/?api_key={VASTAI_API_KEY}",
            timeout=10
        )
        return r.status_code in [200, 204]
    except:
        return False

def categorize_gpus(instances, config):
    """Categorize GPUs into cheap, medium, and expensive based on config."""
    running = [i for i in instances if i.get("actual_status") == "running"]
    
    cheap_max = config["cost_thresholds"]["cheap_gpu_max"]
    expensive_min = config["cost_thresholds"]["expensive_gpu_min"]
    
    cheap = [i for i in running if i.get("dph_total", 0) < cheap_max]
    expensive = [i for i in running if i.get("dph_total", 0) >= expensive_min]
    medium = [i for i in running if cheap_max <= i.get("dph_total", 0) < expensive_min]
    
    return {
        "cheap": sorted(cheap, key=lambda x: x.get("dph_total", 0)),
        "medium": sorted(medium, key=lambda x: x.get("dph_total", 0)),
        "expensive": sorted(expensive, key=lambda x: x.get("dph_total", 0), reverse=True),
        "all": running
    }

def create_alert(alert_type, title, message, data=None, requires_action=True):
    """Create an alert for human review."""
    alert = {
        "id": f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": alert_type,
        "title": title,
        "message": message,
        "data": data or {},
        "requires_action": requires_action,
        "created_at": datetime.now().isoformat(),
        "acknowledged": False
    }
    
    alerts = []
    if ALERTS_FILE.exists():
        try:
            alerts = json.loads(ALERTS_FILE.read_text()).get("alerts", [])
        except:
            pass
    
    alerts = alerts[-49:] + [alert]
    ALERTS_FILE.write_text(json.dumps({"alerts": alerts}, indent=2))
    
    logger.warning(f"ALERT: {title}")
    return alert

def smart_scale_down(instances, config, reason, target_reduction=None):
    """Smart scale-down: Release EXPENSIVE GPUs first, KEEP cheap ones."""
    cats = categorize_gpus(instances, config)
    
    stopped = 0
    stopped_details = []
    
    # First: Release expensive GPUs (most expensive first)
    for inst in cats["expensive"]:
        if target_reduction and stopped >= target_reduction:
            break
        if stop_instance(inst.get("id")):
            gpu_name = inst.get("gpu_name", "Unknown")
            cost = inst.get("dph_total", 0)
            stopped += 1
            stopped_details.append(f"{gpu_name} (${cost:.3f}/hr)")
            logger.info(f"  Released EXPENSIVE: {gpu_name} (${cost:.3f}/hr) - {reason}")
    
    # Second: If still need to reduce, release medium-cost GPUs
    if target_reduction and stopped < target_reduction:
        for inst in sorted(cats["medium"], key=lambda x: x.get("dph_total", 0), reverse=True):
            if stopped >= target_reduction:
                break
            if stop_instance(inst.get("id")):
                gpu_name = inst.get("gpu_name", "Unknown")
                cost = inst.get("dph_total", 0)
                stopped += 1
                stopped_details.append(f"{gpu_name} (${cost:.3f}/hr)")
                logger.info(f"  Released MEDIUM: {gpu_name} (${cost:.3f}/hr) - {reason}")
    
    # NEVER release cheap GPUs automatically if config says to keep them
    if config["behavior"]["keep_cheap_gpus"] and cats["cheap"]:
        logger.info(f"  Keeping {len(cats['cheap'])} cheap GPUs (config: keep_cheap_gpus=true)")
    
    return stopped, stopped_details

def save_state(state):
    """Save watchdog state for trending."""
    try:
        history = []
        if STATE_FILE.exists():
            history = json.loads(STATE_FILE.read_text()).get("history", [])[-100:]
        
        history.append({"timestamp": datetime.now().isoformat(), **state})
        STATE_FILE.write_text(json.dumps({"history": history}, indent=2))
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

def check_and_enforce():
    """Main watchdog check with smart scaling based on config."""
    config = load_config()
    limits = config["scaling_limits"]
    behavior = config["behavior"]
    
    logger.info("=" * 50)
    logger.info("GPU Watchdog check starting...")
    logger.info(f"Config: keep_cheap={behavior['keep_cheap_gpus']}, auto_release_expensive={behavior['auto_release_expensive_when_idle']}")
    
    instances = get_instances()
    cats = categorize_gpus(instances, config)
    running = cats["all"]
    
    gpu_count = len(running)
    hourly_cost = sum(i.get("dph_total", 0) for i in running)
    daily_cost = hourly_cost * 24
    
    bridge_stats = get_gpu_bridge_stats()
    req_per_hour, req_per_gpu_hour = calculate_utilization(bridge_stats, gpu_count)
    
    state = {
        "gpu_count": gpu_count,
        "cheap_gpus": len(cats["cheap"]),
        "medium_gpus": len(cats["medium"]),
        "expensive_gpus": len(cats["expensive"]),
        "hourly_cost": round(hourly_cost, 3),
        "daily_cost": round(daily_cost, 2),
        "requests_per_hour": round(req_per_hour, 1),
        "requests_per_gpu_hour": round(req_per_gpu_hour, 1),
        "action": "none"
    }
    
    logger.info(f"GPUs: {gpu_count} total ({len(cats['cheap'])} cheap, {len(cats['medium'])} medium, {len(cats['expensive'])} expensive)")
    logger.info(f"Cost: ${hourly_cost:.2f}/hr (${daily_cost:.2f}/day)")
    logger.info(f"Utilization: {req_per_hour:.1f} req/hr, {req_per_gpu_hour:.1f} req/GPU/hr")
    
    # ========== HARD LIMITS (Always enforced) ==========
    
    if gpu_count > limits["hard_max_gpus"]:
        logger.warning(f"HARD LIMIT: {gpu_count} GPUs > {limits['hard_max_gpus']}")
        stopped, details = smart_scale_down(instances, config, "hard GPU limit", gpu_count - limits["hard_max_gpus"])
        state["action"] = f"hard_limit_released_{stopped}"
        create_alert("auto_action", f"Released {stopped} GPUs (hard limit)", f"Released: {', '.join(details)}", requires_action=False)
        save_state(state)
        return
    
    if daily_cost > limits["hard_daily_cost"]:
        logger.warning(f"HARD LIMIT: ${daily_cost:.2f}/day > ${limits['hard_daily_cost']}")
        stopped, details = smart_scale_down(instances, config, "hard cost limit")
        state["action"] = f"hard_cost_released_{stopped}"
        create_alert("auto_action", f"Released {stopped} expensive GPUs (cost)", f"Released: {', '.join(details)}", requires_action=False)
        save_state(state)
        return
    
    # ========== SMART IDLE SCALING (Based on config) ==========
    
    idle_threshold = config["utilization"]["idle_threshold"]
    
    if behavior["auto_release_expensive_when_idle"] and req_per_gpu_hour < idle_threshold and cats["expensive"]:
        logger.info(f"Low utilization ({req_per_gpu_hour:.1f} req/GPU/hr) - releasing expensive GPUs")
        stopped, details = smart_scale_down(instances, config, "low utilization")
        if stopped > 0:
            state["action"] = f"idle_released_{stopped}"
            create_alert("auto_action", f"Released {stopped} expensive idle GPUs", 
                        f"Utilization: {req_per_gpu_hour:.1f} req/GPU/hr. Released: {', '.join(details)}. Kept cheap GPUs.", 
                        requires_action=False)
            save_state(state)
            return
    
    # ========== SOFT LIMITS (Alerts if enabled) ==========
    
    if behavior["alert_on_soft_limits"]:
        if gpu_count > limits["soft_max_gpus"]:
            create_alert("info", f"GPU count: {gpu_count} (soft limit: {limits['soft_max_gpus']})",
                        "Within bounds. Expensive GPUs will auto-release when idle.")
        
        if daily_cost > limits["soft_daily_cost"]:
            create_alert("info", f"Daily cost: ${daily_cost:.2f} (soft limit: ${limits['soft_daily_cost']})",
                        "Within bounds. Expensive GPUs will auto-release when idle.")
    
    logger.info(f"All OK - keeping {len(cats['cheap'])} cheap GPUs")
    save_state(state)

def show_status():
    """Show current status and config."""
    config = load_config()
    instances = get_instances()
    cats = categorize_gpus(instances, config)
    
    total_cost = sum(i.get("dph_total", 0) for i in cats["all"])
    
    print("\n" + "=" * 60)
    print("GPU WATCHDOG STATUS")
    print("=" * 60)
    print(f"\nConfig file: {CONFIG_FILE}")
    print(f"Cheap threshold: < ${config['cost_thresholds']['cheap_gpu_max']}/hr")
    print(f"Expensive threshold: > ${config['cost_thresholds']['expensive_gpu_min']}/hr")
    print(f"\nBehavior:")
    print(f"  Keep cheap GPUs: {config['behavior']['keep_cheap_gpus']}")
    print(f"  Auto-release expensive when idle: {config['behavior']['auto_release_expensive_when_idle']}")
    
    print(f"\nCurrent Fleet: {len(cats['all'])} GPUs | ${total_cost:.2f}/hr | ${total_cost*24:.2f}/day")
    
    if cats["cheap"]:
        print(f"\n💎 CHEAP ({len(cats['cheap'])}) - KEEPING:")
        for g in cats["cheap"]:
            print(f"   {g.get('gpu_name'):20} ${g.get('dph_total', 0):.3f}/hr")
    
    if cats["medium"]:
        print(f"\n📊 MEDIUM ({len(cats['medium'])}):")
        for g in cats["medium"]:
            print(f"   {g.get('gpu_name'):20} ${g.get('dph_total', 0):.3f}/hr")
    
    if cats["expensive"]:
        print(f"\n💸 EXPENSIVE ({len(cats['expensive'])}) - WILL RELEASE WHEN IDLE:")
        for g in cats["expensive"]:
            print(f"   {g.get('gpu_name'):20} ${g.get('dph_total', 0):.3f}/hr")
    
    print("\n" + "=" * 60)
    print("To change behavior, edit: /opt/fpai/ai-brain/v2/gpu_config.json")
    print("=" * 60)

if __name__ == "__main__":
    import sys
    
    # SECURITY FIX: Verify API key is set
    if not VASTAI_API_KEY:
        logger.error("VASTAI_API_KEY environment variable not set!")
        logger.error("Set it with: export VASTAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_status()
    else:
        check_and_enforce()
        show_status()
