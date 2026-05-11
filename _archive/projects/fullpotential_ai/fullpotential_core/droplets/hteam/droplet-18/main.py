from fastapi import FastAPI, Request
from datetime import datetime, timezone
import json, os

app = FastAPI(title="Full Potential Registry v2.0")

@app.get("/health")
def health():
    return {"ok": True, "service": "registry-2.0", "timestamp": datetime.now(timezone.utc).isoformat(), "brain":{"status":"active"}}

@app.post("/registry/register")
async def register(request: Request):
    data = await request.json()
    droplet_id = data.get("id","unknown")
    print(f"🆕 Register → {droplet_id}")
    os.makedirs("/brain", exist_ok=True)
    reg_path = "/brain/registry.json"
    registry = []
    if os.path.exists(reg_path):
        registry = json.load(open(reg_path))
    registry.append(data)
    json.dump(registry, open(reg_path,"w"), indent=2)
    return {"id": droplet_id, "status":"registered", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/registry/heartbeat")
async def heartbeat(request: Request):
    data = await request.json()
    droplet_id = data.get("id","unknown")
    print(f"💓 Heartbeat → {droplet_id}")
    return {"status":"ok","id":droplet_id,"timestamp":datetime.now(timezone.utc).isoformat()}

@app.get("/getAll")
def get_all():
    path = "/brain/registry.json"
    if os.path.exists(path):
        return json.load(open(path))
    return {"ok": False, "error": "No registry data yet"}
