# app/server.py
from __future__ import annotations
import os
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException

from memory_mem0 import MemoryMem0
from app.registry import router as registry_router
from app.udc import router as udc_router
from app.registry.sync_airtable import start_sync_loop

load_dotenv()

def load_settings() -> dict:
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def create_app() -> FastAPI:
    app = FastAPI(title="Full Potential OS", version="v.521-M")

    # app state
    app.state.settings = {}
    app.state.mem = MemoryMem0(api_key=os.getenv("MEM0_API_KEY"))

    # routers
    app.include_router(registry_router)
    app.include_router(udc_router)

    @app.on_event("startup")
    def _on_startup():
        # load config
        try:
            app.state.settings = load_settings() or {}
        except Exception:
            app.state.settings = {}
        # start Airtable sync loop (non-blocking)
        start_sync_loop(interval=60)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": app.version}

    @app.post("/chat")
    async def chat(req: Request):
        body = await req.json()
        role = body.get("role", "user")
        content = body.get("content", "")
        user_id = body.get("user_id")
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        try:
            app.state.mem.store(role, content, user_id=user_id)
            return {"stored": True, "echo": content}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/reflect")
    async def reflect(req: Request):
        body = await req.json()
        try:
            app.state.mem.reflect(
                summary=body.get("summary", ""),
                insights=body.get("insights", []),
                decisions=body.get("decisions", []),
                user_id=body.get("user_id"),
            )
            return {"stored": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/intent")
    async def intent(req: Request):
        body = await req.json()
        try:
            app.state.mem.intent(
                intent=body.get("intent", ""),
                horizon_min=body.get("horizon_min", 60),
                tags=body.get("tags"),
                user_id=body.get("user_id"),
            )
            return {"stored": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app

app = create_app()

