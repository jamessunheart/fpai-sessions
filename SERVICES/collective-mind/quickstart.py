from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import json

app = FastAPI()

sessions = {}
thoughts = []

class SessionReg(BaseModel):
    session_id: str
    role: Optional[str] = "general"
    location: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Collective Mind - Quick Start", "sessions": len(sessions)}

@app.post("/register")
async def register(s: SessionReg):
    sessions[s.session_id] = {"id": s.session_id, "role": s.role, "location": s.location, "joined": datetime.now().isoformat()}
    return {"status": "connected", "total_sessions": len(sessions)}

@app.get("/sessions")
async def get_sessions():
    return {"sessions": sessions, "count": len(sessions)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
