import dotenv; dotenv.load_dotenv()
from fastapi import FastAPI, Header, HTTPException, Request
from typing import Optional
import os, time

app = FastAPI()
REG_KEY = os.getenv("REGISTRY_KEY","")

@app.get("/health")
def health():
    return {"ok": True, "service": "registry", "droplet": "drop3", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

@app.post("/registry/register")
async def register(req: Request, x_registry_key: Optional[str]=Header(None)):
    if REG_KEY and (x_registry_key or "") != REG_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await req.json()
    return {"id": body.get("fqdn","unknown"), "status": "registered"}

@app.post("/registry/heartbeat")
async def heartbeat(req: Request, x_registry_key: Optional[str]=Header(None)):
    if REG_KEY and (x_registry_key or "") != REG_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await req.json()
    return {
        "status":"ok",
        "id": body.get("id","unknown"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

# --- temporary alias for legacy droplets ---
@app.post("/register")
async def legacy_register(request: Request):
    """Redirect /register → /registry/register for backward compatibility"""
    body = await request.json()
    from fastapi.responses import JSONResponse
    return JSONResponse({"redirected": True, "target": "/registry/register", "body": body})
