import uvicorn
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
import uuid
import httpx

app = FastAPI(title="God Mode Core")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PATHS ---
COORDINATION_DIR = Path(os.getenv("COORDINATION_DIR", "../../../docs/coordination")).resolve()
INBOX_FILE = Path(os.getenv("INBOX_FILE", "../../../core/STATE/INBOX.json")).resolve()
TREASURY_FILE = Path(os.getenv("TREASURY_FILE", "../../../core/STATE/TREASURY.json")).resolve()

INTENTS_DIR = COORDINATION_DIR / "intents"
CLAIMS_DIR = COORDINATION_DIR / "claims"
HEARTBEATS_DIR = COORDINATION_DIR / "heartbeats"
MESSAGES_DIR = COORDINATION_DIR / "messages/broadcast"

API_PORTAL_URL = os.getenv("API_PORTAL_URL", "http://172.17.0.1:8651")
AUTO_HEALER_URL = os.getenv("AUTO_HEALER_URL", "http://172.17.0.1:8180")
TRADING_URL = os.getenv("TRADING_URL", "http://198.54.123.234:8600")
CONSCIOUSNESS_VERIFIER_URL = os.getenv("CONSCIOUSNESS_VERIFIER_URL", "http://162.0.208.88:8140")

# Data System (primary host services are often reachable via docker-gateway 172.17.0.1)
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL", "http://198.54.123.234:8120")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://198.54.123.234:8125")
STRATEGIC_INTEL_URL = os.getenv("STRATEGIC_INTEL_URL", "http://198.54.123.234:8500")
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
SERVICE_REGISTRY_FILE = COORDINATION_DIR / "SERVICE_REGISTRY.md"
SSOT_FILE = COORDINATION_DIR / "SSOT.json"

# ------------------------------------------------------------------------------
# SSOT-based routing (preferred) — keeps God Mode aligned with system truth.
# ------------------------------------------------------------------------------

def _load_ssot(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return None

def _ssot_routing_url(ssot: dict | None, key: str) -> str | None:
    try:
        if not ssot:
            return None
        url = ssot.get("fleet", {}).get("routing", {}).get(key)
        return str(url) if url else None
    except Exception:
        return None

def _find_service_endpoint(ssot: dict | None, service_prefix: str) -> tuple[str | None, int | None]:
    if not ssot:
        return (None, None)
    nodes = ssot.get("fleet", {}).get("nodes", [])
    if not isinstance(nodes, list):
        return (None, None)

    def _walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from _walk(v)
        elif isinstance(obj, str):
            yield obj

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_ip = node.get("ip")
        for s in _walk(node.get("services", {})):
            if not isinstance(s, str):
                continue
            if s.startswith(service_prefix + ":"):
                try:
                    port = int(s.split(":", 1)[1])
                except Exception:
                    port = None
                return (str(node_ip) if node_ip else None, port)
    return (None, None)

_SSOT = _load_ssot(SSOT_FILE)

# Apply SSOT routing only when env vars are not explicitly set.
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL") or _ssot_routing_url(_SSOT, "ai_inference") or AI_BRAIN_URL
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL") or _ssot_routing_url(_SSOT, "data_service") or DATA_SERVICE_URL
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL") or _ssot_routing_url(_SSOT, "nerve_center") or NERVE_CENTER_URL
TRADING_URL = os.getenv("TRADING_URL") or _ssot_routing_url(_SSOT, "trading") or TRADING_URL

_cv_host, _cv_port = _find_service_endpoint(_SSOT, "fpai-consciousness_verifier")
if not os.getenv("CONSCIOUSNESS_VERIFIER_URL") and _cv_host and _cv_port:
    CONSCIOUSNESS_VERIFIER_URL = f"http://{_cv_host}:{_cv_port}"

# Aria (Admin Control Plane) - Now unified AI assistant on secondary server
# Can reach via public IP or internal network
ARIA_URL = os.getenv("ARIA_URL", "http://162.0.208.88:8180")

# Ensure dirs
MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
INTENTS_DIR.mkdir(parents=True, exist_ok=True)

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# --- DATA HELPERS ---

def get_graph_data():
    nodes = []
    links = []
    seen_agents = set()

    if HEARTBEATS_DIR.exists():
        files = sorted(list(HEARTBEATS_DIR.glob("*.json")), reverse=True)[:50]
        for f in files:
            try:
                name = f.stem.split('-session-')[-1] if 'session' in f.stem else f.stem
                if name not in seen_agents:
                    nodes.append({"id": name, "group": "agent", "status": "active"})
                    seen_agents.add(name)
            except:
                pass

    if CLAIMS_DIR.exists():
        for f in CLAIMS_DIR.glob("*.claim"):
            try:
                with open(f) as cf:
                    data = json.load(cf)
                    session_id = data.get("session_id", "unknown")
                    resource = f.stem
                    nodes.append({"id": resource, "group": "work", "status": "claimed"})
                    links.append({"source": session_id, "target": resource})
                    if session_id not in seen_agents:
                        nodes.append({"id": session_id, "group": "agent", "status": "working"})
                        seen_agents.add(session_id)
            except:
                pass
                
    for core in ["Brain", "Muscle", "Immune", "Architect"]:
        if core not in seen_agents:
            nodes.append({"id": core, "group": "core", "status": "idle"})

    return {"nodes": nodes, "links": links}

def get_messages(limit=20):
    msgs = []
    if MESSAGES_DIR.exists():
        files = sorted(list(MESSAGES_DIR.glob("*.json")), reverse=True)[:limit]
        for f in files:
            try:
                with open(f) as jf:
                    data = json.load(jf)
                    msgs.append(data)
            except:
                pass
    return sorted(msgs, key=lambda x: x.get('timestamp', ''))

def get_kanban_data():
    board = {
        "intent": [],
        "building": [],
        "deployed": []
    }
    claims = set()
    if CLAIMS_DIR.exists():
        for f in CLAIMS_DIR.glob("*.claim"):
            claims.add(f.stem)

    if INTENTS_DIR.exists():
        for f in INTENTS_DIR.glob("*.json"):
            try:
                with open(f) as jf:
                    data = json.load(jf)
                    item = {
                        "id": f.stem,
                        "title": data.get("droplet_name", f.stem),
                        "desc": data.get("architect_intent", ""),
                        "score": data.get("score", 0)
                    }
                    is_claimed = False
                    for claim in claims:
                        if item["id"] in claim or item["title"] in claim:
                            is_claimed = True
                            break
                    
                    if is_claimed:
                        board["building"].append(item)
                    else:
                        board["intent"].append(item)
            except:
                pass
    return board

def get_treasury_data():
    # Default structure
    data = {
        "tvl": 0,
        "pnl_24h": 0,
        "pnl_percent": 0,
        "cash": 0,
        "allocation": {"stable": 0, "blue_chip": 0, "moonshot": 0},
        "positions": [],
        "magnet_engine": {
            "status": "OFFLINE",
            "leverage": 1.0,
            "magnet_strength": 0,
            "distance": 0,
            "conflict": 0,
            "volatility": 0
        }
    }
    
    if TREASURY_FILE.exists():
        try:
            with open(TREASURY_FILE, 'r') as f:
                file_data = json.load(f)
                data.update(file_data)
        except: pass
    
    return data

async def _safe_get_json(url: str, timeout_s: float = 3.0):
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None

async def _safe_post_json(url: str, payload: dict, timeout_s: float = 8.0):
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code in [200, 201, 202]:
                try:
                    return resp.json()
                except Exception:
                    return {"status_code": resp.status_code}
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e)}

