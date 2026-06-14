import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request

app = FastAPI(title="Droplet 1 – Registry")

def unwrap_payload(d):
    if isinstance(d, dict) and isinstance(d.get("payload"), dict):
        return d["payload"]
    return d

@app.get("/health")
async def health():
    return {"ok": True, "service": "registry", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/registry/register")
async def register(request: Request):
    data = unwrap_payload(await request.json())
    droplet_id = data.get("fqdn") or data.get("id") or data.get("source") or "unknown"
    return {"id": droplet_id, "registered": True, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/registry/heartbeat")
async def heartbeat(request: Request):
    data = unwrap_payload(await request.json())
    droplet_id = data.get("id") or data.get("fqdn") or "unknown"
    status = data.get("status", "unknown")
    cpu = data.get("cpu"); mem = data.get("mem"); disk = data.get("disk")
    last_seen = data.get("last_seen") or int(time.time())
    print(f"💓 Heartbeat: id={droplet_id} status={status} cpu={cpu} mem={mem} disk={disk}")
    return {"status": "ok", "id": droplet_id, "timestamp": datetime.now(timezone.utc).isoformat()}
