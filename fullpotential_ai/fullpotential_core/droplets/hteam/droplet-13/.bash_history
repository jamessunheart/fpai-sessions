apt install python3-pip -y
pip install fastapi uvicorn requests
pip install fastapi uvicorn requests --break-system-packages
python3 -m fastapi version
python3
apt install python3-venv -y
python3 -m venv nexusenv
source nexusenv/bin/activate
pip install fastapi uvicorn requests
python -c "import fastapi; print(fastapi.__version__)"
nano nexus.py
uvicorn nexus:app --host 0.0.0.0 --port 80
nano /etc/systemd/system/nexus.service
systemctl daemon-reload
systemctl enable nexus
systemctl start nexus
systemctl status nexus
@app.get("/health")
def health():
nano /root/nexus.py
systemctl status nexus
curl http://64.227.107.127
curl http://64.227.107.127/health
nano /root/nexus.py
systemctl restart nexus
curl http://64.227.107.127/health
journalctl -u nexus -n 20 --no-pager
systemctl status nexus
curl http://64.227.107.127
curl http://64.227.107.127/health
curl -X POST http://64.227.107.127/event/ingest   -H "Content-Type: application/json"   -d '{"source":"test","payload":{"hello":"world"}}'
source /root/nexusenv/bin/activate
systemctl status nexus
rm /root/nexus.py
nano /root/nexus.py
systemctl restart nexus
systemctl status nexus
curl http://64.227.107.127/health
journalctl -u nexus -n 20 --no-pager
rm /root/nexus.py
nano /root/nexus.py
systemctl restart nexus
journalctl -fu nexus
curl -X POST http://drop1.fullpotential.ai/registry/register -H "Content-Type: application/json" -d '{"name":"drop13"}'
curl -v -X POST https://drop1.fullpotential.ai/registry/register   -H "Content-Type: application/json"   -d '{"name":"drop13","fqdn":"drop13.fullpotential.ai","ip":"64.227.107.127","role":"nexus","env":"prod","version":"2025.11.7"}'
systemctl status nexus
curl http://64.227.107.127/health
curl -v -X POST https://drop1.fullpotential.ai/registry/register   -H "Content-Type: application/json"   -d '{"name":"drop13","fqdn":"drop13.fullpotential.ai","ip":"64.227.107.127","role":"nexus","env":"prod","version":"2025.11.7"}'
ufw status
docker ps
ps -aux
exit
source /root/nexusenv/bin/activate
systemctl status nexus
curl http://64.227.107.127/health
curl -X POST https://drop1.fullpotential.ai/registry/register   -H "Content-Type: application/json"   -d '{"name":"drop13","fqdn":"drop13.fullpotential.ai","ip":"64.227.107.127","role":"nexus","env":"prod","version":"2025.11.7"}'
journalctl -u nexus -n 20 --no-pager
curl -X POST https://drop1.fullpotential.ai/registry/heartbeat  -H "Content-Type: application/json"  -d '{
   "trace_id":"test-uuid",
   "source":"drop13.fullpotential.ai",
   "target":"drop1.fullpotential.ai",
   "message_type":"status",
   "payload":{
     "id":"drop13.fullpotential.ai",
     "status":"healthy",
     "cpu":12.4,
     "mem":47.1,
     "disk":65.3,
     "last_seen":1731081600
   },
   "timestamp":"2025-11-07T14:45:00Z"
 }'
sudo systemctl list-units --type=service --state=running | grep nexus
sudo systemctl list-units --type=service --state=running | grep registry
# Show where the Nexus files live
sudo systemctl status nexus | grep "WorkingDirectory"
sudo systemctl status nexus | head -n 10
head -n 50 /root/nexus.py
cat > /root/nexus.py <<'EOF'
from fastapi import FastAPI, Request
import requests, threading, time, psutil, json
from datetime import datetime, timezone

app = FastAPI(title="Droplet 13 – Nexus 🕸️")

CORE = "https://drop1.fullpotential.ai"
DROPLET_ID = "drop13.fullpotential.ai"
REGISTRY_KEY = ""  # optional API key if enabled

HEADERS = {
    "Content-Type": "application/json",
    "X-Registry-Key": REGISTRY_KEY
}

