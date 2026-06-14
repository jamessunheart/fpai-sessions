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