def _parse_markdown_table_rows(md_text: str) -> list[list[str]]:
    """
    Parse basic markdown tables into rows of cells.
    Only supports pipes-based rows, skipping separator rows.
    """
    rows: list[list[str]] = []
    for raw in md_text.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        # Skip header separators like |---|---|
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
    return rows

def _load_service_registry() -> dict:
    """
    Best-effort parse of docs/coordination/SERVICE_REGISTRY.md.
    Returns structured lists for primary/secondary and stopped-on-purpose.
    """
    result = {
        "primary": [],
        "secondary": [],
        "stopped_on_primary": [],
        "errors": []
    }
    if not SERVICE_REGISTRY_FILE.exists():
        result["errors"].append(f"Missing file: {SERVICE_REGISTRY_FILE}")
        return result

    text = SERVICE_REGISTRY_FILE.read_text(errors="ignore")
    rows = _parse_markdown_table_rows(text)

    # Heuristics: rows with 4 columns matching the quick lookup tables
    for r in rows:
        if len(r) < 3:
            continue
        # Quick lookup tables (Service | Port | Status | Purpose)
        if len(r) >= 4 and r[0].lower() == "service" and r[1].lower() == "port":
            continue
        if len(r) >= 4 and r[0] and r[1] and r[2]:
            svc = r[0]
            port_raw = r[1]
            status = r[2]
            purpose = r[3] if len(r) > 3 else ""
            port = None
            try:
                if port_raw and port_raw.strip().isdigit():
                    port = int(port_raw.strip())
            except Exception:
                port = None
            entry = {"service": svc, "port": port, "port_raw": port_raw, "status": status, "purpose": purpose}

            # classify primary/secondary by common known services in purpose/status lines around the file
            # We infer by service name hints (good enough for scan/report UI)
            if svc in ("ai-brain", "ollama") or "secondary" in purpose.lower():
                result["secondary"].append(entry)
            else:
                result["primary"].append(entry)

    # Stopped-on-primary table (Service | Reason | Alternative Location)
    for r in rows:
        if len(r) >= 3 and r[0] and r[1] and r[2]:
            if r[0].lower() == "service" and "reason" in r[1].lower():
                continue
            if r[1].lower() in ("reason", "purpose"):
                continue
            # detect section by specific known service strings
            if r[0].startswith("fpai-") and "DO NOT restart" in text:
                # best-effort: include all fpai-* rows that appear in stopped section
                # we'll filter by known alternatives indicator
                if "secondary" in (r[2] or "").lower() or "stopped" in (r[1] or "").lower() or "duplicate" in (r[1] or "").lower():
                    result["stopped_on_primary"].append({"service": r[0], "reason": r[1], "alternative": r[2]})

    return result

async def _check_health_endpoints(services: list[dict]) -> list[dict]:
    """
    Try /health for services with known ports on docker-gateway host.
    """
    checks = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for s in services:
            port = s.get("port")
            if not port:
                continue
            url = f"http://172.17.0.1:{port}/health"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    checks.append({"service": s.get("service"), "port": port, "url": url, "ok": True, "data": data})
                else:
                    checks.append({"service": s.get("service"), "port": port, "url": url, "ok": False, "status_code": resp.status_code})
            except Exception as e:
                checks.append({"service": s.get("service"), "port": port, "url": url, "ok": False, "error": str(e)})
    return checks

@app.get("/api/unify/scan")
async def unify_scan():
    """
    System Unification scan:
    - Reads Service Registry (docs)
    - Reads current health feed (if available)
    - Probes key /health endpoints
    - Outputs LIVE vs REDUNDANT vs THEATER candidates
    """
    registry = _load_service_registry()
    system_health = await get_system_health()
    health_checks = await _check_health_endpoints(registry.get("primary", []))

    # Build maps for quick decisions
    ok_by_service = {c["service"]: c for c in health_checks if c.get("ok")}
    status_map = (system_health or {}).get("services", {}) if isinstance(system_health, dict) else {}

    live = []
    theater = []
    unknown = []
    redundant = []

    for s in registry.get("primary", []):
        name = s.get("service")
        # Evidence signals
        ok = name in ok_by_service
        systemd_state = status_map.get(name)
        if ok:
            live.append({"service": name, "evidence": {"health": ok_by_service[name], "systemd": systemd_state}, "purpose": s.get("purpose", "")})
        elif systemd_state == "active":
            unknown.append({"service": name, "evidence": {"systemd": systemd_state}, "purpose": s.get("purpose", ""), "note": "Active in system health but /health probe failed or unknown"})
        else:
            theater.append({"service": name, "evidence": {"health_probe": ok_by_service.get(name), "systemd": systemd_state}, "purpose": s.get("purpose", ""), "note": "Documented but no evidence of health"})

    # Redundancy candidates: stopped-on-primary list that appears active in system health
    for s in registry.get("stopped_on_primary", []):
        name = s.get("service")
        if status_map.get(name) == "active":
            redundant.append({"service": name, "reason": s.get("reason"), "alternative": s.get("alternative"), "note": "Marked stopped-on-primary but currently active"})

    return {
        "timestamp": datetime.now().isoformat(),
        "registry": registry,
        "observed": {
            "system_health": system_health,
            "health_checks": health_checks
        },
        "classification": {
            "live_useful": live,
            "unknown": unknown,
            "theater_candidates": theater,
            "redundant_candidates": redundant
        }
    }

@app.post("/api/unify/ingest")
async def unify_ingest(payload: dict = Body(...)):
    """
    Ingest an agent's handoff/summary into long-term memory (Data Service / Mem0).
    This enables Aria to consolidate and reduce redundancy over time.
    """
    session_id = payload.get("session_id", "unknown")
    title = payload.get("title", "Agent Report")
    summary = payload.get("summary", "")
    components = payload.get("components", [])
    recommendations = payload.get("recommendations", [])
    confidence = payload.get("confidence", "")

    if not summary:
        return {"error": "summary required"}

    # Store as a learning record (context/action/outcome/lesson)
    context = f"Agent report | session={session_id} | title={title} | confidence={confidence}"
    action = f"Shared components={components} recommendations={recommendations}"
    outcome = "captured_for_unification"
    lesson = summary

    result = await _safe_post_json(
        f"{DATA_SERVICE_URL.rstrip('/')}/api/data/memory/learn",
        {"context": context, "action": action, "outcome": outcome, "lesson": lesson},
        timeout_s=12.0
    )
    return {"status": "ok", "stored": result}

# --- API ENDPOINTS ---

@app.get("/health")
async def health_check():
    """Standard health endpoint for system monitoring."""
    return {"status": "healthy", "service": "god-mode-backend", "timestamp": datetime.now().isoformat()}

@app.get("/api/health")
async def health():
    return {"status": "God Mode Online", "timestamp": datetime.now().isoformat()}


