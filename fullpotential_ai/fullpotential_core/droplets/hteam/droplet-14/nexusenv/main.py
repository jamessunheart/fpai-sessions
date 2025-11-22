from fastapi import FastAPI
from datetime import datetime
import os, hashlib

app = FastAPI()

@app.get("/health")
def health_check():
    uptime = float(os.popen("awk '{print $1}' /proc/uptime").read().strip())
    proof = hashlib.sha256(f"drop14_{uptime}".encode()).hexdigest()
    return {
        "ok": True,
        "uptime": uptime,
        "droplet": "drop14.fullpotential.ai",
        "status": "healthy",
        "proof": proof,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/getAll")
def get_all():
    return {"detail": "Drop14 responding OK"}
