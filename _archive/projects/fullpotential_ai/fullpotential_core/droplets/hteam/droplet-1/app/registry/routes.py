# app/registry/routes.py
import os, time, uuid, datetime, requests, jwt
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from .store import upsert_register, update_heartbeat, list_droplets
from . import router 


API_KEY    = os.getenv("REGISTRY_API_KEY")
DROPLETID  = os.getenv("DROPLET_ID", "droplet-1")      # this droplet (sender)
ORCH_URL   = os.getenv("DROPLET10_URL")                # e.g. https://drop10.fullpotential.ai
ORCH_KEY   = os.getenv("DROPLET10_API_KEY")            # optional header for D10
JWT_SECRET = os.getenv("REGISTRY_JWT_SECRET")          # for Authorization: Bearer <jwt>
ORCH_ID    = os.getenv("DROPLET10_ID", "droplet-10")   # target droplet id

def _auth_dependency(request: Request):
    if API_KEY and request.headers.get("X-Registry-Key") != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

def _iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _bearer() -> str | None:
    if not JWT_SECRET:
        return None
    now = int(time.time())
    return jwt.encode({"sub": DROPLETID, "iat": now, "exp": now + 600}, JWT_SECRET, algorithm="HS256")

def _udc_envelope(payload: dict) -> dict:
    return {
        "udc_version": "1.0",
        "trace_id": f"reg-{uuid.uuid4()}",
        "source": DROPLETID,          # <— this droplet (sender)
        "target": ORCH_ID,            # <— droplet-10
        "message_type": "registry",
        "timestamp": _iso_now(),
        "payload": payload,
    }

def _post_to_orchestrator_registry(envelope: dict):
    if not ORCH_URL:
        return
    url = ORCH_URL + "/registry/"
    headers = {"Content-Type": "application/json"}
    if ORCH_KEY:
        headers["X-Registry-Key"] = ORCH_KEY
    tok = _bearer()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
        headers["X-Trace-Id"] = envelope["trace_id"]
        headers["X-Source"]   = DROPLETID
    try:
        requests.post(url, json=envelope, headers=headers, timeout=8)
    except Exception:
        pass  # non-blocking mirror

@router.post("/registry/register", dependencies=[Depends(_auth_dependency)])
async def register(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    # Upsert locally first
    try:
        dpl_id = upsert_register(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build origin droplet_id (prefer fqdn -> id -> name)
    origin_id = data.get("fqdn") or data.get("id") or data.get("name") or "unknown"

    # Mirror to D10 with UDC envelope (source=this droplet, target=10)
    payload = {
        "droplet_id": origin_id,              # <— the origin that registered to droplet-1
        "ip": data.get("ip"),
        "role": data.get("role"),
        "env": data.get("env"),
        "version": data.get("version"),
    }
    envelope = _udc_envelope(payload)
    background_tasks.add_task(_post_to_orchestrator_registry, envelope)

    return JSONResponse({"id": dpl_id}, status_code=201)

@router.post("/registry/heartbeat", dependencies=[Depends(_auth_dependency)])
async def heartbeat(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if not data.get("id"):
        raise HTTPException(status_code=400, detail="id required")

    ok = update_heartbeat(data)
    if not ok:
        raise HTTPException(status_code=404, detail="unknown droplet")

    # Forward minimal status to D10 (origin carried in payload)
    origin_id = data.get("id") or "unknown"
    payload = {
        "droplet_id": origin_id,
        "ip": data.get("ip"),
        "status": data.get("status"),
        "cpu": data.get("cpu"),
        "mem": data.get("mem"),
        "disk": data.get("disk"),
        "last_seen": data.get("last_seen"),
    }
    envelope = _udc_envelope(payload)
    background_tasks.add_task(_post_to_orchestrator_registry, envelope)

    return {"status": "ok"}

@router.get("/registry/droplets", dependencies=[Depends(_auth_dependency)])
async def droplets():
    return list_droplets()["droplets"]

@router.get("/dashboard", dependencies=[Depends(_auth_dependency)])
async def dashboard():
    return list_droplets()