# ────────────────────────────────────────────────────────────────────────────────
# Aria Admin Proxy (keeps God Mode as the single cockpit)
# ────────────────────────────────────────────────────────────────────────────────

def _require_aria_token(req: Request) -> str:
    token = req.headers.get("X-Aria-Admin-Token", "")
    if not token:
        raise HTTPException(status_code=401, detail="X-Aria-Admin-Token required")
    return token

async def _aria_get(path: str, token: str):
    url = f"{ARIA_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"X-Aria-Admin-Token": token})
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e)}

async def _aria_post(path: str, token: str, payload: dict):
    url = f"{ARIA_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, json=payload, headers={"X-Aria-Admin-Token": token})
            if resp.status_code in (200, 201, 202):
                try:
                    return resp.json()
                except Exception:
                    return {"status_code": resp.status_code}
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/aria/system")
async def aria_system(req: Request):
    token = _require_aria_token(req)
    return await _aria_get("/admin/system", token)

@app.get("/api/aria/capabilities")
async def aria_capabilities(req: Request):
    token = _require_aria_token(req)
    return await _aria_get("/admin/capabilities", token)

@app.post("/api/aria/chat")
async def aria_chat(req: Request, payload: dict = Body(...)):
    """
    Chat with ARIA - the unified AI assistant.
    Now connects to the new sovereignty-first ARIA on secondary server.
    """
    message = payload.get("message", "")
    task_type = payload.get("task_type", "general")
    session_id = payload.get("session_id")
    
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    
    # Call new ARIA chat endpoint directly (no admin token needed)
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ARIA_URL}/chat",
                json={
                    "message": message,
                    "task_type": task_type,
                    "session_id": session_id,
                }
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/aria/health")
async def aria_health():
    """Get ARIA health status."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ARIA_URL}/health")
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e), "aria_url": ARIA_URL}


@app.get("/api/aria/stats")
async def aria_stats():
    """Get ARIA usage statistics."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ARIA_URL}/stats")
            if resp.status_code == 200:
                return resp.json()
            return {"error": resp.text, "status_code": resp.status_code}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# NERVOUS SYSTEM INTEGRATION
# ============================================================================

# ============================================================================
# AUTONOMY INTELLIGENCE STORE
# Complete system awareness passed from Autonomy Optimizer
# ============================================================================

_system_intelligence = {
    # Nervous System Data
    "nervous_system": {
        "last_update": None,
        "services": {},
        "api_needs": {},
        "predictions": [],
        "health_summary": {},
        "learned_patterns": 0
    },
    # Resilience Data
    "resilience": {
        "last_update": None,
        "degradation_level": "normal",
        "circuit_breakers": {},
        "providers": {},
        "resources": {},
        "scaling": {}
    },
    # Health Monitor Data
    "health": {
        "last_update": None,
        "services": {},
        "healthy_count": 0,
        "total_count": 0,
        "incidents": []
    },
    # Notifications
    "notifications": [],
    # System Traits (capabilities)
    "traits": {
        "self_aware": True,
        "self_healing": True,
        "predictive": True,
        "safe_scaling": True,
        "graceful_degradation": True,
        "provider_failover": True,
        "circuit_breakers": True,
        "proactive_alerts": True
    }
}

@app.post("/api/nervous-system-update")
async def receive_nervous_system_update(data: dict):
    """
    Receive real-time updates from the Nervous System.
    This enables God Mode to display proactive intelligence.
    """
    global _system_intelligence
    _system_intelligence["nervous_system"] = {
        "last_update": data.get("timestamp"),
        "services": data.get("services", {}),
        "api_needs": data.get("api_needs", {}),
        "predictions": data.get("predictions", []),
        "health_summary": data.get("health_summary", {}),
        "learned_patterns": data.get("learned_patterns", 0)
    }
    
    # Broadcast to connected WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "nervous_system_update",
        "data": _system_intelligence["nervous_system"]
    }))
    
    return {"status": "received"}

@app.post("/api/resilience-update")
async def receive_resilience_update(data: dict):
    """
    Receive resilience engine updates.
    Includes circuit breakers, provider failover, degradation level.
    """
    global _system_intelligence
    _system_intelligence["resilience"] = {
        "last_update": datetime.now().isoformat(),
        "degradation_level": data.get("degradation_level", "normal"),
        "circuit_breakers": data.get("circuit_breakers", {}),
        "providers": data.get("providers", {}),
        "resources": data.get("resources", {}),
        "scaling": data.get("scaling", {}),
        "degradation": data.get("degradation", {})
    }
    
    # Broadcast to connected WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "resilience_update",
        "data": _system_intelligence["resilience"]
    }))
    
    return {"status": "received"}

@app.post("/api/health-update")
async def receive_health_update(data: dict):
    """
    Receive health monitor updates.
    """
    global _system_intelligence
    _system_intelligence["health"] = {
        "last_update": data.get("timestamp"),
        "services": data.get("services", {}),
        "healthy_count": data.get("healthy", 0),
        "total_count": data.get("total", 0),
        "incidents": data.get("incidents", [])[:20]
    }
    
    # Broadcast to connected WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "health_update",
        "data": _system_intelligence["health"]
    }))
    
    return {"status": "received"}

@app.get("/api/nervous-system")
async def get_nervous_system_data():
    """Get current nervous system intelligence for display."""
    return _system_intelligence["nervous_system"]

@app.get("/api/resilience")
async def get_resilience_data():
    """Get current resilience status for display."""
    # If no data received yet, fetch from autonomy optimizer
    if not _system_intelligence["resilience"].get("last_update"):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:8900/api/v1/resilience/status")
                if resp.status_code == 200:
                    data = resp.json()
                    _system_intelligence["resilience"] = {
                        "last_update": data.get("timestamp"),
                        "degradation_level": data.get("degradation_level", "normal"),
                        "circuit_breakers": data.get("circuit_breakers", {}),
                        "providers": data.get("providers", {}),
                        "resources": data.get("resources", {}),
                        "scaling": data.get("scaling", {}),
                        "degradation": data.get("degradation", {})
                    }
        except:
            pass
    return _system_intelligence["resilience"]

@app.get("/api/system-health")
async def get_system_health():
    """Get current system health for display."""
    # Fetch fresh data if needed
    if not _system_intelligence["health"].get("last_update"):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:8900/api/v1/system/health")
                if resp.status_code == 200:
                    data = resp.json()
                    _system_intelligence["health"] = {
                        "last_update": datetime.now().isoformat(),
                        "services": data.get("services", {}),
                        "healthy_count": data.get("healthy", 0),
                        "total_count": data.get("total", 0),
                        "incidents": data.get("recent_incidents", [])[:20]
                    }
        except:
            pass
    return _system_intelligence["health"]

