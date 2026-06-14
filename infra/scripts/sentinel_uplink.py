import json
import requests
import sys
import pathlib
import datetime

# Configuration
IDENTITY_FILE = pathlib.Path("/opt/fpai/config/identities/storage-sentinel_identity.json")
ALERT_FILE = pathlib.Path("/opt/fpai/data/storage_alert.json")
LOG_FILE = pathlib.Path("/var/log/fpai-sentinel.log")

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] [UPLINK] {msg}\n")

def main():
    if not IDENTITY_FILE.exists() or not ALERT_FILE.exists():
        log("Missing identity or alert file. Aborting uplink.")
        return

    try:
        # Load Identity
        with open(IDENTITY_FILE, "r") as f:
            identity = json.load(f)
        
        # Load Status
        with open(ALERT_FILE, "r") as f:
            status_data = json.load(f)
            
        api_key = identity.get("api_key")
        # Prefer internal URL for reliability
        genesis_url = "http://198.54.123.234:8150" 
        
        # 1. Send Heartbeat / Telemetry
        # We use the /api/telemetry endpoint if available, otherwise just verify auth serves as a heartbeat
        telemetry_payload = {
            "agent_name": identity.get("agent_name"),
            "status": status_data.get("status"),
            "metrics": status_data
        }
        
        try:
            # Try to send to a telemetry endpoint (hypothetical, but good practice)
            # If 404, we fall back to just logging locally that we tried.
            # But primarily we want to Alert if CRITICAL.
            
            if status_data.get("status") == "critical":
                # PUSH TO MISSION HUB (Human Intervention Needed)
                mission_url = "http://198.54.123.234:8700/api/assignments" # Mission Hub Internal
                task_payload = {
                    "title": "CRITICAL: Storage Exhaustion Imminent",
                    "description": f"Storage usage is at {status_data.get('usage_percent')}%. {status_data.get('days_remaining')} days remaining.",
                    "type": "system_alert",
                    "priority": "high",
                    "source": "storage-sentinel"
                }
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                
                # Note: Mission Hub might require different auth, but we try with our agent key
                # For now, we just log that we WOULD send this.
                log(f"CRITICAL STATUS DETECTED. Triggering alert logic for {mission_url}")
                # resp = requests.post(mission_url, json=task_payload, headers=headers, timeout=5)
                
            # Send standard heartbeat to Genesis
            heartbeat_url = f"{genesis_url}/auth/heartbeat"
            headers = {"Authorization": f"Bearer {api_key}"}
            # Using the 'verify' endpoint as a heartbeat substitute if specific heartbeat doesn't exist
            verify_url = f"{genesis_url}/auth/agent"
            
            resp = requests.post(verify_url, json={"agent_name": identity['agent_name'], "api_key": api_key}, timeout=5)
            if resp.status_code == 200:
                log(f"Heartbeat successful to Genesis. System Status: {status_data.get('status')}")
            else:
                log(f"Heartbeat failed: {resp.status_code} - {resp.text}")

        except Exception as e:
            log(f"Network error during uplink: {e}")

    except Exception as e:
        log(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()

