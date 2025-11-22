from fastapi import FastAPI
from app.services.brain_generator import BrainGenerator
import datetime

app = FastAPI(title="Registry 2.0")

@app.on_event("startup")
async def startup_event():
    brain = BrainGenerator()
    brain.generate_manifest({
        "id": "18",
        "name": "Registry 2.0",
        "connections": ["13","14","16"]
    })

@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "registry-2.0",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "brain": {"status": "active"}
    }