@app.get("/api/system-intelligence")
async def get_complete_intelligence():
    """
    Get COMPLETE system intelligence - all traits and capabilities.
    This is the master endpoint for God Mode dashboard.
    """
    dashboard = {}
    resilience = {}
    nervous = {}
    
    # Fetch fresh data from autonomy optimizer
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get dashboard summary
            try:
                dash_resp = await client.get("http://127.0.0.1:8900/api/v1/system/dashboard")
                if dash_resp.status_code == 200:
                    dashboard = dash_resp.json()
            except Exception as e:
                print(f"Dashboard fetch error: {e}")
            
            # Get resilience status
            try:
                res_resp = await client.get("http://127.0.0.1:8900/api/v1/resilience/status")
                if res_resp.status_code == 200:
                    resilience = res_resp.json()
            except Exception as e:
                print(f"Resilience fetch error: {e}")
            
            # Get nervous system status
            try:
                ns_resp = await client.get("http://127.0.0.1:8900/api/v1/nervous-system/status")
                if ns_resp.status_code == 200:
                    nervous = ns_resp.json()
            except Exception as e:
                print(f"Nervous system fetch error: {e}")
            
    except Exception as e:
        print(f"Overall fetch error: {e}")
    
    return {
        "timestamp": datetime.now().isoformat(),
        
        # System Traits (capabilities)
        "traits": _system_intelligence["traits"],
        
        # Overall Status
        "status": {
            "ecosystem_health": dashboard.get("ecosystem_health_score", 0),
            "operational_status": dashboard.get("status", "unknown"),
            "degradation_level": resilience.get("degradation_level", "normal"),
            "services_healthy": dashboard.get("services", {}).get("healthy", 0),
            "services_total": dashboard.get("services", {}).get("total", 0)
        },
        
        # Nervous System (Awareness & Prediction)
        "awareness": {
            "services_monitored": nervous.get("services_aware", 0),
            "patterns_learned": nervous.get("patterns_learned", 0),
            "active_predictions": nervous.get("active_predictions", 0),
            "top_predictions": nervous.get("top_predictions", [])
        },
        
        # Resilience (Protection)
        "resilience": {
            "circuit_breakers": resilience.get("circuit_breakers", {}),
            "providers": resilience.get("providers", {}),
            "degradation": resilience.get("degradation", {}),
            "scaling": resilience.get("scaling", {})
        },
        
        # Resources
        "resources": resilience.get("resources", {}),
        
        # AI Brain Status
        "ai_brain": dashboard.get("ai_brain", {}),
        
        # API Needs
        "api_needs": dashboard.get("key_pool", {}),
        
        # Recent Incidents
        "incidents": dashboard.get("recent_incidents", []),
        
        # Notifications
        "notifications": _system_intelligence["notifications"][-20:]
    }

@app.get("/api/commons")
async def get_commons_data():
    """
    Get Commons Ministry data - Trust Index, Contributions, Needs Allocation.
    Aggregates data from the Commons Stack services.
    """
    trust_index = {}
    contributions = {}
    needs = {}
    budget = {}
    policy = {}
    
    TRUST_INDEX_URL = "http://127.0.0.1:8560"
    CONTRIBUTION_URL = "http://127.0.0.1:8570"
    NEEDS_URL = "http://127.0.0.1:8565"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch Trust Index
            try:
                ti_resp = await client.get(f"{TRUST_INDEX_URL}/api/trust-index")
                if ti_resp.status_code == 200:
                    trust_index = ti_resp.json()
            except Exception as e:
                print(f"Trust Index fetch error: {e}")
            
            # Fetch Policy
            try:
                policy_resp = await client.get(f"{TRUST_INDEX_URL}/api/trust-index/policy")
                if policy_resp.status_code == 200:
                    policy = policy_resp.json()
            except Exception as e:
                print(f"Policy fetch error: {e}")
            
            # Fetch Contributions
            try:
                contrib_resp = await client.get(f"{CONTRIBUTION_URL}/api/contributions/aggregate")
                if contrib_resp.status_code == 200:
                    contributions = contrib_resp.json()
            except Exception as e:
                print(f"Contributions fetch error: {e}")
            
            # Fetch Needs Committed
            try:
                needs_resp = await client.get(f"{NEEDS_URL}/api/needs/committed")
                if needs_resp.status_code == 200:
                    needs = needs_resp.json()
            except Exception as e:
                print(f"Needs fetch error: {e}")
            
            # Fetch Budget
            try:
                budget_resp = await client.get(f"{NEEDS_URL}/api/needs/budget")
                if budget_resp.status_code == 200:
                    budget = budget_resp.json()
            except Exception as e:
                print(f"Budget fetch error: {e}")
    
    except Exception as e:
        print(f"Commons data fetch error: {e}")
    
    return {
        "trust_index": trust_index,
        "contributions": contributions,
        "needs": needs,
        "budget": budget,
        "policy": policy,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/notification")
async def receive_notification(data: dict):
    """Receive notifications from the nervous system."""
    global _system_intelligence
    
    notification = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().isoformat(),
        "event_type": data.get("event_type", "unknown"),
        "data": data.get("data", {}),
        "read": False
    }
    
    _system_intelligence["notifications"].append(notification)
    # Keep last 100 notifications
    _system_intelligence["notifications"] = _system_intelligence["notifications"][-100:]
    
    # Broadcast to WebSocket clients
    await manager.broadcast(json.dumps({
        "type": "notification",
        "data": notification
    }))
    
    print(f"[NOTIFICATION] {notification['event_type']}: {notification['data']}")
    return {"status": "received", "id": notification["id"]}

@app.get("/api/notifications")
async def get_notifications(unread_only: bool = False):
    """Get all notifications."""
    notifications = _system_intelligence["notifications"]
    if unread_only:
        notifications = [n for n in notifications if not n.get("read")]
    return {"notifications": notifications, "count": len(notifications)}

@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    for n in _system_intelligence["notifications"]:
        if n.get("id") == notification_id:
            n["read"] = True
            return {"status": "marked_read"}
    return {"status": "not_found"}

@app.get("/api/traits")
async def get_system_traits():
    """Get all system traits/capabilities."""
    return {
        "traits": _system_intelligence["traits"],
        "description": {
            "self_aware": "Continuously scans and understands all services",
            "self_healing": "Automatically restarts crashed services",
            "predictive": "Anticipates problems before they occur",
            "safe_scaling": "Scales with safeguards and rollback",
            "graceful_degradation": "Maintains core function under stress",
            "provider_failover": "Switches to backup providers automatically",
            "circuit_breakers": "Prevents cascade failures",
            "proactive_alerts": "Sends alerts before issues become critical"
        }
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SPARKET ENGINE - Inspired Marketing Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

SPARKET_ENGINE_URL = os.getenv("SPARKET_ENGINE_URL", "http://localhost:8750")

# Global state for SPARKET data (updated by the engine)
_sparket_data = {
    "field": {
        "state": "nascent",
        "coherence": 50,
        "dominant_energy": "quiet",
        "emerging_themes": []
    },
    "impact": {
        "lives_touched": 0,
        "transformations": 0,
        "ripple_effects": 0
    },
    "ripple": {
        "multiplication_ratio": 0.0,
        "total_nodes": 0,
        "multipliers": 0
    },
    "tests": [],
    "transmissions": [],
    "last_update": None
}

@app.get("/api/sparket")
async def get_sparket_data():
    """
    Get SPARKET engine dashboard data.
    Shows field coherence, impact metrics, ripple network, ad tests, and transmissions.
    """
    # Try to fetch fresh data from SPARKET engine
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SPARKET_ENGINE_URL}/api/v1/dashboard")
            if response.status_code == 200:
                data = response.json()
                # Update local cache
                _sparket_data.update(data)
                _sparket_data["last_update"] = datetime.now().isoformat()
    except Exception as e:
        # Return cached data if engine unavailable
        pass
    
    return _sparket_data

