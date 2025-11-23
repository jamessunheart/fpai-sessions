from fastapi import FastAPI
from datetime import datetime
from app.routers import api
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(api.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {
        "status": "active",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/capabilities")
async def capabilities():
    return {
        "name": "verifier-service",
        "version": "1.0.0",
        "capabilities": ["udc-scan", "security-scan"]
    }

