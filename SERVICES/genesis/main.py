from fastapi import FastAPI, HTTPException, Request, Depends, Header
from pydantic import BaseModel
from typing import List, Dict, Optional
import subprocess
import logging
import json
import os
import uuid
import datetime

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("genesis")

app = FastAPI(title="Genesis", description="The Source Point for Full Potential OS")

# Configuration
DATA_DIR = "data"
KEYS_FILE = f"{DATA_DIR}/keys.json"
SERVERS_FILE = f"{DATA_DIR}/servers.json"
SERVICES_FILE = f"{DATA_DIR}/services.json"

# Swarm Resilience Secret (Should be ENV in prod)
SWARM_SECRET = "fpai-swarm-genesis-permanent-link-v1"

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Models ---

class AgentAuth(BaseModel):
    agent_name: str
    api_key: str

class EnrollmentRequest(BaseModel):
    key: str
    agent_name: str

class ServerRegistration(BaseModel):
    ip: str
    name: str
    role: str = "worker"
    ssh_port: int = 22
    root_password: Optional[str] = None 

class ServiceRegistration(BaseModel):
    name: str
    port: int
    description: str
    url: str

# --- Storage Helpers ---

def load_json(file_path):
    if not os.path.exists(file_path): return {}
    with open(file_path, 'r') as f: return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w') as f: json.dump(data, f, indent=2)

# --- Core Logic ---

def whitelist_ip(ip_address: str):
    """Execute system command to whitelist IP."""
    try:
        # Unban and Whitelist using sudo (requires sudoers setup)
        subprocess.run(["sudo", "fail2ban-client", "set", "sshd", "unbanip", ip_address], check=False)
        subprocess.run(["sudo", "fail2ban-client", "set", "sshd", "addignoreip", ip_address], check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to whitelist: {e}")
        return False 

# --- Endpoints ---

@app.get("/")
def root():
    return {"service": "Genesis", "status": "online", "motto": "The Source Point"}

@app.post("/auth/agent")
async def agent_handshake(auth: AgentAuth, request: Request):
    """
    Agent connects with Key.
    Returns: Whitelist confirmation + Map of the Universe.
    """
    keys = load_json(KEYS_FILE)
    
    # Validate Key
    if keys.get(auth.agent_name) != auth.api_key:
        raise HTTPException(403, "Invalid Genesis Key")
    
    # Whitelist IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0]
        
    whitelist_ip(client_ip)
    
    # Return The Map
    servers = load_json(SERVERS_FILE)
    services = load_json(SERVICES_FILE)
    
    return {
        "status": "access_granted",
        "ip_whitelisted": client_ip,
        "universe": {
            "servers": servers,
            "services": services,
            "ai_brain": "http://198.54.123.234:8250" # Hardcoded main brain for now
        }
    }

@app.post("/auth/enroll")
async def enroll_agent(req: EnrollmentRequest):
    """Self-register a new agent using the Master Enrollment Key."""
    keys = load_json(KEYS_FILE)
    enrollment_key = keys.get("ENROLLMENT_MASTER_KEY")
    
    if not enrollment_key or req.key != enrollment_key:
        raise HTTPException(403, "Invalid Enrollment Key")
        
    if req.agent_name in keys and keys[req.agent_name] != enrollment_key and "agent-" in keys[req.agent_name]:
        raise HTTPException(409, "Agent already registered.")
        
    # Generate new personal key
    personal_key = f"agent-{uuid.uuid4().hex}"
    keys[req.agent_name] = personal_key
    save_json(KEYS_FILE, keys)
    
    return {
        "status": "enrolled",
        "agent_name": req.agent_name,
        "personal_key": personal_key
    }

@app.get("/auth/verify-key/{api_key}")
async def verify_api_key(api_key: str):
    """Verify an API key and identify the agent (Internal/Service use)."""
    keys = load_json(KEYS_FILE)
    
    # Reverse lookup (inefficient for huge lists, fine for <1000 agents)
    for name, key in keys.items():
        if key == api_key:
            return {"status": "valid", "agent_name": name, "role": "agent"}
            
    raise HTTPException(401, "Invalid Key")

@app.get("/auth/recover-key")
async def recover_enrollment_key(x_swarm_secret: str = Header(None)):
    """
    Emergency Beacon: Retrieve the current Enrollment Key using the Swarm Secret.
    Allows agents to self-heal if they lose auth.
    """
    if x_swarm_secret != SWARM_SECRET:
        logger.warning(f"Invalid Beacon attempt with secret: {x_swarm_secret}")
        raise HTTPException(403, "Invalid Swarm Secret")
    
    keys = load_json(KEYS_FILE)
    enrollment_key = keys.get("ENROLLMENT_MASTER_KEY")
    
    if not enrollment_key:
        # Auto-generate if missing
        enrollment_key = f"enroll-{uuid.uuid4().hex[:12]}"
        keys["ENROLLMENT_MASTER_KEY"] = enrollment_key
        save_json(KEYS_FILE, keys)
        
    return {"enrollment_key": enrollment_key}

@app.post("/admin/set-enrollment-key")
async def set_enrollment_key():
    """Generate or Rotate the Master Enrollment Key."""
    keys = load_json(KEYS_FILE)
    new_key = f"enroll-{uuid.uuid4().hex[:12]}"
    keys["ENROLLMENT_MASTER_KEY"] = new_key
    save_json(KEYS_FILE, keys)
    return {"enrollment_key": new_key}

@app.post("/admin/generate-key")
async def generate_key(agent_name: str):
    """Generate a new Agent Key (Admin only - protected by network/auth in future)."""
    keys = load_json(KEYS_FILE)
    new_key = f"genesis-{uuid.uuid4().hex[:8]}"
    keys[agent_name] = new_key
    save_json(KEYS_FILE, keys)
    return {"agent": agent_name, "key": new_key}

@app.get("/registry/agents")
async def list_agents():
    """List all registered agents (Admin)."""
    keys = load_json(KEYS_FILE)
    agents = []
    for name, key in keys.items():
        if name == "ENROLLMENT_MASTER_KEY": continue
        agents.append({"name": name, "type": "agent" if "agent-" in key else "genesis_minted"})
    return {"agents": agents}

@app.get("/registry/services")
async def list_services():
    """List all registered services."""
    return load_json(SERVICES_FILE)

@app.get("/registry/servers")
async def list_servers():
    """List all registered servers."""
    return load_json(SERVERS_FILE)

@app.post("/registry/servers")
async def register_server(server: ServerRegistration):
    """Register a new server."""
    servers = load_json(SERVERS_FILE)
    servers[server.name] = {
        "ip": server.ip,
        "role": server.role,
        "port": server.ssh_port,
        "added_at": str(datetime.datetime.utcnow())
    }
    save_json(SERVERS_FILE, servers)
    return {"status": "registered", "server": server.name}

@app.post("/registry/services")
async def register_service(service: ServiceRegistration):
    """Register a service."""
    services = load_json(SERVICES_FILE)
    services[service.name] = service.dict()
    save_json(SERVICES_FILE, services)
    return {"status": "registered", "service": service.name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8150)