@app.post("/api/sparket-update")
async def receive_sparket_update(data: dict):
    """
    Receive updates from the SPARKET engine.
    This enables real-time dashboard updates.
    """
    global _sparket_data
    
    if "field" in data:
        _sparket_data["field"] = data["field"]
    if "impact" in data:
        _sparket_data["impact"] = data["impact"]
    if "ripple" in data:
        _sparket_data["ripple"] = data["ripple"]
    if "tests" in data:
        _sparket_data["tests"] = data["tests"]
    if "transmissions" in data:
        _sparket_data["transmissions"] = data["transmissions"]
    
    _sparket_data["last_update"] = datetime.now().isoformat()
    
    # Broadcast to connected WebSocket clients
    await manager.broadcast({
        "type": "sparket_update",
        "data": _sparket_data
    })
    
    return {"status": "received", "timestamp": _sparket_data["last_update"]}

# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/stats")
async def get_stats():
    intents = len(list(INTENTS_DIR.glob("*.json"))) if INTENTS_DIR.exists() else 0
    claims = len(list(CLAIMS_DIR.glob("*.claim"))) if CLAIMS_DIR.exists() else 0
    return {"intents": intents, "claims": claims}

@app.get("/api/graph")
async def api_graph():
    return get_graph_data()

@app.get("/api/chat")
async def api_chat():
    return get_messages()

@app.post("/api/chat")
async def post_chat(msg: dict = Body(...)):
    content = msg.get("content")
    sender = msg.get("sender", "ARCHITECT")
    if not content: return {"error": "empty"}
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}-{uuid.uuid4().hex[:4]}.json"
    data = {
        "sender": sender,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "id": uuid.uuid4().hex
    }
    with open(MESSAGES_DIR / filename, 'w') as f:
        json.dump(data, f, indent=2)
    await manager.broadcast({"type": "chat_new", "data": data})
    return data

@app.get("/api/board")
async def api_board():
    return get_kanban_data()

@app.post("/api/mission")
async def create_mission(mission: dict = Body(...)):
    name = mission.get("name")
    desc = mission.get("desc")
    if not name: return {"error": "Name required"}
    filename = f"{name}.json"
    data = {
        "architect_intent": desc,
        "droplet_name": name,
        "approval_mode": "auto",
        "auto_deploy": True,
        "generated_by": "God Mode GUI",
        "score": 50,
        "created_at": datetime.now().isoformat()
    }
    with open(INTENTS_DIR / filename, 'w') as f:
        json.dump(data, f, indent=2)
    await manager.broadcast({"type": "board_update", "data": get_kanban_data()})
    return {"status": "created"}

@app.get("/api/inbox")
async def get_inbox():
    if not INBOX_FILE.exists(): return []
    try:
        with open(INBOX_FILE, 'r') as f:
            data = json.load(f)
            return data.get("items", [])
    except: return []

@app.get("/api/treasury")
async def api_treasury():
    return get_treasury_data()

@app.get("/api/overview")
async def api_overview():
    """
    Minimal, high-signal overview used by the simplified God Mode UI.
    Returns 3 core cards: Money, Health, DoNow (+ optional Experimental section).
    """
    treasury = get_treasury_data()

    # Health (primary auto-healer, if reachable from this host/container)
    auto_healer = await _safe_get_json(f"{AUTO_HEALER_URL}/api/status", timeout_s=3.0)

    # Money (primary trading)
    # WhaleTrack has evolved; support both legacy /api/stats and Magnet's UDC endpoints.
    trading_stats = (
        await _safe_get_json(f"{TRADING_URL}/api/stats", timeout_s=3.0)
        or await _safe_get_json(f"{TRADING_URL}/api/strategy/info", timeout_s=3.0)
        or await _safe_get_json(f"{TRADING_URL}/health", timeout_s=3.0)
    )

    # Do Now (top pending task, if any)
    top_task = None
    try:
        tasks = await generate_tasks()
        pending = [t for t in tasks if t.get("status") == "pending"]
        pending.sort(key=lambda t: t.get("priority", 0), reverse=True)
        top_task = pending[0] if pending else None
    except Exception:
        pass

    # Experimental: Consciousness (secondary)
    consciousness_health = await _safe_get_json(f"{CONSCIOUSNESS_VERIFIER_URL}/health", timeout_s=2.0)

    return {
        "timestamp": datetime.now().isoformat(),
        "money": {
            "treasury": treasury,
            "trading_stats": trading_stats,
        },
        "health": {
            "auto_healer": auto_healer,
        },
        "do_now": {
            "top_task": top_task,
        },
        "experimental": {
            "consciousness_verifier": consciousness_health,
        },
    }


@app.get("/api/connections")
async def api_connections():
    """
    Explicit upstream connectivity checks (SSOT vs configured runtime).
    This is separate from UI/service scans so endpoint miswires are obvious.
    """
    ssot = _load_ssot(SSOT_FILE)

    def _source(env_var: str, ssot_val: str | None) -> str:
        if os.getenv(env_var):
            return "env"
        if ssot_val:
            return "ssot"
        return "default"

    ssot_ai = _ssot_routing_url(ssot, "ai_inference")
    ssot_data = _ssot_routing_url(ssot, "data_service")
    ssot_nerve = _ssot_routing_url(ssot, "nerve_center")
    ssot_trading = _ssot_routing_url(ssot, "trading")
    cv_host, cv_port = _find_service_endpoint(ssot, "fpai-consciousness_verifier")
    ssot_conscious = (f"http://{cv_host}:{cv_port}" if (cv_host and cv_port) else None)

    checks = [
        {
            "id": "ai_brain",
            "name": "AI Brain",
            "configured_base_url": AI_BRAIN_URL,
            "ssot_url": ssot_ai,
            "source": _source("AI_BRAIN_URL", ssot_ai),
            "probe_path": "/health",
        },
        {
            "id": "data_service",
            "name": "Data Service",
            "configured_base_url": DATA_SERVICE_URL,
            "ssot_url": ssot_data,
            "source": _source("DATA_SERVICE_URL", ssot_data),
            "probe_path": "/health",
        },
        {
            "id": "nerve_center",
            "name": "Nerve Center",
            "configured_base_url": NERVE_CENTER_URL,
            "ssot_url": ssot_nerve,
            "source": _source("NERVE_CENTER_URL", ssot_nerve),
            "probe_path": "/health",
        },
        {
            "id": "trading",
            "name": "Trading (WhaleTrack Magnet)",
            "configured_base_url": TRADING_URL,
            "ssot_url": ssot_trading,
            "source": _source("TRADING_URL", ssot_trading),
            "probe_path": "/health",
        },
        {
            "id": "consciousness_verifier",
            "name": "Consciousness Verifier",
            "configured_base_url": CONSCIOUSNESS_VERIFIER_URL,
            "ssot_url": ssot_conscious,
            "source": _source("CONSCIOUSNESS_VERIFIER_URL", ssot_conscious),
            "probe_path": "/health",
        },
    ]

    async def _probe(client: httpx.AsyncClient, c: dict) -> dict:
        base = (c.get("configured_base_url") or "").rstrip("/")
        path = c.get("probe_path") or "/health"
        url = f"{base}{path}" if base else None
        start = time.perf_counter()
        if not url:
            return {**c, "ok": False, "error": "missing_configured_url", "latency_ms": None, "status_code": None, "url": None}
        try:
            resp = await client.get(url)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            ok = resp.status_code == 200
            sample = None
            try:
                sample = resp.json()
            except Exception:
                sample = {"raw": resp.text[:200]}
            suggested_fix = None
            if c.get("ssot_url") and (c.get("configured_base_url") != c.get("ssot_url")) and c.get("source") != "env":
                suggested_fix = "Configured URL differs from SSOT; consider removing overrides or reloading configuration."
            return {
                **c,
                "url": url,
                "ok": ok,
                "status_code": resp.status_code,
                "latency_ms": latency_ms,
                "sample": sample,
                "suggested_fix": suggested_fix,
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {**c, "url": url, "ok": False, "status_code": None, "latency_ms": latency_ms, "error": str(e)}

    async with httpx.AsyncClient(timeout=5.0) as client:
        results = await asyncio.gather(*[_probe(client, c) for c in checks])

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ssot_loaded": bool(ssot),
        "connections": results,
    }


