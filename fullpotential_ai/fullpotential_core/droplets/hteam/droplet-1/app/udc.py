from __future__ import annotations
import os, time, psutil, yaml, threading, json
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
from jsonschema import validate, ValidationError

from .security import require_jwt  # FastAPI version of require_jwt (as a dependency)

router = APIRouter()

BOOT_TS = time.time()
DROPLET_ID = os.getenv("DROPLET_ID", "drop1")
UDC_VERSION = os.getenv("UDC_VERSION", "1.0")

# ---- events log (observability) ----
EVENTS = deque(maxlen=500)
def _event(kind: str, detail: str = ""):
    EVENTS.append({"ts": int(time.time()), "droplet": DROPLET_ID, "kind": kind, "detail": detail})

# ---- UDC ENVELOPE (new) ----
UDC_ENVELOPE = {
    "type": "object",
    "required": ["udc_version","trace_id","source","target","message_type","payload","timestamp"],
    "properties": {
        "udc_version": {"type": "string", "enum": [UDC_VERSION, "1.0"]},
        "trace_id": {"type": "string"},
        "source": {"type": "string"},
        "target": {"type": "string"},
        "message_type": {
            "type": "string",
            "enum": ["status","event","command","query","proof","registry"]
        },
        "payload": {"type": "object"},
        "timestamp": {"type": "string"}  # ISO-8601 string
    }
}


# ---- Prometheus metrics ----
REG = CollectorRegistry()
G_CPU = Gauge("droplet_cpu_percent", "CPU percent", registry=REG)
G_MEM = Gauge("droplet_mem_percent", "Memory percent", registry=REG)
G_UP  = Gauge("droplet_uptime_seconds", "Uptime seconds", registry=REG)

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/capabilities")
async def capabilities():
    return {
        "udc_version": UDC_VERSION,
        "features": ["registry", "airtable_sync", "orchestrator_forward"],
        "endpoints": [
            "/health","/capabilities","/state","/dependencies",
            "/message","/send","/reload-config","/shutdown","/emergency-stop",
            "/metrics","/logs","/events","/version","/proof"
        ],
    }

@router.get("/state")
async def state():
    cpu = psutil.cpu_percent(interval=0.0)
    mem = psutil.virtual_memory().percent
    uptime = int(time.time() - BOOT_TS)
    # update metrics
    G_CPU.set(cpu); G_MEM.set(mem); G_UP.set(uptime)
    return {"cpu": cpu, "mem": mem, "uptime_sec": uptime}

@router.get("/dependencies")
async def deps():
    # reuse your existing registry list as "connected droplets"
    try:
        from .registry.store import list_droplets
        dl = list_droplets().get("droplets", [])
        return {"connected": [d.get("fqdn") for d in dl]}
    except Exception:
        return {"connected": []}

@router.post("/message", dependencies=[Depends(require_jwt)])
async def message(request: Request):
    body = await request.json()
    try:
        validate(body, UDC_ENVELOPE)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"schema: {e.message}")

    _event("message_received", body.get("message_type",""))
    # store last proof if message_type == "proof"
    if body.get("message_type") == "proof":
        request.app.state.LAST_PROOF = {
            "ts": int(time.time()),
            "droplet": DROPLET_ID,
            "trace_id": body["trace_id"],
            "message_type": body["message_type"],
        }
    return JSONResponse({"status": "accepted"}, status_code=202)

@router.post("/send", dependencies=[Depends(require_jwt)])
async def send(request: Request):
    body = await request.json()
    try:
        validate(body, UDC_ENVELOPE)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"schema: {e.message}")

    _event("message_sent", body.get("message_type",""))
    # enqueue/forward happens elsewhere; UDC just validates/enqueues
    return JSONResponse({"status": "queued"}, status_code=202)

@router.post("/reload-config", dependencies=[Depends(require_jwt)])
async def reload_config(request: Request):
    try:
        with open("config/settings.yaml","r",encoding="utf-8") as f:
            settings = yaml.safe_load(f)
        request.app.state.SETTINGS = settings
        _event("config_reloaded")
        return {"reloaded": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reload failed: {e}")

@router.post("/shutdown", dependencies=[Depends(require_jwt)])
async def shutdown():
    _event("shutdown_requested")
    threading.Thread(target=lambda: os._exit(0), daemon=True).start()
    return {"status": "shutting_down"}

@router.post("/emergency-stop", dependencies=[Depends(require_jwt)])
async def emergency_stop():
    _event("emergency_stop")
    os._exit(1)

@router.get("/metrics")
async def metrics():
    # refresh snapshot so gauges reflect current values
    psutil.cpu_percent(0.0)
    data = generate_latest(REG)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@router.get("/logs", dependencies=[Depends(require_jwt)])
async def logs():
    path = "logs/app.log"
    try:
        with open(path, "rb") as f:
            data = f.readlines()[-200:]
        return PlainTextResponse(b"".join(data))
    except Exception:
        return PlainTextResponse(b"")

@router.get("/events")
async def events():
    return list(EVENTS)

@router.get("/version")
async def version():
    return {
        "build": os.getenv("BUILD_ID","local"),
        "commit": os.getenv("GIT_SHA",""),
        "time": os.getenv("BUILD_TIME",""),
    }

@router.get("/proof")
async def proof(request: Request):
    return getattr(request.app.state, "LAST_PROOF", {})
