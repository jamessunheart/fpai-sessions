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