# ============================================================================
# DATA SYSTEM (visual + operations)
# ============================================================================


@app.get("/api/data-system/status")
async def data_system_status():
    """
    Proxy view for the complete Data System state.
    This keeps the frontend simple and avoids cross-origin issues.
    """
    nerve_health = await _safe_get_json(f"{NERVE_CENTER_URL}/health", timeout_s=3.0)
    pipeline = await _safe_get_json(f"{NERVE_CENTER_URL}/api/intelligence/pipeline/health", timeout_s=5.0)
    digest_latest = await _safe_get_json(f"{NERVE_CENTER_URL}/api/intelligence/digest/latest", timeout_s=5.0)
    intents_recent = await _safe_get_json(f"{NERVE_CENTER_URL}/api/intelligence/intents/recent?limit=25", timeout_s=5.0)
    outcomes_recent = await _safe_get_json(f"{NERVE_CENTER_URL}/api/outcomes/recent?limit=25&hours=168", timeout_s=5.0)
    outcomes_stats = await _safe_get_json(f"{NERVE_CENTER_URL}/api/outcomes/stats?hours=168", timeout_s=5.0)

    data_health = await _safe_get_json(f"{DATA_SERVICE_URL}/health", timeout_s=3.0)
    strategic_health = await _safe_get_json(f"{STRATEGIC_INTEL_URL}/health", timeout_s=3.0)
    ai_brain_health = await _safe_get_json(f"{AI_BRAIN_URL}/health", timeout_s=3.0)

    return {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "nerve_center_url": NERVE_CENTER_URL,
            "data_service_url": DATA_SERVICE_URL,
            "strategic_intel_url": STRATEGIC_INTEL_URL,
            "ai_brain_url": AI_BRAIN_URL,
            "doc_path": "docs/coordination/DATA_SYSTEM_MAP.md",
        },
        "services": {
            "nerve_center": nerve_health,
            "data_service": data_health,
            "strategic_intelligence": strategic_health,
            "ai_brain": ai_brain_health,
        },
        "pipeline": pipeline,
        "digest_latest": digest_latest,
        "intents_recent": intents_recent,
        "outcomes_recent": outcomes_recent,
        "outcomes_stats": outcomes_stats,
    }


@app.post("/api/data-system/digest/run")
async def data_system_run_digest(payload: dict = Body(...)):
    """
    Proxy: run digest on Nerve Center.
    """
    return await _safe_post_json(f"{NERVE_CENTER_URL}/api/intelligence/digest/run", payload, timeout_s=30.0)


@app.post("/api/data-system/outcomes/record")
async def data_system_record_outcome(payload: dict = Body(...)):
    """
    Proxy: record outcome on Nerve Center.
    """
    return await _safe_post_json(f"{NERVE_CENTER_URL}/api/outcomes/record", payload, timeout_s=10.0)

# --- MISSION CONTROL INTEGRATION ---

SERVICES_DIR = Path(os.getenv("SERVICES_DIR", "/services"))
MISSION_TOKENS_FILE = COORDINATION_DIR / "mission_tokens.json"
MISSION_TASKS_FILE = COORDINATION_DIR / "mission_tasks.json"
TRUSTED_HUMANS_FILE = COORDINATION_DIR / "trusted_humans.json"
TEAM_ACTIVITY_FILE = COORDINATION_DIR / "team_activity.json"

def load_json_file(path, default=None):
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else []

def save_json_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

async def scan_api_needs():
    """Scan all services for NEEDS.json files AND query API Portal"""
    needs = []
    
    # 1. File System Scan
    if SERVICES_DIR.exists():
        for service_dir in SERVICES_DIR.iterdir():
            if not service_dir.is_dir():
                continue
            needs_file = service_dir / "NEEDS.json"
            if needs_file.exists():
                try:
                    with open(needs_file) as f:
                        data = json.load(f)
                        for need in data.get('needs', []):
                            need['service'] = data.get('service', service_dir.name)
                            needs.append(need)
                except:
                    pass
    
    # 2. API Portal Fetch
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{API_PORTAL_URL}/needs")
            if resp.status_code == 200:
                portal_needs = resp.json()
                for pn in portal_needs:
                    # Map Portal format to God Mode format
                    needs.append({
                        "id": f"portal_{pn.get('id')}",
                        "service": pn.get("requesting_service"),
                        "capability": pn.get("purpose"),
                        "priority": pn.get("priority", 5),
                        "status": "missing" if pn.get("status") == "needed" else pn.get("status"),
                        "recommended_api": {
                            "name": pn.get("api_name"),
                            "provider": pn.get("api_provider"),
                            "signup_url": pn.get("signup_url")
                        },
                        "instructions": [pn.get("notes")] if pn.get("notes") else []
                    })
    except Exception:
        pass
        
    return needs

def calculate_priority(need):
    score = 0
    blocking = need.get('blocking', [])
    score += len(blocking) * 100
    score += (10 - need.get('priority', 5)) * 50
    # Safely get nested dicts
    rec_api = need.get('recommended_api') or {}
    complexity = rec_api.get('signup_complexity', 'moderate')
    complexity_map = {'simple': 50, 'moderate': 30, 'complex': 10}
    score += complexity_map.get(complexity, 30)
    if not rec_api.get('requires_credit_card', False):
        score += 25
    return score

