#!/bin/bash
# Automated SSOT refresh - keeps Single Source of Truth accurate
# Can be run manually or via cron

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSOT_FILE="$SCRIPT_DIR/../SSOT.json"
DISCOVERY_FILE="/tmp/service_discovery_map.json"

# Run service discovery
python3 << 'EOFPYTHON'
import subprocess
import json
from datetime import datetime

# Service discovery
ports = {
    8000: "Registry",
    8001: "Orchestrator",
    8002: "Unknown",
    8003: "I PROACTIVE",
    8004: "FPAI Analytics",
    8009: "Unknown",
    8010: "FPAI Hub",
    8025: "Credentials Manager",
    8030: "Simple Dashboard",
    8031: "Visual Dashboard",
    8040: "FPAI Hub (alternate)",
    8401: "I MATCH",
    8700: "AI Automation"
}

service_map = {}

for port, suspected_name in sorted(ports.items()):
    try:
        health_result = subprocess.run(
            ["curl", "-s", "--max-time", "2", f"http://localhost:{port}/health"],
            capture_output=True,
            timeout=3
        )
        
        if health_result.returncode == 0 and health_result.stdout:
            try:
                health_data = json.loads(health_result.stdout)
                service_map[str(port)] = {
                    "name": health_data.get("service", suspected_name),
                    "version": health_data.get("version", "unknown"),
                    "status": "online",
                    "health_status": health_data.get("status", "unknown")
                }
                continue
            except:
                pass
    except:
        pass
    
    service_map[str(port)] = {
        "name": suspected_name,
        "status": "offline"
    }

# Save discovery results
with open("/tmp/service_discovery_map.json", "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat() + "Z",
        "services": service_map
    }, f, indent=2)

print(f"Discovery complete: {len([s for s in service_map.values() if s['status'] == 'online'])} online, {len([s for s in service_map.values() if s['status'] == 'offline'])} offline")
EOFPYTHON

# Update SSOT with discovery results
python3 << 'EOFPYTHON2'
import json
from datetime import datetime
from pathlib import Path

# Load discovery results
with open("/tmp/service_discovery_map.json") as f:
    discovery = json.load(f)

# Load current SSOT
ssot_path = Path("/Users/jamessunheart/Development/docs/coordination/SSOT.json")
with open(ssot_path) as f:
    ssot = json.load(f)

# Update server_status
ssot["server_status"] = {}
for port, data in discovery["services"].items():
    ssot["server_status"][port] = data["status"]

# Update timestamp
ssot["last_update"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

# Update metadata
if "metadata" not in ssot:
    ssot["metadata"] = {}
ssot["metadata"]["last_verified"] = discovery["timestamp"]
ssot["metadata"]["verification_method"] = "automated_health_checks"
ssot["metadata"]["auto_refresh"] = True

# Write back
with open(ssot_path, "w") as f:
    json.dump(ssot, f, indent=2)

online_count = len([s for s in ssot["server_status"].values() if s == "online"])
offline_count = len([s for s in ssot["server_status"].values() if s == "offline"])

print(f"✅ SSOT updated: {online_count} online, {offline_count} offline")
print(f"   Timestamp: {ssot['last_update']}")
EOFPYTHON2

echo ""
echo "✅ Auto-refresh complete!"
