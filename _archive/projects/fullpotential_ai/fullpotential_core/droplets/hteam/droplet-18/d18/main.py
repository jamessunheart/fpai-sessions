from fastapi import FastAPI, Request
from datetime import datetime
import hashlib

app = FastAPI(title="Registry v2")

registry = {}
heartbeats = {}

@app.get("/")
def root():
    return {"message": "Registry v2 online", "status": "ok", "registered": len(registry)}

@app.get("/health")
def health():
    proof = hashlib.sha256(f"drop18_{datetime.utcnow()}".encode()).hexdigest()
    return {
        "id": 18,
        "name": "Registry v2",
        "steward": "Suresh",
        "status": "active",
        "proof": proof,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/registry/register")
async def register(request: Request):
    data = await request.json()
    fqdn = data.get("fqdn", f"unknown-{datetime.utcnow().timestamp()}")
    registry[fqdn] = {
        **data,
        "registered_at": datetime.utcnow().isoformat() + "Z"
    }
    print(f"[REGISTER] {fqdn} registered from {data.get('ip')}")
    return {"status": "registered", "fqdn": fqdn, "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.post("/registry/heartbeat")
async def heartbeat(request: Request):
    data = await request.json()
    fqdn = data.get("fqdn", "unknown")
    heartbeats[fqdn] = {
        "last_seen": datetime.utcnow().isoformat() + "Z",
        "status": data.get("status", "unknown"),
        "payload": data
    }
    print(f"[HEARTBEAT] {fqdn} @ {heartbeats[fqdn]['last_seen']}")
    return {"status": "ok", "fqdn": fqdn, "received_at": datetime.utcnow().isoformat() + "Z"}

@app.get("/registry/list")
def list_registry():
    return {"registry": registry, "heartbeats": heartbeats}