async def generate_tasks():
    """Generate tasks from API needs"""
    needs = await scan_api_needs()
    tasks = load_json_file(MISSION_TASKS_FILE, [])
    existing_ids = {t['id'] for t in tasks}
    
    for need in needs:
        if need.get('status') != 'missing':
            continue
        task_id = f"{need.get('service', 'unknown')}_{need['id']}"
        if task_id in existing_ids:
            continue
        api = need.get('recommended_api') or {}
        task = {
            "id": task_id,
            "service": need.get('service'),
            "capability": need.get('capability'),
            "api_name": api.get('name', 'Unknown API'),
            "priority": calculate_priority(need),
            "status": "pending",
            "instructions": need.get('instructions', []),
            "credential_fields": need.get('credential_fields', []),
            "created_at": datetime.now().isoformat(),
            "blocking_services": need.get('blocking', []),
            "signup_url": api.get('signup_url'),
            "signup_complexity": api.get('signup_complexity', 'moderate'),
            "free_tier": api.get('free_tier'),
            "estimated_time": api.get('estimated_signup_time', '30 min')
        }
        tasks.append(task)
    
    tasks.sort(key=lambda t: t.get('priority', 0), reverse=True)
    save_json_file(MISSION_TASKS_FILE, tasks)
    return tasks

@app.get("/api/mission-control/tokens")
async def get_tokens():
    return load_json_file(MISSION_TOKENS_FILE, [])

@app.post("/api/mission-control/tokens")
async def create_token(token_data: dict = Body(...)):
    tokens = load_json_file(MISSION_TOKENS_FILE, [])
    from datetime import timedelta
    
    expires_hours = token_data.get('expires_hours')
    expires_at = None
    if expires_hours:
        expires_at = (datetime.now() + timedelta(hours=int(expires_hours))).isoformat()
    
    new_token = {
        "id": uuid.uuid4().hex,
        "type": token_data.get('type', 'assistant'),
        "name": token_data.get('name', 'Unnamed'),
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "active": True
    }
    tokens.append(new_token)
    save_json_file(MISSION_TOKENS_FILE, tokens)
    await manager.broadcast({"type": "tokens_update", "data": tokens})
    return new_token

@app.delete("/api/mission-control/tokens/{token_id}")
async def revoke_token(token_id: str):
    tokens = load_json_file(MISSION_TOKENS_FILE, [])
    for t in tokens:
        if t['id'] == token_id:
            t['active'] = False
    save_json_file(MISSION_TOKENS_FILE, tokens)
    await manager.broadcast({"type": "tokens_update", "data": tokens})
    return {"status": "revoked"}

@app.get("/api/mission-control/tasks")
async def get_tasks():
    return await generate_tasks()

@app.get("/api/mission-control/needs")
async def get_needs():
    needs = await scan_api_needs()
    return {
        "needs": sorted(needs, key=lambda n: calculate_priority(n), reverse=True),
        "total": len(needs),
        "missing": len([n for n in needs if n.get('status') == 'missing'])
    }

@app.post("/api/mission-control/tasks/{task_id}/complete")
async def complete_task(task_id: str, creds: dict = Body(...)):
    tasks = load_json_file(MISSION_TASKS_FILE, [])
    for t in tasks:
        if t['id'] == task_id:
            t['status'] = 'completed'
            t['completed_at'] = datetime.now().isoformat()
            t['completed_by'] = creds.get('completed_by', 'unknown')
    save_json_file(MISSION_TASKS_FILE, tasks)
    await manager.broadcast({"type": "tasks_update", "data": tasks})
    return {"status": "completed"}

@app.get("/api/mission-control/stats")
async def mission_stats():
    tasks = load_json_file(MISSION_TASKS_FILE, [])
    tokens = load_json_file(MISSION_TOKENS_FILE, [])
    needs = await scan_api_needs()
    
    blocked_services = set()
    for task in tasks:
        if task.get('status') == 'pending':
            blocked_services.update(task.get('blocking_services', []))
    
    return {
        "active_tokens": len([t for t in tokens if t.get('active')]),
        "pending_tasks": len([t for t in tasks if t.get('status') == 'pending']),
        "completed_tasks": len([t for t in tasks if t.get('status') == 'completed']),
        "blocked_services": len(blocked_services),
        "total_api_needs": len(needs)
    }

# --- TEAM HUB (Trusted Humans Management) ---

def get_trusted_humans():
    return load_json_file(TRUSTED_HUMANS_FILE, [])

def save_trusted_humans(humans):
    save_json_file(TRUSTED_HUMANS_FILE, humans)

def get_team_activity():
    return load_json_file(TEAM_ACTIVITY_FILE, [])

def log_team_activity(action: str, human_id: str, details: dict = None):
    activity = get_team_activity()
    activity.append({
        "id": uuid.uuid4().hex,
        "action": action,
        "human_id": human_id,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    })
    # Keep last 500 activities
    activity = activity[-500:]
    save_json_file(TEAM_ACTIVITY_FILE, activity)

def calculate_trust_score(human: dict) -> int:
    """Calculate trust level 1-5 based on performance"""
    tasks_completed = human.get('tasks_completed', 0)
    tasks_failed = human.get('tasks_failed', 0)
    total = tasks_completed + tasks_failed
    
    if total == 0:
        return 1  # New human
    
    success_rate = tasks_completed / total if total > 0 else 0
    
    # Trust levels based on volume + success rate
    if tasks_completed >= 20 and success_rate >= 0.95:
        return 5  # Trusted
    elif tasks_completed >= 10 and success_rate >= 0.90:
        return 4  # Proven
    elif tasks_completed >= 5 and success_rate >= 0.80:
        return 3  # Reliable
    elif tasks_completed >= 2 and success_rate >= 0.70:
        return 2  # Learning
    else:
        return 1  # New

@app.get("/api/team/humans")
async def get_humans():
    humans = get_trusted_humans()
    # Calculate current trust scores
    for h in humans:
        h['trust_level'] = calculate_trust_score(h)
    return humans

@app.post("/api/team/humans")
async def add_human(human_data: dict = Body(...)):
    humans = get_trusted_humans()
    
    new_human = {
        "id": uuid.uuid4().hex,
        "name": human_data.get('name', 'Unnamed'),
        "email": human_data.get('email', ''),
        "specialty": human_data.get('specialty', 'general'),  # api, dev, design, etc.
        "contact_channel": human_data.get('contact_channel', 'email'),  # email, slack, fiverr, etc.
        "contact_info": human_data.get('contact_info', ''),
        "notes": human_data.get('notes', ''),
        "tasks_completed": 0,
        "tasks_failed": 0,
        "credits_earned": 0,
        "created_at": datetime.now().isoformat(),
        "last_active": None,
        "status": "active"
    }
    
    humans.append(new_human)
    save_trusted_humans(humans)
    log_team_activity("human_added", new_human['id'], {"name": new_human['name']})
    
    await manager.broadcast({"type": "team_update", "data": humans})
    return new_human

@app.put("/api/team/humans/{human_id}")
async def update_human(human_id: str, updates: dict = Body(...)):
    humans = get_trusted_humans()
    
    for h in humans:
        if h['id'] == human_id:
            # Only update allowed fields
            allowed = ['name', 'email', 'specialty', 'contact_channel', 'contact_info', 'notes', 'status']
            for key in allowed:
                if key in updates:
                    h[key] = updates[key]
            save_trusted_humans(humans)
            log_team_activity("human_updated", human_id, updates)
            await manager.broadcast({"type": "team_update", "data": humans})
            return h
    
    return {"error": "Human not found"}

@app.delete("/api/team/humans/{human_id}")
async def remove_human(human_id: str):
    humans = get_trusted_humans()
    humans = [h for h in humans if h['id'] != human_id]
    save_trusted_humans(humans)
    log_team_activity("human_removed", human_id)
    await manager.broadcast({"type": "team_update", "data": humans})
    return {"status": "removed"}