# ----------------------------------------------------
# Registration payload (static, runs once on startup)
# ----------------------------------------------------
REGISTER_PAYLOAD = {
    "name": "drop13",
    "fqdn": DROPLET_ID,
    "ip": "64.227.107.127",
    "role": "integration_hub",
    "env": "prod",
    "version": "2025.11.7",
    "cost_hour": 0.02
}

# ----------------------------------------------------
# Build dynamic heartbeat payload
# ----------------------------------------------------
def build_heartbeat():
    """Collect system metrics and format as heartbeat payload."""
    return {
        "id": DROPLET_ID,
        "status": "healthy",
        "cpu": round(psutil.cpu_percent(), 2),
        "mem": round(psutil.virtual_memory().percent, 2),
        "disk": round(psutil.disk_usage('/').percent, 2),
        "last_seen": int(time.time()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ----------------------------------------------------
# Register Nexus with Registry (Drop 1)
# ----------------------------------------------------
def register():
    try:
        print("🚀 Registering with Core Droplet 1…")
        r = requests.post(f"{CORE}/registry/register", json=REGISTER_PAYLOAD, headers=HEADERS, timeout=10)
        print(f"✅ Registry Response [{r.status_code}]: {r.text}")
    except Exception as e:
        print(f"❌ Registration failed: {e}")

# ----------------------------------------------------
# Send heartbeat loop
# ----------------------------------------------------
def heartbeat():
    """Continuously send heartbeat data to Registry."""
    while True:
        try:
            payload = build_heartbeat()
            r = requests.post(f"{CORE}/registry/heartbeat", json=payload, headers=HEADERS, timeout=10)

            if r.status_code == 200:
                print(f"💓 Heartbeat OK [{r.status_code}] → {r.text}")
            else:
                print(f"⚠️ Heartbeat failed [{r.status_code}] → {r.text}")

        except Exception as e:
            print(f"⚠️ Heartbeat error: {e}")

        time.sleep(60)

# ----------------------------------------------------
# FastAPI startup hook
# ----------------------------------------------------
@app.on_event("startup")
def startup_event():
    register()
    threading.Thread(target=heartbeat, daemon=True).start()
    print("🔄 Nexus heartbeat thread started.")

# ----------------------------------------------------
# Routes
# ----------------------------------------------------
@app.get("/")
def root():
    return {"status": "✅ Nexus running", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
def health():
    return {"ok": True, "uptime": time.time(), "droplet": DROPLET_ID}
EOF

sudo systemctl restart nexus
journalctl -u nexus -n 30 --no-pager
source /root/nexusenv/bin/activate
pip install psutil
sudo systemctl restart nexus
journalctl -u nexus -n 30 --no-pager
curl http://64.227.107.127/health
journalctl -u nexus -n 20 --no-pager | grep Heartbeat
cp /root/registry.py /root/registry_backup_$(date +%F_%T).py
cat > /root/registry.py <<'EOF'
from fastapi import FastAPI, Request
from datetime import datetime, timezone
import json

app = FastAPI(title="Droplet 1 – Registry (Core)")

REGISTRY_DB = "/app/data/registry.db"  # placeholder – optional persistence

@app.post("/registry/register")
async def register(request: Request):
    """Register new droplet."""
    data = await request.json()
    droplet_id = data.get("fqdn") or data.get("id")
    print(f"🆕 Register request → {droplet_id}")
    return {"id": droplet_id, "registered": True, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/registry/heartbeat")
async def heartbeat(request: Request):
    """Handle heartbeat from any droplet."""
    data = await request.json()
    # unwrap UDC payloads if present
    if "payload" in data and isinstance(data["payload"], dict):
        payload = data["payload"]
    else:
        payload = data

    droplet_id = payload.get("id")
    status = payload.get("status", "unknown")
    cpu = payload.get("cpu")
    mem = payload.get("mem")
    disk = payload.get("disk")

    # basic validation
    if not droplet_id:
        return {"error": "id required"}

    print(f"💓 Heartbeat → {droplet_id} | CPU {cpu}% | MEM {mem}% | DISK {disk}% | Status {status}")
    return {"status": "ok", "id": droplet_id, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/health")
def health():
    return {"ok": True, "service": "registry", "timestamp": datetime.now(timezone.utc).isoformat()}
EOF

echo "🕸️ Nexus Status:" && curl -s http://64.227.107.127/health && echo "\n📡 Heartbeats:" && journalctl -u nexus -n 2 --no-pager | grep Heartbeat
curl -I https://drop13.fullpotential.ai
curl https://drop13.fullpotential.ai/health
curl -X POST https://drop1.fullpotential.ai/registry/register   -H "Content-Type: application/json"   -d '{"name":"drop13","fqdn":"drop13.fullpotential.ai","ip":"64.227.107.127","role":"nexus","env":"prod","version":"2025.11.7"}'
curl -X POST https://drop1.fullpotential.ai/registry/heartbeat   -H "Content-Type: application/json"   -d '{
        "id":"drop13.fullpotential.ai",
        "status":"healthy",
        "cpu":12.3,
        "mem":47.8,
        "disk":61.5,
        "last_seen":1731025200
      }'
hostname -f && whoami
cat /etc/os-release | head -3
ls /opt
systemctl status nexus --no-pager
hostname
ubuntu-s-1vcpu-512mb-droplet-13
curl -s http://127.0.0.1:8001/getAll | jq
apt install jq -y
curl -s http://127.0.0.1:8001/getAll | jq
cat >/usr/local/bin/verify-network.sh <<'EOF'
#!/bin/bash
REGISTRY_IP="24.199.107.120"
REGISTRY_PORT="8001"
REGISTRY_KEY="regkey_f3e19b7b8d17493fa8c01c3eab2e9b71"

echo "🔍 Checking Registry (drop18) health..."
curl -s http://$REGISTRY_IP:$REGISTRY_PORT/health | jq . || curl -s http://$REGISTRY_IP:$REGISTRY_PORT/health

echo
echo "💓 Sending heartbeat for this droplet..."
DROPLET_ID=$(hostname -f 2>/dev/null || hostname)
curl -s -X POST http://$REGISTRY_IP:$REGISTRY_PORT/registry/heartbeat \
  -H "Content-Type: application/json" \
  -H "X-Registry-Key: $REGISTRY_KEY" \
  -d "{\"id\":\"$DROPLET_ID\"}" | jq . || echo "Heartbeat failed"

echo
echo "📦 Fetching full registry manifest..."
curl -s http://$REGISTRY_IP:$REGISTRY_PORT/getAll | jq . || curl -s http://$REGISTRY_IP:$REGISTRY_PORT/getAll

echo
echo "✅ Test complete for: $DROPLET_ID"
EOF

chmod +x /usr/local/bin/verify-network.sh
verify-network.sh --repair
curl -X POST http://24.199.107.120:8001/registry/heartbeat   -H "Content-Type: application/json"   -H "X-Registry-Key: regkey_f3e19b7b8d17493fa8c01c3eab2e9b71"   -d '{"id": "james-test-node.fullpotential.ai"}'
curl -X POST http://24.199.107.120:8001/registry/register   -H "Content-Type: application/json"   -H "X-Registry-Key: regkey_f3e19b7b8d17493fa8c01c3eab2e9b71"   -d '{"id":"james-test-node.fullpotential.ai","name":"observer","role":"external_tester","env":"prod","version":"2.0"}'
# Basic reachability (from inside drop13)
hostname -f
ip a | sed -n '1,120p'
ss -ltnp | sed -n '1,200p'              # show listeners (expect :80 and :443; plus app port if any)
ufw status || true                      # firewall state
systemctl is-active nginx && nginx -v   # nginx running?
systemctl status nginx --no-pager
# External checks (from drop13 itself)
curl -I -k https://drop13.fullpotential.ai/           # expect 200/301
curl -s -k https://drop13.fullpotential.ai/health || true
curl -s -k https://drop13.fullpotential.ai/getAll || true
LISTEN 0 2048 0.0.0.0:80 users:(("uvicorn",pid=6906,fd=7))
ps aux | grep uvicorn
# 1. View its systemd service definition (if any)
systemctl list-units | grep nexus
systemctl status nexus.service --no-pager 2>/dev/null || true
# 2. See the folder structure
ls -la /root | grep nexus
ls -la /root/nexusenv
ls -la /root | grep nexus.py
# 3. Check what ports are public
ss -ltnp | grep 80
# 4. Verify the health route directly
curl -s http://127.0.0.1:80/health
ls
find / -type f -name "requirements.txt" 2>/dev/null | grep -v '/venv/'
