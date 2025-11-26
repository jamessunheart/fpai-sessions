from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from typing import Optional
import httpx
from auth import (
    LoginRequest, Token, authenticate_user, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Master Control Dashboard", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Login page"""
    with open("templates/login.html", "r") as f:
        return f.read()

@app.post("/api/login", response_model=Token)
async def login(login_request: LoginRequest, response: Response):
    """Authenticate and create session"""
    if not authenticate_user(login_request.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "james@fullpotential.ai"},
        expires_delta=access_token_expires
    )

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=True  # Only over HTTPS
    )

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/logout")
async def logout(response: Response):
    """Logout and clear session"""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(username: str = Depends(get_current_user)):
    """Protected dashboard - requires authentication"""
    with open("templates/dashboard.html", "r") as f:
        return f.read()

@app.get("/health")
async def health():
    """UDC Endpoint 1: Health check"""
    from datetime import datetime
    return {
        "status": "active",
        "service": "master-dashboard",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/capabilities")
async def capabilities():
    """UDC Endpoint 2: Service capabilities"""
    return {
        "version": "1.0.0",
        "features": [
            "Master control dashboard",
            "Service status monitoring",
            "Authentication and authorization",
            "Unified service access"
        ],
        "dependencies": ["credential-vault", "registry"],
        "udc_version": "1.0",
        "metadata": {
            "auth_enabled": True,
            "monitored_services": 6
        }
    }


@app.get("/state")
async def state():
    """UDC Endpoint 3: Resource usage and performance"""
    from datetime import datetime
    return {
        "uptime_seconds": 0,
        "requests_total": 0,
        "requests_per_minute": 0.0,
        "errors_last_hour": 0,
        "last_restart": datetime.utcnow().isoformat() + "Z",
        "resource_usage": {
            "status": "operational",
            "load": "normal"
        }
    }


@app.get("/dependencies")
async def dependencies():
    """UDC Endpoint 4: Service dependencies"""
    return {
        "required": [],
        "optional": [
            "credential-vault",
            "registry",
            "orchestrator",
            "i-proactive",
            "i-match"
        ],
        "missing": [],
        "integrations": {
            "auth": "Authentication system",
            "monitoring": "Service health checks"
        }
    }


@app.post("/message")
async def message(payload: dict):
    """UDC Endpoint 5: Inter-service messaging"""
    from datetime import datetime
    return {
        "status": "received",
        "message_id": f"msg-{datetime.utcnow().timestamp()}",
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "service": "master-dashboard"
    }

@app.get("/api/services/status")
async def services_status(username: str = Depends(get_current_user)):
    """Get status of all services - requires authentication"""
    services = {
        "credential_vault": {"url": "https://fullpotential.com/vault/health", "name": "Credential Vault"},
        "dashboard": {"url": "http://198.54.123.234:8002", "name": "Dashboard"},
        "registry": {"url": "http://198.54.123.234:8000", "name": "Registry"},
        "orchestrator": {"url": "http://198.54.123.234:8001", "name": "Orchestrator"},
        "i_proactive": {"url": "http://198.54.123.234:8400", "name": "I PROACTIVE"},
        "i_match": {"url": "http://198.54.123.234:8401", "name": "I MATCH"},
    }

    status = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for key, service in services.items():
            try:
                resp = await client.get(service["url"])
                status[key] = {
                    "name": service["name"],
                    "status": "online" if resp.status_code == 200 else "error",
                    "url": service["url"]
                }
            except:
                status[key] = {
                    "name": service["name"],
                    "status": "offline",
                    "url": service["url"]
                }

    return status

@app.get("/api/me")
async def get_me(username: str = Depends(get_current_user)):
    """Get current user info"""
    return {"username": username, "authenticated": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8026)