@app.post("/api/team/humans/{human_id}/task-complete")
async def record_task_completion(human_id: str, task_data: dict = Body(...)):
    """Record a completed task and award credits"""
    humans = get_trusted_humans()
    
    for h in humans:
        if h['id'] == human_id:
            h['tasks_completed'] = h.get('tasks_completed', 0) + 1
            h['last_active'] = datetime.now().isoformat()
            
            # Award credits based on task type
            credits = task_data.get('credits', 50)  # Default 50 credits per task
            h['credits_earned'] = h.get('credits_earned', 0) + credits
            
            save_trusted_humans(humans)
            log_team_activity("task_completed", human_id, {
                "task": task_data.get('task_name'),
                "credits": credits
            })
            await manager.broadcast({"type": "team_update", "data": humans})
            return {"status": "recorded", "new_credits": h['credits_earned'], "trust_level": calculate_trust_score(h)}
    
    return {"error": "Human not found"}

@app.post("/api/team/humans/{human_id}/task-failed")
async def record_task_failure(human_id: str, task_data: dict = Body(...)):
    """Record a failed task"""
    humans = get_trusted_humans()
    
    for h in humans:
        if h['id'] == human_id:
            h['tasks_failed'] = h.get('tasks_failed', 0) + 1
            h['last_active'] = datetime.now().isoformat()
            
            save_trusted_humans(humans)
            log_team_activity("task_failed", human_id, {
                "task": task_data.get('task_name'),
                "reason": task_data.get('reason')
            })
            await manager.broadcast({"type": "team_update", "data": humans})
            return {"status": "recorded", "trust_level": calculate_trust_score(h)}
    
    return {"error": "Human not found"}

@app.get("/api/team/stats")
async def team_stats():
    humans = get_trusted_humans()
    tokens = load_json_file(MISSION_TOKENS_FILE, [])
    activity = get_team_activity()
    
    active_humans = [h for h in humans if h.get('status') == 'active']
    active_tokens = [t for t in tokens if t.get('active')]
    
    # Get humans with active tokens
    working_now = 0
    for token in active_tokens:
        # Check if token is linked to a human
        for h in humans:
            if token.get('human_id') == h['id']:
                working_now += 1
                break
    
    # Recent activity (last 24h)
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    recent_activity = [a for a in activity if a.get('timestamp', '') > cutoff]
    
    # Calculate total credits earned
    total_credits = sum(h.get('credits_earned', 0) for h in humans)
    
    return {
        "total_humans": len(humans),
        "active_humans": len(active_humans),
        "working_now": working_now,
        "active_tokens": len(active_tokens),
        "recent_activity_count": len(recent_activity),
        "total_credits_earned": total_credits,
        "top_performers": sorted(humans, key=lambda h: h.get('tasks_completed', 0), reverse=True)[:3]
    }

@app.get("/api/team/activity")
async def get_activity(limit: int = 50):
    activity = get_team_activity()
    return activity[-limit:]

@app.post("/api/team/assign-token")
async def assign_token_to_human(data: dict = Body(...)):
    """Create a token and link it to a specific human"""
    human_id = data.get('human_id')
    token_type = data.get('type', 'assistant')
    expires_hours = data.get('expires_hours', 24)
    
    humans = get_trusted_humans()
    human = next((h for h in humans if h['id'] == human_id), None)
    
    if not human:
        return {"error": "Human not found"}
    
    # Create token linked to human
    tokens = load_json_file(MISSION_TOKENS_FILE, [])
    from datetime import timedelta
    
    expires_at = None
    if expires_hours:
        expires_at = (datetime.now() + timedelta(hours=int(expires_hours))).isoformat()
    
    new_token = {
        "id": uuid.uuid4().hex,
        "type": token_type,
        "name": f"{human['name']} - {token_type.title()}",
        "human_id": human_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "active": True
    }
    
    tokens.append(new_token)
    save_json_file(MISSION_TOKENS_FILE, tokens)
    
    log_team_activity("token_assigned", human_id, {
        "token_id": new_token['id'],
        "type": token_type,
        "expires_hours": expires_hours
    })
    
    await manager.broadcast({"type": "tokens_update", "data": tokens})
    
    # Generate portal URL
    portal_type = "assistant" if token_type == "assistant" else "developer"
    portal_url = f"/portal/{portal_type}?token={new_token['id']}"
    
    return {
        "token": new_token,
        "portal_url": portal_url,
        "human": human
    }

@app.get("/api/team/recommendations")
async def get_ai_recommendations():
    """AI-powered recommendations for task assignments"""
    humans = get_trusted_humans()
    tasks = load_json_file(MISSION_TASKS_FILE, [])
    
    pending_tasks = [t for t in tasks if t.get('status') == 'pending']
    active_humans = [h for h in humans if h.get('status') == 'active']
    
    recommendations = []
    
    for task in pending_tasks[:5]:  # Top 5 priority tasks
        # Find best human for this task
        task_type = task.get('capability', 'general')
        
        # Score each human for this task
        scored_humans = []
        for h in active_humans:
            score = 0
            
            # Specialty match
            if h.get('specialty') == 'api' and 'api' in task_type.lower():
                score += 50
            elif h.get('specialty') == 'dev' and 'dev' in task_type.lower():
                score += 50
            elif h.get('specialty') == 'general':
                score += 20
            
            # Trust level
            trust = calculate_trust_score(h)
            score += trust * 10
            
            # Recent activity (active humans preferred)
            if h.get('last_active'):
                try:
                    last = datetime.fromisoformat(h['last_active'])
                    days_ago = (datetime.now() - last).days
                    if days_ago < 7:
                        score += 20
                    elif days_ago < 30:
                        score += 10
                except:
                    pass
            
            scored_humans.append((h, score))
        
        scored_humans.sort(key=lambda x: x[1], reverse=True)
        
        if scored_humans:
            best_human, confidence = scored_humans[0]
            recommendations.append({
                "task": task,
                "recommended_human": best_human,
                "confidence": min(confidence, 100),
                "reason": f"Best match based on specialty ({best_human.get('specialty')}) and trust level ({calculate_trust_score(best_human)})"
            })
    
    return recommendations

# --- WEBSOCKET ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- BACKGROUND TASKS ---

async def watch_system_state():
    last_board_hash = 0
    
    while True:
        try:
            # 1. Stats
            stats = await get_stats()
            await manager.broadcast({"type": "stats_update", "data": stats})
            
            # 2. Board
            board = get_kanban_data()
            current_hash = len(board["intent"]) + len(board["building"])
            if current_hash != last_board_hash:
                 await manager.broadcast({"type": "board_update", "data": board})
                 last_board_hash = current_hash
            
            # 3. Treasury (Check periodically)
            # In real usage, check mtime. For now, send every 10s
            if datetime.now().second % 10 == 0:
                treasury = get_treasury_data()
                await manager.broadcast({"type": "treasury_update", "data": treasury})

        except Exception as e:
            print(f"Watcher Error: {e}")
        
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup():
    asyncio.create_task(watch_system_state())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
