from fastapi import FastAPI, Request
from datetime import datetime
import hashlib, requests

app = FastAPI(title="Droplet 18 - Registry v2")

REGISTRY_STORE = {"registry": {}, "heartbeats": {}}

@app.get("/")
def root():
    return {"ok": True, "service": "Registry v2", "ts": datetime.utcnow().isoformat() + "Z"}

@app.get("/health")
def health():
    proof = hashlib.sha256(f"drop18_{datetime.utcnow()}".encode()).hexdigest()
    # best-effort callback; never crash health
    try:
        requests.post("http://24.199.107.120:8001/registry/heartbeat",
                      json={"id":"drop18.fullpotential.ai","status":"healthy","version":"2025.11.12","schema_version":"udc-1.0"},
                      timeout=1.5)
    except Exception as e:
        print("[WARN] registry callback:", e)
    return {
        "id": 18,
        "name": "Registry v2",
        "steward": "Suresh",
        "status": "active",
        "proof": proof,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# ---- Registry endpoints (v2 minimal) ----
@app.post("/registry/register")
async def registry_register(req: Request):
    data = await req.json()
    fqdn = data.get("fqdn") or data.get("name") or f"node-{len(REGISTRY_STORE[registry])+1}"
    REGISTRY_STORE["registry"][fqdn] = data | {"registered_at": datetime.utcnow().isoformat()+"Z"}
    return {"ok": True, "id": fqdn}

@app.post("/registry/heartbeat")
async def registry_heartbeat(req: Request):
    data = await req.json()
    nid = data.get("id") or data.get("fqdn") or "unknown"
    REGISTRY_STORE["heartbeats"][nid] = data | {"seen_at": datetime.utcnow().isoformat()+"Z"}
    return {"ok": True}

@app.get("/registry/list")
def registry_list():
    return REGISTRY_STORE

