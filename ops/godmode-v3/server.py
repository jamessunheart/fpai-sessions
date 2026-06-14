"""
⚡ GOD MODE v3.0 - OMNISCIENT SYSTEM COMMAND CENTER
The all-seeing eye of Full Potential AI

Features:
- Real-time WebSocket updates
- Service detail modals with logs
- Auto-healing capabilities
- Alert system
- Performance trends
- One-click actions

Performance controls (env vars):
- GODMODE_SERVICE_TIMEOUT=2.5            # per-service probe timeout (seconds)
- GODMODE_OVERVIEW_TTL=2.0              # overview response cache (seconds)
- GODMODE_TTL_SERVICES=15               # sub-scan TTLs (seconds)
- GODMODE_TTL_SYSTEM=10
- GODMODE_TTL_DOCKER=30
- GODMODE_TTL_ERRORS=30
- GODMODE_TTL_SESSIONS=60
- GODMODE_TTL_COORDINATION=15

Boot behavior:
- / renders a fast boot snapshot immediately (no blocking scans) and upgrades via WebSocket updates.
- Background scans run every 15s when clients are connected, otherwise every 60s.
"""
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import json
import asyncio
import time
import httpx
import subprocess
import shlex
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
import os

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parent

# SSOT-based routing (single source of truth) — reduces hardcoded endpoint drift.
_DEFAULT_PRIMARY_IP = "198.54.123.234"
_DEFAULT_SECONDARY_IP = "162.0.208.88"

def _load_ssot() -> Optional[dict]:
    """
    Best-effort load of docs/coordination/SSOT.json so God Mode uses the same
    routing truth as the rest of the system.
    """
    candidates: list[Path] = []
    env_path = os.getenv("SSOT_PATH") or os.getenv("SSOT_FILE")
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend([
        Path("/opt/fpai/docs/coordination/SSOT.json"),
        (Path(__file__).resolve().parents[2] / "docs/coordination/SSOT.json"),
    ])
    for p in candidates:
        try:
            if p.exists():
                return json.loads(p.read_text())
        except Exception:
            continue
    return None

def _ssot_routing_url(ssot: Optional[dict], key: str) -> Optional[str]:
    try:
        if not ssot:
            return None
        url = ssot.get("fleet", {}).get("routing", {}).get(key)
        return str(url) if url else None
    except Exception:
        return None

def _parse_host_port(url: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    if not url:
        return (None, None)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return (parsed.hostname, parsed.port)
    except Exception:
        return (None, None)

def _find_service_endpoint(ssot: Optional[dict], service_prefix: str) -> tuple[Optional[str], Optional[int]]:
    """
    Find a service endpoint by scanning SSOT node service strings like:
      - 'ai-brain:8101'
      - 'ollama:11434'
      - 'whaletrack-magnet:8600'
      - 'fpai-consciousness_verifier:8140'
    Returns (node_ip, port) if found.
    """
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

_SSOT = _load_ssot()

# Prefer env overrides, else SSOT-derived hosts, else defaults.
_primary_from_trading = _parse_host_port(_ssot_routing_url(_SSOT, "trading"))[0]
_secondary_from_ai = _parse_host_port(_ssot_routing_url(_SSOT, "ai_inference"))[0]
PRIMARY_IP = os.getenv("PRIMARY_IP") or _primary_from_trading or _DEFAULT_PRIMARY_IP
SECONDARY_IP = os.getenv("SECONDARY_IP") or _secondary_from_ai or _DEFAULT_SECONDARY_IP

PRIMARY_TAILSCALE_IP = os.getenv("PRIMARY_TAILSCALE_IP", "100.122.184.66")
SECONDARY_TAILSCALE_IP = os.getenv("SECONDARY_TAILSCALE_IP", "100.127.118.106")
SERVER_IP = PRIMARY_IP  # Backwards-compatible alias (scanner defaults to primary)
VERSION = "3.0.0"

# SSOT-derived service ports (fallbacks match docs/coordination/SERVICE_REGISTRY.md)
_conscious_host, _conscious_port = _find_service_endpoint(_SSOT, "fpai-consciousness_verifier")
CONSCIOUSNESS_VERIFIER_HOST = _conscious_host or SECONDARY_IP
CONSCIOUSNESS_VERIFIER_PORT = _conscious_port or 8140

_magnet_host, _magnet_port = _find_service_endpoint(_SSOT, "whaletrack-magnet")
WHALETRACK_MAGNET_HOST = _magnet_host or PRIMARY_IP
WHALETRACK_MAGNET_PORT = _magnet_port or 8600

# Alignment ritual logging (inner loop state)
def _resolve_state_dir() -> Path:
    env_dir = os.getenv("FP_STATE_DIR") or os.getenv("STATE_DIR")
    if env_dir:
        return Path(env_dir)
    candidates = [
        Path("/opt/fpai/core/STATE"),
        (Path(__file__).resolve().parents[2] / "core/STATE"),
    ]
    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return candidates[-1]

STATE_DIR = _resolve_state_dir()
RITUAL_LOG_FILE = STATE_DIR / "GOD_CONNECTION_LOG.jsonl"

# =============================================================================
# LEGACY "COUNCIL" GOD MODE INTEGRATION (read-only)
# =============================================================================
LEGACY_GODMODE_DIR = Path(os.getenv("LEGACY_GODMODE_DIR", "/opt/fpai/god-mode"))

# Prefer the shared coordination directory (used by active agents) if present,
# then fall back to the legacy god-mode tree.
_legacy_coord_env = os.getenv("LEGACY_COORDINATION_DIR")
if _legacy_coord_env:
    LEGACY_COORDINATION_DIR = Path(_legacy_coord_env)
else:
    _coord_candidates = [
        Path("/opt/fpai/docs/coordination"),
        LEGACY_GODMODE_DIR / "docs/coordination",
    ]
    LEGACY_COORDINATION_DIR = next((p for p in _coord_candidates if p.exists()), _coord_candidates[0])

LEGACY_INTENTS_DIR = LEGACY_COORDINATION_DIR / "intents"
LEGACY_CLAIMS_DIR = LEGACY_COORDINATION_DIR / "claims"
LEGACY_HEARTBEATS_DIR = LEGACY_COORDINATION_DIR / "heartbeats"
LEGACY_BROADCAST_DIR = LEGACY_COORDINATION_DIR / "messages/broadcast"


# ============================================================
# 🔐 ADMIN AUTHENTICATION - Protect God Mode
# ============================================================
import hashlib
import secrets
from functools import wraps

# Admin credentials (hash the password for security)
ADMIN_USERNAME = os.getenv("GODMODE_ADMIN_USERNAME", "admin")

# Prefer a pre-hashed secret; fall back to hashing a provided plaintext secret.
_admin_password = os.getenv("GODMODE_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
ADMIN_PASSWORD_HASH = os.getenv("GODMODE_ADMIN_PASSWORD_HASH") or os.getenv("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH and _admin_password:
    ADMIN_PASSWORD_HASH = hashlib.sha256(_admin_password.encode()).hexdigest()
ADMIN_PASSWORD_CONFIGURED = bool(ADMIN_PASSWORD_HASH)

# Dangerous admin actions are disabled by default.
ENABLE_ADMIN_EXEC = str(os.getenv("GODMODE_ENABLE_EXEC", "")).lower() in ("1", "true", "yes", "on")
ENABLE_ADMIN_RESTART_ALL = str(os.getenv("GODMODE_ENABLE_RESTART_ALL", "")).lower() in ("1", "true", "yes", "on")

AUDIT_LOG_FILE = Path(os.getenv("GODMODE_AUDIT_LOG", "/opt/fpai/logs/godmode_audit.jsonl"))

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return getattr(request.client, "host", "unknown")

def _audit(event: str, request: Request, details: Optional[dict] = None):
    rec = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "ip": _get_client_ip(request),
        "ua": request.headers.get("user-agent"),
        "details": details or {},
    }
    try:
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        # Never block God Mode on audit log I/O issues.
        pass
ADMIN_SESSIONS = {}  # token -> expiry

def generate_admin_token():
    token = secrets.token_urlsafe(32)
    ADMIN_SESSIONS[token] = time.time() + 86400  # 24 hour expiry
    return token

def verify_admin_token(token: str) -> bool:
    if not token:
        return False
    expiry = ADMIN_SESSIONS.get(token)
    if not expiry:
        return False
    if time.time() > expiry:
        del ADMIN_SESSIONS[token]
        return False
    return True

def admin_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token")
        if not verify_admin_token(token):
            return JSONResponse({"error": "Unauthorized - Admin login required"}, status_code=401)
        return await func(request, *args, **kwargs)
    return wrapper

# Live services on server
LIVE_SERVICES = {
    # PRIMARY (198.54.123.234) - Trading, Revenue, Data
    "god-mode": {
        "port": 8300,
        "name": "God Mode",
        "category": "consciousness",
        "icon": "⚡",
        "public_url": "https://fullpotential.ai/admin/god",
        "systemd": "godmode",
    },
    "auto-healer": {
        "port": 8180,
        "name": "Auto-Healer",
        "category": "infrastructure",
        "icon": "🩺",
        "public_url": None,
        "systemd": "fpai-auto-healer.service",
        "health_endpoint": "/api/status",
    },
    "genesis": {
        "port": 8150,
        "name": "Genesis",
        "category": "core",
        "icon": "🌱",
        "public_url": None,
        "systemd": "genesis.service",
    },
    "data-service": {
        "port": 8125,
        "name": "Data Service",
        "category": "core",
        "icon": "📊",
        "public_url": None,
        "systemd": "fpai-data-service.service",
    },
    "nerve-center": {
        "port": 8120,
        "name": "Nerve Center",
        "category": "core",
        "icon": "🧬",
        "public_url": None,
        "systemd": "fpai-nerve-center.service",
    },
    "team-hub": {
        "port": 8355,
        "name": "Team Hub",
        "category": "interface",
        "icon": "🤝",
        "public_url": "https://fullpotential.ai/services/collaboration",
        "systemd": "team-hub.service",
    },
    "aria": {
        "port": 8710,
        "name": "Aria",
        "category": "interface",
        "icon": "🤖",
        "public_url": None,
        "systemd": "fpai-aria.service",
        "health_endpoint": "/health",
    },
    "strategic-intel": {
        "port": 8500,
        "name": "Strategic Intel",
        "category": "intelligence",
        "icon": "🧠",
        "public_url": None,
        "systemd": "fpai-strategic-intel.service",
    },
    "whaletrack-magnet": {
        "host": WHALETRACK_MAGNET_HOST,
        "port": WHALETRACK_MAGNET_PORT,
        "name": "WhaleTrack Magnet",
        "category": "revenue",
        "icon": "🐋",
        "public_url": "https://fullpotential.ai/dashboards/whaletrack/",
        "systemd": "whaletrack-magnet.service",
        "health_endpoint": "/health",
    },
    "whaletrack-live": {
        "port": 8601,
        "name": "WhaleTrack Live",
        "category": "revenue",
        "icon": "🐋",
        "public_url": None,
        "systemd": "whaletrack-live.service",
        "health_endpoint": "/api/stats",
    },
    "credits-manager": {
        "port": 8955,
        "name": "Credits Manager",
        "category": "revenue",
        "icon": "🏦",
        "public_url": None,
        "systemd": "credits-manager.service",
    },
    "credits-gateway": {
        "port": 8765,
        "name": "Credits Gateway",
        "category": "revenue",
        "icon": "💳",
        "public_url": "https://fullpotential.ai/services/credits/purchase",
        "systemd": "fpai-fp-credits-gateway.service",
    },

    # SECONDARY (162.0.208.88) - AI, Consciousness, Intelligence Processing
    "ai-brain": {
        "host": SECONDARY_IP,
        "port": 8101,
        "name": "AI Brain",
        "category": "intelligence",
        "icon": "🧠",
        "public_url": None,
    },
    "ollama": {
        "host": SECONDARY_IP,
        "port": 11434,
        "name": "Ollama",
        "category": "intelligence",
        "icon": "🦙",
        "public_url": None,
        "health_endpoint": "/api/tags",
    },
    "consciousness-verifier": {
        "host": CONSCIOUSNESS_VERIFIER_HOST,
        "port": CONSCIOUSNESS_VERIFIER_PORT,
        "name": "Consciousness Verifier",
        "category": "consciousness",
        "icon": "🧪",
        "public_url": None,
        "health_endpoint": "/health",
    },
}

CATEGORIES = {
    "core": {"name": "Core Systems", "color": "#3b82f6", "description": "Foundation services"},
    "intelligence": {"name": "Intelligence", "color": "#8b5cf6", "description": "AI & decision making"},
    "wellness": {"name": "Wellness", "color": "#10b981", "description": "Health optimization"},
    "revenue": {"name": "Revenue", "color": "#f59e0b", "description": "Value generation"},
    "interface": {"name": "Interface", "color": "#06b6d4", "description": "User touchpoints"},
    "infrastructure": {"name": "Infrastructure", "color": "#64748b", "description": "System backbone"},
    "coordination": {"name": "Coordination", "color": "#ec4899", "description": "Multi-agent sync"},
    "consciousness": {"name": "Consciousness", "color": "#fbbf24", "description": "System awareness"},
}

# =============================================================================
# OMNISCIENT SCANNER v3
# =============================================================================

class OmniscientScanner:
    """The all-seeing eye that scans the entire system"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ts: Dict[str, float] = {}
        self.last_scan = None
        self._overview_cache: Optional[Dict[str, Any]] = None
        self._overview_cache_ts: float = 0.0
        self._booted_at_ts: float = time.time()
        self.service_history: Dict[str, deque] = {}
        self.alerts: List[Dict] = []
        self._alert_dedupe: Dict[str, float] = {}  # key -> last_ts (unix)
        self.metrics_history: deque = deque(maxlen=60)  # Last 60 data points
        self.scan_count = 0

    def _cache_is_fresh(self, key: str, ttl_s: float) -> bool:
        ts = self.cache_ts.get(key)
        return bool(ts) and (time.time() - ts) < ttl_s and (key in self.cache)

    def _cache_get(self, key: str, ttl_s: float, default=None):
        if self._cache_is_fresh(key, ttl_s):
            return self.cache.get(key)
        return default

    def _cache_set(self, key: str, value: Any):
        self.cache[key] = value
        self.cache_ts[key] = time.time()

    def get_boot_snapshot(self) -> Dict[str, Any]:
        """
        Fast, non-blocking snapshot for initial page render / WS init.
        Uses the last computed overview if available; otherwise returns safe defaults.
        """
        if self._overview_cache:
            return self._overview_cache

        # If we have partial caches, use them; otherwise default to empty.
        services = self.cache.get("services") if isinstance(self.cache.get("services"), dict) else {}
        system_metrics = self.cache.get("system") if isinstance(self.cache.get("system"), dict) else {}
        docker = self.cache.get("docker") if isinstance(self.cache.get("docker"), dict) else {"total": 0, "running": 0, "healthy": 0, "unhealthy": 0, "containers": []}
        errors = self.cache.get("errors") if isinstance(self.cache.get("errors"), dict) else {"errors_last_hour": 0, "errors_last_5m": 0, "alert_level": "unknown"}
        coordination = self.cache.get("coordination") if isinstance(self.cache.get("coordination"), dict) else {"intents_total": 0, "claims_total": 0, "top_intent": None, "recent_messages": []}
        sessions = self.cache.get("sessions") if isinstance(self.cache.get("sessions"), dict) else {"active_count": 0, "sessions": []}

        # Minimal category grouping for template safety.
        by_category = {}
        for cat_id, cat_info in CATEGORIES.items():
            cat_services = [s for s in services.values() if isinstance(s, dict) and s.get("category") == cat_id]
            by_category[cat_id] = {
                **cat_info,
                "services": cat_services,
                "online": len([s for s in cat_services if s.get("status") in ["healthy", "online"]]),
                "total": len(cat_services),
            }

        online_count = len([s for s in services.values() if isinstance(s, dict) and s.get("status") in ["healthy", "online"]])
        total_count = len(services) if isinstance(services, dict) else 0
        avg_latency = 0
        try:
            avg_latency = sum((s.get("latency_ms") or 0) for s in services.values() if isinstance(s, dict)) / max(1, online_count)
        except Exception:
            avg_latency = 0

        cpu_pct = float(system_metrics.get("cpu_percent", 0) or 0)
        mem_pct = float(system_metrics.get("memory_percent", 0) or 0)
        disk_pct = float(system_metrics.get("disk_percent", 0) or 0)

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "services_online": online_count,
                "services_healthy": len([s for s in services.values() if isinstance(s, dict) and s.get("status") == "healthy"]),
                "services_total": total_count,
                "health_percent": round(online_count / max(1, total_count) * 100) if total_count else 0,
                "health_score": 0,
                "avg_latency_ms": round(avg_latency, 2),
                "active_sessions": sessions.get("active_count", 0) if isinstance(sessions, dict) else 0,
            },
            "system": {
                "cpu_percent": cpu_pct,
                "memory_percent": mem_pct,
                "disk_percent": disk_pct,
            },
            "docker": docker,
            "errors": errors,
            "coordination": coordination,
            "services": services,
            "categories": by_category,
            "alerts": self.alerts[:10],
            "trends": list(self.metrics_history)[-20:],
            "scan_count": self.scan_count,
            "version": VERSION,
            "boot": {"fast": True, "booted_at": self._booted_at_ts},
        }
        
    def add_alert(self, level: str, message: str, service: str = None):
        """Add an alert to the system"""
        # Dedupe identical alerts during the background scan loop
        key = f"{level}|{service or ''}|{message}"
        now = time.time()
        last = self._alert_dedupe.get(key)
        if last and (now - last) < 60:
            return
        self._alert_dedupe[key] = now

        alert = {
            "id": f"alert-{datetime.utcnow().timestamp()}",
            "level": level,  # critical, warning, info
            "message": message,
            "service": service,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "acknowledged": False
        }
        self.alerts.insert(0, alert)
        self.alerts = self.alerts[:50]  # Keep last 50 alerts
        
    async def scan_service(self, service_id: str, config: dict, client: Optional[httpx.AsyncClient] = None) -> dict:
        """Scan a single service for health and capabilities"""
        # Separate:
        # - display host/url (what the user should open in their browser)
        # - probe host/url (what this server should call to measure health)
        display_host = config.get("host") or SERVER_IP
        host = config.get("host")

        local_hosts = {
            None,
            "",
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            PRIMARY_IP,
            PRIMARY_TAILSCALE_IP,
            SERVER_IP,
        }
        probe_host = "127.0.0.1" if (host in local_hosts) else host
        display_url = f"http://{display_host}:{config['port']}"
        probe_url = f"http://{probe_host}:{config['port']}"
        health_endpoint = config.get("health_endpoint", "/health")
        if not health_endpoint.startswith("/"):
            health_endpoint = "/" + health_endpoint
        public_url = config.get("public_url") or display_url
        result = {
            "id": service_id,
            "name": config["name"],
            "port": config["port"],
            "category": config["category"],
            "icon": config["icon"],
            "url": public_url,
            "internal_url": display_url,
            "probe_url": probe_url,
            "status": "unknown",
            "latency_ms": None,
            "health_data": None,
            "uptime_percent": 100,
            "last_check": datetime.utcnow().isoformat() + "Z"
        }
        
        timeout_s = float(os.getenv("GODMODE_SERVICE_TIMEOUT", "2.5"))
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=timeout_s)
            close_client = True

        try:
            start = datetime.utcnow()

            try:
                resp = await client.get(f"{probe_url}{health_endpoint}")
                latency = (datetime.utcnow() - start).total_seconds() * 1000
                result["latency_ms"] = round(latency, 2)

                if resp.status_code == 200:
                    result["status"] = "healthy"
                    try:
                        result["health_data"] = resp.json()
                    except Exception:
                        result["health_data"] = {"raw": resp.text[:200]}
                else:
                    result["status"] = "degraded"
            except Exception:
                try:
                    resp = await client.get(probe_url)
                    latency = (datetime.utcnow() - start).total_seconds() * 1000
                    result["latency_ms"] = round(latency, 2)
                    result["status"] = "online" if resp.status_code < 500 else "error"
                except Exception:
                    result["status"] = "offline"
                    self.add_alert("critical", f"{config['name']} is offline", service_id)
        except Exception as e:
            result["status"] = "offline"
            result["error"] = str(e)
        finally:
            if close_client:
                try:
                    await client.aclose()
                except Exception:
                    pass
            
        # Store history
        if service_id not in self.service_history:
            self.service_history[service_id] = deque(maxlen=100)
        self.service_history[service_id].append({
            "status": result["status"],
            "latency": result["latency_ms"],
            "time": result["last_check"]
        })
        
        # Calculate uptime
        history = list(self.service_history[service_id])
        if history:
            online_count = sum(1 for h in history if h["status"] in ["healthy", "online", "degraded"])
            result["uptime_percent"] = round(online_count / len(history) * 100, 1)

        # Auto-clear stale "offline" alerts when a service recovers
        if result["status"] in ["healthy", "online", "degraded"]:
            self.alerts = [
                a for a in self.alerts
                if not (
                    a.get("service") == service_id
                    and "offline" in str(a.get("message", "")).lower()
                )
            ]
        
        return result
    
    async def scan_all_services(self) -> Dict[str, Any]:
        """Scan all known services in parallel"""
        timeout_s = float(os.getenv("GODMODE_SERVICE_TIMEOUT", "2.5"))
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            tasks = [self.scan_service(sid, config, client=client) for sid, config in LIVE_SERVICES.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        services = {}
        for result in results:
            if isinstance(result, dict):
                services[result["id"]] = result
            
        self.cache["services"] = services
        self.cache_ts["services"] = time.time()
        self.last_scan = datetime.utcnow()
        self.scan_count += 1
        
        return services
    
    async def scan_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics (CPU, Memory, Disk)"""
        try:
            # Run OS probes off the event loop thread to keep the UI responsive.
            cpu_f = asyncio.to_thread(
                subprocess.run,
                ["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            mem_f = asyncio.to_thread(
                subprocess.run,
                ["sh", "-c", "free -m | awk '/Mem:/ {print $3, $2}'"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            disk_f = asyncio.to_thread(
                subprocess.run,
                ["sh", "-c", "df -h / | awk 'NR==2 {print $3, $2, $5}'"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            load_f = asyncio.to_thread(
                subprocess.run,
                ["sh", "-c", "cat /proc/loadavg | awk '{print $1, $2, $3}'"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            cpu_result, mem_result, disk_result, load_result = await asyncio.gather(cpu_f, mem_f, disk_f, load_f)

            cpu_percent = float(cpu_result.stdout.strip()) if (cpu_result.stdout or "").strip() else 0

            mem_parts = (mem_result.stdout or "").strip().split()
            mem_used = int(mem_parts[0]) if len(mem_parts) > 0 and mem_parts[0].isdigit() else 0
            mem_total = int(mem_parts[1]) if len(mem_parts) > 1 and mem_parts[1].isdigit() else 1

            disk_parts = (disk_result.stdout or "").strip().split()
            disk_used = disk_parts[0] if len(disk_parts) > 0 else "0"
            disk_total = disk_parts[1] if len(disk_parts) > 1 else "0"
            disk_percent_str = disk_parts[2].replace("%", "") if len(disk_parts) > 2 else "0"
            disk_percent = float(disk_percent_str) if disk_percent_str.replace(".", "").isdigit() else 0

            load_parts = (load_result.stdout or "").strip().split()
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_used_mb": mem_used,
                "memory_total_mb": mem_total,
                "memory_percent": round(mem_used / max(1, mem_total) * 100, 1),
                "disk_used": disk_used,
                "disk_total": disk_total,
                "disk_percent": disk_percent,
                "load_1m": float(load_parts[0]) if len(load_parts) > 0 else 0,
                "load_5m": float(load_parts[1]) if len(load_parts) > 1 else 0,
                "load_15m": float(load_parts[2]) if len(load_parts) > 2 else 0,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            # Store in history for trends
            self.metrics_history.append(metrics)
            
            # Alert if resources critical
            if metrics["memory_percent"] > 90:
                self.add_alert("critical", f"Memory usage critical: {metrics['memory_percent']}%")
            elif metrics["memory_percent"] > 80:
                self.add_alert("warning", f"Memory usage high: {metrics['memory_percent']}%")
                
            if metrics["disk_percent"] > 90:
                self.add_alert("critical", f"Disk usage critical: {metrics['disk_percent']}%")
            
            self._cache_set("system", metrics)
            return metrics
        except Exception as e:
            return {"error": str(e), "cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}
    
    async def scan_docker_containers(self) -> Dict[str, Any]:
        """Get Docker container status"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}|{{.Image}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            containers = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    status_text = parts[1] if len(parts) > 1 else "unknown"
                    containers.append({
                        "name": parts[0],
                        "status": status_text,
                        "ports": parts[2] if len(parts) > 2 else "",
                        "image": parts[3] if len(parts) > 3 else "",
                        "healthy": "healthy" in status_text.lower(),
                        "up": "up" in status_text.lower(),
                        "unhealthy": "unhealthy" in status_text.lower()
                    })
            
            unhealthy_count = len([c for c in containers if c["unhealthy"]])
            if unhealthy_count > 0:
                self.add_alert("warning", f"{unhealthy_count} Docker containers unhealthy")
            
            data = {
                "total": len(containers),
                "running": len([c for c in containers if c["up"]]),
                "healthy": len([c for c in containers if c["healthy"]]),
                "unhealthy": unhealthy_count,
                "containers": containers
            }
            self._cache_set("docker", data)
            return data
        except Exception as e:
            return {"total": 0, "running": 0, "healthy": 0, "containers": [], "error": str(e)}
    
    async def scan_recent_errors(self) -> Dict[str, Any]:
        """Get recent error count from journalctl"""
        try:
            r_hour_f = asyncio.to_thread(
                subprocess.run,
                ["sh", "-c", "journalctl --since '1 hour ago' -p err --no-pager 2>/dev/null | wc -l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            r_5m_f = asyncio.to_thread(
                subprocess.run,
                ["sh", "-c", "journalctl --since '5 minutes ago' -p err --no-pager 2>/dev/null | wc -l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            r_hour, r_5m = await asyncio.gather(r_hour_f, r_5m_f)
            errors_last_hour = int(r_hour.stdout.strip()) if r_hour.stdout.strip().isdigit() else 0
            errors_last_5m = int(r_5m.stdout.strip()) if r_5m.stdout.strip().isdigit() else 0

            # Alert based on *recent* error rate (5m window) so fixes clear quickly.
            alert_level = "critical" if errors_last_5m > 200 else ("warning" if errors_last_5m > 50 else "normal")

            if alert_level == "critical":
                self.add_alert(
                    "critical",
                    f"High error rate: {errors_last_5m} errors in last 5m ({errors_last_hour} in last hour)"
                )
            elif alert_level == "warning":
                self.add_alert("warning", f"Elevated error rate: {errors_last_5m} errors in last 5m")

            data = {
                "errors_last_hour": errors_last_hour,
                "errors_last_5m": errors_last_5m,
                "alert_level": alert_level
            }
            self._cache_set("errors", data)
            return data
        except Exception as e:
            return {"errors_last_hour": 0, "errors_last_5m": 0, "alert_level": "unknown", "error": str(e)}

    async def scan_security_threats(self) -> Dict[str, Any]:
        """Scan for security threats like SSH brute force attempts"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["lastb", "-n", "50"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            failed_ips = {}
            for line in result.stdout.split("\n"):
                parts = line.split()
                if len(parts) >= 3:
                    ip = parts[2]
                    if ip and ip[0].isdigit():
                        failed_ips[ip] = failed_ips.get(ip, 0) + 1
            
            total_attempts = len(result.stdout.strip().split("\n"))
            threat_level = "high" if len(failed_ips) > 3 else ("medium" if failed_ips else "low")
            
            top_attackers = [
                {"ip": ip, "attempts": count}
                for ip, count in sorted(failed_ips.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            if threat_level == "high":
                self.add_alert("warning", f"SSH brute force from {len(failed_ips)} IPs")
            
            data = {
                "threat_level": threat_level,
                "failed_ssh_attempts": total_attempts,
                "attacking_ips": top_attackers,
                "unique_attackers": len(failed_ips)
            }
            self._cache_set("security", data)
            return data
        except Exception as e:
            return {"threat_level": "unknown", "error": str(e)}
    
    async def scan_cron_jobs(self) -> Dict[str, Any]:
        """Scan scheduled cron jobs"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            jobs = [line for line in result.stdout.split("\n") if line.strip() and not line.startswith("#")]
            
            data = {
                "total_jobs": len(jobs),
                "jobs": jobs[:15]
            }
            self._cache_set("cron", data)
            return data
        except Exception as e:
            return {"total_jobs": 0, "jobs": [], "error": str(e)}
    
    async def scan_backups(self) -> Dict[str, Any]:
        """Check backup status"""
        try:
            manifest_path = Path("/opt/fpai/backups/manifest.json")
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
                return {
                    "status": "healthy",
                    "last_backup": manifest.get("last_backup"),
                    "total_backups": len(manifest.get("backups", []))
                }
            return {"status": "no_manifest", "total_backups": 0}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    
    async def scan_sessions(self) -> Dict[str, Any]:
        """Scan active coordination sessions"""
        sessions_path = Path("/opt/fpai/docs/coordination/sessions/ACTIVE")
        active_sessions = []
        
        if sessions_path.exists():
            for session_file in sessions_path.glob("*.json"):
                try:
                    with open(session_file) as f:
                        session_data = json.load(f)
                        active_sessions.append(session_data)
                except:
                    pass
                    
        return {"active_count": len(active_sessions), "sessions": active_sessions}

    def _safe_load_json(self, path: Path, default=None):
        try:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    async def scan_legacy_coordination(self, limit_messages: int = 5) -> Dict[str, Any]:
        """
        Read coordination state from the legacy /opt/fpai/god-mode tree.
        This is read-only integration to avoid running two separate God Mode UIs.
        """
        intents_total = len(list(LEGACY_INTENTS_DIR.glob("*.json"))) if LEGACY_INTENTS_DIR.exists() else 0
        claims_total = len(list(LEGACY_CLAIMS_DIR.glob("*.claim"))) if LEGACY_CLAIMS_DIR.exists() else 0

        # Top intent by score (best-effort)
        top_intent = None
        if LEGACY_INTENTS_DIR.exists():
            best_score = None
            for fpath in LEGACY_INTENTS_DIR.glob("*.json"):
                data = self._safe_load_json(fpath, default={}) or {}
                score = data.get("score", 0)
                try:
                    score = float(score)
                except Exception:
                    score = 0

                if best_score is None or score > best_score:
                    best_score = score
                    top_intent = {
                        "id": fpath.stem,
                        "title": data.get("droplet_name", fpath.stem),
                        "desc": data.get("architect_intent", "") or "",
                        "score": score,
                        "created_at": data.get("created_at"),
                    }

        # Recent broadcast messages
        messages = []
        if LEGACY_BROADCAST_DIR.exists():
            files = sorted(list(LEGACY_BROADCAST_DIR.glob("*.json")), reverse=True)[: max(1, limit_messages)]
            for fpath in files:
                data = self._safe_load_json(fpath, default=None)
                if isinstance(data, dict):
                    messages.append(data)

        return {
            "source": str(LEGACY_COORDINATION_DIR),
            "intents_total": intents_total,
            "claims_total": claims_total,
            "top_intent": top_intent,
            "recent_messages": messages,
        }

    async def get_coordination_board(self) -> Dict[str, Any]:
        """Return a simple kanban-style view of intents vs claimed work (legacy coordination)."""
        board = {"intent": [], "building": [], "deployed": []}
        claims = set()

        if LEGACY_CLAIMS_DIR.exists():
            for fpath in LEGACY_CLAIMS_DIR.glob("*.claim"):
                claims.add(fpath.stem.lower())

        if LEGACY_INTENTS_DIR.exists():
            for fpath in LEGACY_INTENTS_DIR.glob("*.json"):
                data = self._safe_load_json(fpath, default={}) or {}
                item = {
                    "id": fpath.stem,
                    "title": data.get("droplet_name", fpath.stem),
                    "desc": data.get("architect_intent", "") or "",
                    "score": data.get("score", 0),
                    "created_at": data.get("created_at"),
                }
                haystack = f"{item['id']} {item['title']}".lower()
                is_claimed = any(haystack in c or c in haystack for c in claims) if claims else False
                if is_claimed:
                    board["building"].append(item)
                else:
                    board["intent"].append(item)

        board["intent"].sort(key=lambda x: x.get("score", 0), reverse=True)
        board["building"].sort(key=lambda x: x.get("score", 0), reverse=True)
        return board

    async def get_coordination_messages(self, limit: int = 20) -> Dict[str, Any]:
        msgs = []
        if LEGACY_BROADCAST_DIR.exists():
            files = sorted(list(LEGACY_BROADCAST_DIR.glob("*.json")), reverse=True)[: max(1, limit)]
            for fpath in files:
                data = self._safe_load_json(fpath, default=None)
                if isinstance(data, dict):
                    msgs.append(data)
        return {"messages": msgs, "total": len(msgs), "source": str(LEGACY_BROADCAST_DIR)}

    async def get_coordination_graph(self) -> Dict[str, Any]:
        """Return a minimal agent<->work graph from heartbeats and claims (legacy coordination)."""
        nodes = []
        links = []
        seen_agents = set()

        if LEGACY_HEARTBEATS_DIR.exists():
            files = sorted(list(LEGACY_HEARTBEATS_DIR.glob("*.json")), reverse=True)[:50]
            for fpath in files:
                data = self._safe_load_json(fpath, default={}) or {}
                sid = data.get("session_id") or fpath.stem
                if sid and sid not in seen_agents:
                    nodes.append({"id": sid, "group": "agent", "status": "active"})
                    seen_agents.add(sid)

        if LEGACY_CLAIMS_DIR.exists():
            for fpath in LEGACY_CLAIMS_DIR.glob("*.claim"):
                data = self._safe_load_json(fpath, default={}) or {}
                session_id = data.get("session_id") or data.get("claimed_by") or "unknown"
                resource = fpath.stem
                nodes.append({"id": resource, "group": "work", "status": "claimed"})
                links.append({"source": session_id, "target": resource})
                if session_id not in seen_agents:
                    nodes.append({"id": session_id, "group": "agent", "status": "working"})
                    seen_agents.add(session_id)

        return {"nodes": nodes, "links": links}
    
    async def get_system_overview(self, fast: bool = False) -> Dict[str, Any]:
        """
        Get complete system overview.

        - `fast=True` returns quickly (uses cached/stale data and avoids expensive fresh scans).
        - Always caches sub-results with TTLs to keep the UI responsive.
        """
        now = time.time()
        overview_ttl = float(os.getenv("GODMODE_OVERVIEW_TTL", "2.0"))
        if fast:
            overview_ttl = min(overview_ttl, 0.5)
        if self._overview_cache and (now - self._overview_cache_ts) < overview_ttl:
            return self._overview_cache

        # TTLs (seconds) — tuned for responsiveness
        ttl_services = float(os.getenv("GODMODE_TTL_SERVICES", "15"))
        ttl_system = float(os.getenv("GODMODE_TTL_SYSTEM", "10"))
        ttl_docker = float(os.getenv("GODMODE_TTL_DOCKER", "30"))
        ttl_errors = float(os.getenv("GODMODE_TTL_ERRORS", "30"))
        ttl_sessions = float(os.getenv("GODMODE_TTL_SESSIONS", "60"))
        ttl_coordination = float(os.getenv("GODMODE_TTL_COORDINATION", "15"))

        defaults = {
            "services": {},
            "system": {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0},
            "docker": {"total": 0, "running": 0, "healthy": 0, "unhealthy": 0, "containers": []},
            "errors": {"errors_last_hour": 0, "errors_last_5m": 0, "alert_level": "unknown"},
            "sessions": {"active_count": 0, "sessions": []},
            "coordination": {"intents_total": 0, "claims_total": 0, "top_intent": None, "recent_messages": []},
        }

        def _pick_cached(key: str, ttl_s: float):
            if self._cache_is_fresh(key, ttl_s):
                return self.cache.get(key)
            return None

        # Decide what to compute now.
        # In fast mode, never block for missing expensive scans — use cached or defaults.
        pending: Dict[str, Any] = {}
        services = _pick_cached("services", ttl_services)
        if services is None and not fast:
            pending["services"] = self.scan_all_services()
        elif services is None:
            services = self.cache.get("services", defaults["services"])

        system_metrics = _pick_cached("system", ttl_system)
        if system_metrics is None and not fast:
            pending["system"] = self.scan_system_metrics()
        elif system_metrics is None:
            system_metrics = self.cache.get("system", defaults["system"])

        docker = _pick_cached("docker", ttl_docker)
        if docker is None and not fast:
            pending["docker"] = self.scan_docker_containers()
        elif docker is None:
            docker = self.cache.get("docker", defaults["docker"])

        errors = _pick_cached("errors", ttl_errors)
        if errors is None and not fast:
            pending["errors"] = self.scan_recent_errors()
        elif errors is None:
            errors = self.cache.get("errors", defaults["errors"])

        sessions = _pick_cached("sessions", ttl_sessions)
        if sessions is None and not fast:
            pending["sessions"] = self.scan_sessions()
        elif sessions is None:
            sessions = self.cache.get("sessions", defaults["sessions"])

        coordination = _pick_cached("coordination", ttl_coordination)
        if coordination is None and not fast:
            pending["coordination"] = self.scan_legacy_coordination(limit_messages=20)
        elif coordination is None:
            coordination = self.cache.get("coordination", defaults["coordination"])

        if pending:
            keys = list(pending.keys())
            results = await asyncio.gather(*[pending[k] for k in keys], return_exceptions=True)
            for k, res in zip(keys, results):
                if isinstance(res, Exception):
                    val = self.cache.get(k, defaults.get(k))
                else:
                    val = res
                    self._cache_set(k, val)
                if k == "services":
                    services = val
                elif k == "system":
                    system_metrics = val
                elif k == "docker":
                    docker = val
                elif k == "errors":
                    errors = val
                elif k == "sessions":
                    sessions = val
                elif k == "coordination":
                    coordination = val
        
        # Calculate metrics
        online_count = len([s for s in services.values() if s["status"] in ["healthy", "online"]])
        total_count = len(services)
        healthy_count = len([s for s in services.values() if s["status"] == "healthy"])
        avg_latency = sum(s["latency_ms"] or 0 for s in services.values()) / max(1, online_count)
        
        # Group by category
        by_category = {}
        for cat_id, cat_info in CATEGORIES.items():
            cat_services = [s for s in services.values() if s["category"] == cat_id]
            by_category[cat_id] = {
                **cat_info,
                "services": cat_services,
                "online": len([s for s in cat_services if s["status"] in ["healthy", "online"]]),
                "total": len(cat_services)
            }
        
        # Overall health score (0-100)
        # Docker: only penalize for unhealthy *running* containers; if nothing is running, treat as neutral.
        docker_running = docker.get("running", 0) if isinstance(docker, dict) else 0
        docker_unhealthy = docker.get("unhealthy", 0) if isinstance(docker, dict) else 0
        docker_score = 1.0 if docker_running == 0 else max(0.0, (docker_running - docker_unhealthy) / max(1, docker_running))

        # Errors: use a short window so fixes clear quickly, while still reporting last-hour context separately.
        errors_5m = errors.get("errors_last_5m", 0) if isinstance(errors, dict) else 0
        errors_score = 1 - min(errors_5m / 200, 1)  # critical threshold ~200 errors / 5m

        health_score = (
            (online_count / max(1, total_count)) * 40 +  # Service uptime (40%)
            docker_score * 20 +  # Docker health (20%)
            (1 - min(system_metrics.get("memory_percent", 0) / 100, 1)) * 20 +  # Memory (20%)
            errors_score * 20  # Error rate (20%)
        )
        
        overview = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "services_online": online_count,
                "services_healthy": healthy_count,
                "services_total": total_count,
                "health_percent": round(online_count / max(1, total_count) * 100),
                "health_score": round(health_score),
                "avg_latency_ms": round(avg_latency, 2),
                "active_sessions": sessions["active_count"],
            },
            "system": system_metrics,
            "docker": docker,
            "errors": errors,
            "coordination": coordination,
            "services": services,
            "categories": by_category,
            "alerts": self.alerts[:10],  # Last 10 alerts
            "trends": list(self.metrics_history)[-20:],  # Last 20 data points
            "scan_count": self.scan_count,
            "version": VERSION
        }
        self._overview_cache = overview
        self._overview_cache_ts = time.time()
        return overview

# =============================================================================
# APP SETUP
# =============================================================================

scanner = OmniscientScanner()
active_connections: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle"""
    print(f"⚡ GOD MODE v{VERSION} - OMNISCIENT COMMAND CENTER ONLINE")
    # Do not block startup on full system scans; warm caches in the background.
    asyncio.create_task(background_scanner())
    yield
    print("⚡ God Mode shutting down...")

async def background_scanner():
    """Background task to continuously scan system"""
    while True:
        try:
            # If nobody is watching, scan less frequently to reduce load.
            scan_interval = 15 if active_connections else 60

            # One scan per loop (avoid duplicate work).
            overview = await scanner.get_system_overview()

            # Broadcast to all WebSocket connections
            if active_connections:
                for ws in active_connections:
                    try:
                        await ws.send_json({"type": "update", "data": overview})
                    except:
                        pass
        except Exception as e:
            print(f"Background scan error: {e}")
        await asyncio.sleep(scan_interval)

app = FastAPI(
    title=f"God Mode v{VERSION}",
    description="Omniscient System Command Center",
    version=VERSION,
    lifespan=lifespan
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard UI"""
    # Fast boot: render immediately from cached/stub data, then let WS updates fill in.
    overview = scanner.get_boot_snapshot()
    return templates.TemplateResponse("index.html", {"request": request, "data": overview})

@app.get("/api/overview")
async def api_overview():
    """Full system overview API"""
    return await scanner.get_system_overview()

@app.get("/api/connections")
async def api_connections():
    """
    Explicit upstream connectivity checks (SSOT vs configured runtime).
    This is separate from the general service scan so miswired endpoints are obvious.
    """
    ssot = _load_ssot()

    def _source(env_var: str, ssot_val: Optional[str]) -> str:
        if os.getenv(env_var):
            return "env"
        if ssot_val:
            return "ssot"
        return "default"

    def _service_base_url(service_id: str) -> Optional[str]:
        cfg = LIVE_SERVICES.get(service_id)
        if not cfg:
            return None
        host = cfg.get("host") or SERVER_IP
        port = cfg.get("port")
        if not port:
            return None
        return f"http://{host}:{port}"

    # SSOT truths
    ssot_ai = _ssot_routing_url(ssot, "ai_inference")
    ssot_ollama = _ssot_routing_url(ssot, "ollama")
    ssot_trading = _ssot_routing_url(ssot, "trading")
    ssot_data = _ssot_routing_url(ssot, "data_service")
    ssot_nerve = _ssot_routing_url(ssot, "nerve_center")

    configured_ai = AI_BRAIN_URL
    configured_ollama = OLLAMA_ENDPOINT
    configured_trading = ssot_trading or _service_base_url("whaletrack-magnet")
    configured_data = _service_base_url("data-service") or ssot_data
    configured_nerve = _service_base_url("nerve-center") or ssot_nerve
    configured_conscious = f"http://{CONSCIOUSNESS_VERIFIER_HOST}:{CONSCIOUSNESS_VERIFIER_PORT}"
    configured_aria = (os.getenv("ARIA_ENDPOINT") or os.getenv("ARIA_URL") or "").strip() or None

    checks = [
        {
            "id": "ai_brain",
            "name": "AI Brain",
            "configured_base_url": configured_ai,
            "ssot_url": ssot_ai,
            "source": _source("AI_BRAIN_URL", ssot_ai),
            "probe_path": "/health",
        },
        {
            "id": "ollama",
            "name": "Ollama",
            "configured_base_url": configured_ollama,
            "ssot_url": ssot_ollama,
            "source": _source("OLLAMA_ENDPOINT", ssot_ollama),
            "probe_path": "/api/tags",
        },
        {
            "id": "trading",
            "name": "Trading (WhaleTrack Magnet)",
            "configured_base_url": configured_trading,
            "ssot_url": ssot_trading,
            "source": _source("TRADING_URL", ssot_trading),
            "probe_path": "/health",
        },
        {
            "id": "data_service",
            "name": "Data Service",
            "configured_base_url": configured_data,
            "ssot_url": ssot_data,
            "source": _source("DATA_SERVICE_URL", ssot_data),
            "probe_path": "/health",
        },
        {
            "id": "nerve_center",
            "name": "Nerve Center",
            "configured_base_url": configured_nerve,
            "ssot_url": ssot_nerve,
            "source": _source("NERVE_CENTER_URL", ssot_nerve),
            "probe_path": "/health",
        },
        {
            "id": "consciousness_verifier",
            "name": "Consciousness Verifier",
            "configured_base_url": configured_conscious,
            "ssot_url": None,
            "source": "ssot" if ssot else "default",
            "probe_path": "/health",
        },
        {
            "id": "aria",
            "name": "Aria",
            "configured_base_url": (configured_aria.rstrip("/") if configured_aria else None) or _aria_base_url(),
            "ssot_url": None,
            "source": "env" if configured_aria else "default",
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
                suggested_fix = f"Configured URL differs from SSOT. Consider setting {c.get('id').upper()} via env or restart to reload SSOT."
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

@app.get("/api/ritual/recent")
async def ritual_recent(limit: int = 10):
    """Return the most recent alignment ritual commits (JSONL tail)."""
    try:
        limit = max(1, min(int(limit), 50))
    except Exception:
        limit = 10

    if not RITUAL_LOG_FILE.exists():
        return {"records": [], "count": 0, "path": str(RITUAL_LOG_FILE)}

    try:
        # Avoid reading an unbounded log file into memory; tail the last chunk.
        with open(RITUAL_LOG_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            read_size = min(size, 20000)  # ~20KB tail is enough for ~10-50 JSONL records
            if read_size > 0:
                f.seek(-read_size, os.SEEK_END)
            chunk = f.read(read_size).decode("utf-8", errors="ignore")

        lines = chunk.splitlines()
        tail = lines[-limit:]
        records = []
        for line in tail:
            line = (line or "").strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
        return {"records": records, "count": len(records), "path": str(RITUAL_LOG_FILE)}
    except Exception as e:
        return {"records": [], "count": 0, "path": str(RITUAL_LOG_FILE), "error": str(e)}

@app.post("/api/ritual/commit")
async def ritual_commit(request: Request):
    """
    Commit a 1-minute alignment ritual:
      intent → signals → action → reflection
    Persists as JSONL under core/STATE (or configured FP_STATE_DIR).
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    intent = str(payload.get("intent") or "").strip() or "Revenue"
    action = str(payload.get("action") or payload.get("chosen_action") or "").strip()
    reflection = str(payload.get("reflection") or "").strip()
    owner = str(payload.get("owner") or "").strip() or None
    signals = payload.get("signals") if isinstance(payload.get("signals"), dict) else {}

    ts = datetime.utcnow().isoformat() + "Z"
    rid = f"ritual-{int(time.time())}-{secrets.token_hex(4)}"

    record = {
        "id": rid,
        "timestamp": ts,
        "intent": intent,
        "signals": signals,
        "action": action,
        "reflection": reflection,
        "owner": owner,
        "source": "godmode-v3",
    }

    write_error = None
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(RITUAL_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        write_error = str(e)

    # Optional: ingest into Data Service learnings (disabled by default)
    ingest_result = None
    if str(os.getenv("ENABLE_RITUAL_INGEST", "")).lower() in ("1", "true", "yes", "on"):
        data_service_url = os.getenv("DATA_SERVICE_URL") or _ssot_routing_url(_SSOT, "data_service")
        if data_service_url:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        f"{data_service_url.rstrip('/')}/api/data/memory/learn",
                        json={
                            "context": f"GodMode alignment | intent={intent} | owner={owner or 'unknown'}",
                            "action": action,
                            "outcome": "alignment_commit",
                            "lesson": reflection or json.dumps(signals),
                        },
                    )
                    ingest_result = {"status_code": resp.status_code, "ok": resp.status_code < 300}
            except Exception as e:
                ingest_result = {"ok": False, "error": str(e)}

    # Optional: create an intent (mission) in coordination (if requested)
    mission_path = None
    if payload.get("create_mission"):
        mission_name = str(payload.get("mission_name") or "").strip()
        mission_desc = str(payload.get("mission_desc") or "").strip() or action
        if mission_name:
            safe = "".join(ch for ch in mission_name if ch.isalnum() or ch in ("-", "_", " ")).strip().replace(" ", "_")[:60] or "mission"
            fname = f"{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}-{safe}-{secrets.token_hex(2)}.json"
            try:
                LEGACY_INTENTS_DIR.mkdir(parents=True, exist_ok=True)
                mission_payload = {
                    "droplet_name": mission_name,
                    "architect_intent": mission_desc,
                    "approval_mode": "auto",
                    "auto_deploy": False,
                    "generated_by": "godmode-ritual",
                    "score": 50,
                    "created_at": ts,
                }
                (LEGACY_INTENTS_DIR / fname).write_text(json.dumps(mission_payload, indent=2), encoding="utf-8")
                mission_path = str(LEGACY_INTENTS_DIR / fname)
            except Exception as e:
                record["mission_error"] = str(e)

    # Optional: broadcast to coordination (off by default to avoid noise)
    broadcast_path = None
    if payload.get("broadcast"):
        try:
            LEGACY_BROADCAST_DIR.mkdir(parents=True, exist_ok=True)
            msg = {
                "from": "godmode",
                "to": "broadcast",
                "timestamp": ts,
                "subject": f"Alignment: {intent}",
                "message": f"{owner + ': ' if owner else ''}{action}".strip(),
            }
            fname = f"{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}-godmode-{secrets.token_hex(2)}.json"
            (LEGACY_BROADCAST_DIR / fname).write_text(json.dumps(msg, indent=2), encoding="utf-8")
            broadcast_path = str(LEGACY_BROADCAST_DIR / fname)
        except Exception as e:
            record["broadcast_error"] = str(e)

    return {
        "status": "ok" if not write_error else "degraded",
        "id": rid,
        "timestamp": ts,
        "log_path": str(RITUAL_LOG_FILE),
        "write_error": write_error,
        "ingest_result": ingest_result,
        "mission_path": mission_path,
        "broadcast_path": broadcast_path,
    }

@app.get("/api/coordination")
async def api_coordination():
    """Legacy coordination summary (intents/claims/messages)."""
    return await scanner.scan_legacy_coordination(limit_messages=20)

@app.get("/api/coordination/board")
async def api_coordination_board():
    """Kanban-style view of coordination intents vs claimed work."""
    return await scanner.get_coordination_board()

@app.get("/api/coordination/messages")
async def api_coordination_messages(limit: int = 20):
    """Recent coordination broadcast messages."""
    return await scanner.get_coordination_messages(limit=limit)

@app.get("/api/coordination/graph")
async def api_coordination_graph():
    """Agent<->work graph from heartbeats and claims."""
    return await scanner.get_coordination_graph()

@app.get("/api/services")
async def api_services():
    """Live services status"""
    return await scanner.scan_all_services()

@app.get("/api/services/{service_id}")
async def api_service_detail(service_id: str):
    """Single service details with history"""
    if service_id in LIVE_SERVICES:
        result = await scanner.scan_service(service_id, LIVE_SERVICES[service_id])
        result["history"] = list(scanner.service_history.get(service_id, []))
        result["config"] = LIVE_SERVICES[service_id]
        return result
    return JSONResponse({"error": "Service not found"}, status_code=404)

@app.get("/api/services/{service_id}/logs")
async def api_service_logs(service_id: str, lines: int = 100):
    """Get service logs"""
    config = LIVE_SERVICES.get(service_id)
    if not config:
        return JSONResponse({"error": "Service not found"}, status_code=404)
    
    logs = ""
    try:
        # Try Docker first
        if config.get("docker"):
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), config["docker"]],
                capture_output=True, text=True, timeout=10
            )
            logs = result.stdout + result.stderr
        # Try systemd
        elif config.get("systemd"):
            result = subprocess.run(
                ["journalctl", "-u", config["systemd"], "-n", str(lines), "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            logs = result.stdout
    except Exception as e:
        logs = f"Error fetching logs: {e}"
    
    return {"service": service_id, "logs": logs, "lines": lines}

@app.post("/api/services/{service_id}/restart")
@admin_required
async def api_restart_service(request: Request, service_id: str):
    """Restart a service"""
    config = LIVE_SERVICES.get(service_id)
    if not config:
        return JSONResponse({"error": "Service not found"}, status_code=404)
    
    try:
        if config.get("docker"):
            result = subprocess.run(
                ["docker", "restart", config["docker"]],
                capture_output=True, text=True, timeout=60
            )
        elif config.get("systemd"):
            result = subprocess.run(
                ["systemctl", "restart", config["systemd"]],
                capture_output=True, text=True, timeout=30
            )
        else:
            return JSONResponse({"error": "No restart method configured"}, status_code=400)
        
        _audit("service_restart", request, {"service_id": service_id, "status": "requested"})
        scanner.add_alert("info", f"Service {config['name']} restarted", service_id)
        return {"status": "restarted", "service": service_id}
    except Exception as e:
        _audit("service_restart_error", request, {"service_id": service_id, "error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/system")
async def api_system():
    """System metrics"""
    return await scanner.scan_system_metrics()

@app.get("/api/docker")
async def api_docker():
    """Docker container status"""
    return await scanner.scan_docker_containers()

@app.get("/api/docker/{container_name}/logs")
async def api_docker_logs(container_name: str, lines: int = 100):
    """Get Docker container logs"""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container_name],
            capture_output=True, text=True, timeout=10
        )
        return {"container": container_name, "logs": result.stdout + result.stderr, "lines": lines}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/docker/{container_name}/restart")
@admin_required
async def api_restart_container(request: Request, container_name: str):
    """Restart a Docker container"""
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True, text=True, timeout=60
        )
        _audit("docker_restart", request, {"container": container_name, "status": "requested"})
        scanner.add_alert("info", f"Container {container_name} restarted")
        return {"status": "restarted", "container": container_name}
    except Exception as e:
        _audit("docker_restart_error", request, {"container": container_name, "error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/alerts")
async def api_alerts():
    """Get system alerts"""
    return {"alerts": scanner.alerts}

@app.post("/api/alerts/{alert_id}/acknowledge")
async def api_acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    for alert in scanner.alerts:
        if alert["id"] == alert_id:
            alert["acknowledged"] = True
            return {"status": "acknowledged"}
    return JSONResponse({"error": "Alert not found"}, status_code=404)

@app.get("/api/trends")
async def api_trends():
    """Get metrics trends"""
    return {"trends": list(scanner.metrics_history), "points": len(scanner.metrics_history)}



# ============================================================
# 🔐 ADMIN LOGIN ENDPOINTS
# ============================================================

@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Login to admin panel"""
    if not ADMIN_PASSWORD_CONFIGURED:
        _audit("admin_login_blocked", request, {"reason": "password_not_configured"})
        return JSONResponse(
            {"error": "Admin password not configured. Set GODMODE_ADMIN_PASSWORD(_HASH) env var."},
            status_code=503,
        )
    try:
        data = await request.json()
        username = data.get("username", "")
        password = data.get("password", "")
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
            token = generate_admin_token()
            response = JSONResponse({"status": "authenticated", "message": "Welcome to God Mode"})
            is_secure = (request.headers.get("x-forwarded-proto", "").lower() == "https") or (request.url.scheme == "https")
            response.set_cookie(
                "admin_token",
                token,
                httponly=True,
                max_age=86400,
                secure=is_secure,
                samesite="strict",
                path="/",
            )
            _audit("admin_login_success", request, {"username": username})
            scanner.add_alert("info", f"Admin login from {_get_client_ip(request)}")
            return response
        else:
            _audit("admin_login_failed", request, {"username": username})
            scanner.add_alert("warning", f"Failed admin login attempt from {_get_client_ip(request)}")
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/api/admin/verify")
async def admin_verify(request: Request):
    """Verify admin session"""
    token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token")
    if verify_admin_token(token):
        return {"authenticated": True}
    return {"authenticated": False}

@app.post("/api/admin/logout")
async def admin_logout(request: Request):
    """Logout admin session"""
    token = request.cookies.get("admin_token")
    if token and token in ADMIN_SESSIONS:
        del ADMIN_SESSIONS[token]
    _audit("admin_logout", request, {})
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie("admin_token")
    return response




# ============================================================
# 🎛️ SERVER CONTROL PANEL - Restart All Services
# ============================================================

ALL_SYSTEMD_SERVICES = [
    "fpai-registry",
    "fpai-orchestrator", 
    "dashboard",
    "godmode",
    "breath-optimizer",
    "fpai-strategic-intelligence",
    "whaletrack-magnet",
    "fpai-ai-gateway",
    "fpai-credits-gateway",
]

@app.post("/api/admin/restart-all")
async def restart_all_services(request: Request):
    """🔄 Restart ALL services - Protected endpoint"""
    token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token")
    if not verify_admin_token(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not ENABLE_ADMIN_RESTART_ALL:
        _audit("admin_restart_all_blocked", request, {"reason": "disabled_by_default"})
        return JSONResponse({"error": "Restart-all is disabled by default (set GODMODE_ENABLE_RESTART_ALL=true)."}, status_code=403)
    
    results = []
    for service in ALL_SYSTEMD_SERVICES:
        try:
            proc = await asyncio.create_subprocess_exec(
                "sudo", "systemctl", "restart", service,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            status = "restarted" if proc.returncode == 0 else "failed"
            results.append({"service": service, "status": status})
        except Exception as e:
            results.append({"service": service, "status": "error", "error": str(e)})
    
    _audit("admin_restart_all", request, {"results": results})
    scanner.add_alert("warning", f"All services restarted by admin")
    return {"status": "complete", "results": results}

@app.get("/api/admin/services-status")
async def get_all_services_status(request: Request):
    """📊 Get status of all registered services"""
    token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token")
    if not verify_admin_token(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    statuses = []
    for service in ALL_SYSTEMD_SERVICES:
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "is-active", service,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            status = stdout.decode().strip()
            statuses.append({"service": service, "status": status})
        except Exception as e:
            statuses.append({"service": service, "status": "unknown", "error": str(e)})
    
    return {"services": statuses, "timestamp": datetime.now().isoformat()}

@app.post("/api/admin/exec")
async def execute_command(request: Request):
    """🖥️ Execute shell command - PROTECTED"""
    token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token")
    if not verify_admin_token(token):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not ENABLE_ADMIN_EXEC:
        _audit("admin_exec_blocked", request, {"reason": "disabled_by_default"})
        return JSONResponse({"error": "Exec is disabled by default (set GODMODE_ENABLE_EXEC=true)."}, status_code=403)
    
    try:
        data = await request.json()
        command = (data.get("command", "") or "").strip()
        if not command:
            return JSONResponse({"error": "Empty command"}, status_code=400)

        # Safety: block shell metacharacters (this endpoint runs without a shell)
        if any(ch in command for ch in [";", "|", "&", ">", "<", "\n", "\r"]):
            return JSONResponse({"error": "Blocked metacharacters in command"}, status_code=403)
        
        # Safety: Block dangerous commands
        blocked = ["rm -rf /", "mkfs", "dd if=", "> /dev/", "chmod 777 /"]
        for b in blocked:
            if b in command:
                return JSONResponse({"error": f"Blocked dangerous command: {b}"}, status_code=403)

        # Allowlist commands (first token) — customize via GODMODE_EXEC_ALLOWLIST
        allowlist = [
            x.strip()
            for x in os.getenv(
                "GODMODE_EXEC_ALLOWLIST",
                "systemctl,journalctl,docker,df,du,free,uptime,top,ps,ss,netstat,tail,cat,ls",
            ).split(",")
            if x.strip()
        ]

        args = shlex.split(command)
        if not args:
            return JSONResponse({"error": "Unable to parse command"}, status_code=400)
        if args[0] not in allowlist:
            return JSONResponse({"error": f"Command not allowed: {args[0]}"}, status_code=403)

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/opt/fpai"
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        
        _audit("admin_exec", request, {"command": command[:200], "exit_code": proc.returncode})
        scanner.add_alert("info", f"Admin executed: {command[:50]}...")
        
        return {
            "stdout": stdout.decode()[-5000:],  # Last 5000 chars
            "stderr": stderr.decode()[-1000:],
            "exit_code": proc.returncode
        }
    except asyncio.TimeoutError:
        _audit("admin_exec_timeout", request, {"command": (locals().get("command") or "")[:200]})
        return JSONResponse({"error": "Command timed out (30s limit)"}, status_code=408)
    except Exception as e:
        _audit("admin_exec_error", request, {"error": str(e)})
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "omniscient",
        "version": VERSION,
        "last_scan": scanner.last_scan.isoformat() if scanner.last_scan else None,
        "services_tracked": len(LIVE_SERVICES),
        "scan_count": scanner.scan_count,
        "uptime": "eternal"
    }

@app.get("/capabilities")
async def capabilities():
    """UDC capabilities"""
    return {
        "name": "God Mode",
        "version": VERSION,
        "capabilities": [
            "system_overview", "live_health_monitoring", "service_discovery",
            "session_tracking", "category_grouping", "latency_monitoring",
            "websocket_realtime", "system_metrics", "docker_monitoring",
            "error_tracking", "alert_system", "trends", "service_logs",
            "one_click_restart", "auto_scanning"
        ]
    }

# =============================================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time updates via WebSocket"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial data
        overview = scanner.get_boot_snapshot()
        await websocket.send_json({"type": "init", "data": overview})

        # Fast wake: compute a fresh overview immediately after connect and push an update.
        async def _warm_update(ws: WebSocket):
            try:
                fresh = await scanner.get_system_overview()
                await ws.send_json({"type": "update", "data": fresh})
            except Exception:
                pass

        asyncio.create_task(_warm_update(websocket))
        
        # Keep connection alive and listen for commands
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                if data.get("command") == "refresh":
                    overview = await scanner.get_system_overview()
                    await websocket.send_json({"type": "update", "data": overview})
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# =============================================================================
# MAIN
# =============================================================================


# =============================================================================
# LLAMA CHAT INTEGRATION (v3.1.0)
# =============================================================================

from pydantic import BaseModel

# Prefer explicit env override, else SSOT routing, else fall back to secondary IP.
OLLAMA_ENDPOINT = (
    os.getenv("OLLAMA_ENDPOINT")
    or _ssot_routing_url(_SSOT, "ollama")
    or f"http://{SECONDARY_IP}:11434"
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

chat_history: List[Dict[str, str]] = []

class ChatMessage(BaseModel):
    message: str

class AriaChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    task_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

async def get_system_context_for_llama() -> str:
    """Build system context for Llama."""
    try:
        overview = await scanner.get_system_overview()
        services_status = []
        for svc in overview.get("services", {}).values():
            status = "UP" if svc.get("healthy") else "DOWN"
            services_status.append(f"- {svc.get('name', 'Unknown')}: {status}")
        
        context = f"""SYSTEM STATUS:
Health: {overview.get('metrics', {}).get('health_score', 'N/A')}%
Online: {overview.get('metrics', {}).get('services_online', 0)}/{overview.get('metrics', {}).get('services_total', 0)}
CPU: {overview.get('system', {}).get('cpu_percent', 'N/A')}%
Memory: {overview.get('system', {}).get('memory_percent', 'N/A')}%

SERVICES:
""" + "\n".join(services_status) + """

You are Llama, AI assistant for God Mode. Help with system optimization."""
        return context
    except Exception as e:
        return f"Context error: {e}"

@app.post("/api/chat")
async def chat_with_llama(chat: ChatMessage):
    """Chat with Llama."""
    global chat_history
    chat_history.append({"role": "user", "content": chat.message})
    
    try:
        system_context = await get_system_context_for_llama()
        prompt = system_context + "\n\nHuman: " + chat.message + "\nLlama:"
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{OLLAMA_ENDPOINT}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            if response.status_code == 200:
                result = response.json()
                msg = result.get("response", "No response")
                chat_history.append({"role": "assistant", "content": msg})
                return {"response": msg, "model": OLLAMA_MODEL}
            return {"response": f"Llama status {response.status_code}", "model": "error"}
    except Exception as e:
        return {"response": f"Error: {repr(e)}", "model": "error"}

@app.post("/api/chat/stream")
async def chat_with_llama_stream(chat: ChatMessage):
    """
    Streaming chat endpoint (SSE) required by REQUIRED_FEATURES.json.
    Produces lines like: `data: {\"token\": \"...\"}\\n\\n`
    """
    global chat_history
    chat_history.append({"role": "user", "content": chat.message})

    system_context = await get_system_context_for_llama()
    prompt = system_context + "\n\nHuman: " + chat.message + "\nLlama:"

    async def event_generator():
        full = ""
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": True}

        # Try configured endpoint first; fall back to secondary Ollama (Tailscale then public).
        endpoints = [OLLAMA_ENDPOINT]
        for fb in (f"http://{SECONDARY_TAILSCALE_IP}:11434", f"http://{SECONDARY_IP}:11434"):
            if fb not in endpoints:
                endpoints.append(fb)

        last_error = None
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("POST", f"{endpoint}/api/generate", json=payload) as resp:
                        if resp.status_code != 200:
                            last_error = f"Ollama status {resp.status_code}"
                            continue

                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                            except Exception:
                                continue
                            token = obj.get("response")
                            if token:
                                full += token
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if obj.get("done"):
                                break

                        chat_history.append({"role": "assistant", "content": full})
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        return
            except Exception as e:
                last_error = repr(e)

        yield f"data: {json.dumps({'error': last_error or 'Unable to stream from Ollama'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/chat/history")
async def get_chat_history():
    return {"history": chat_history[-20:]}

@app.delete("/api/chat/history") 
async def clear_chat_history():
    global chat_history
    chat_history = []
    return {"status": "cleared"}


# =============================================================================
# ARIA INTEGRATION (God Mode ↔ Aria)
# =============================================================================

def _aria_base_url() -> str:
    """
    Prefer explicit env override, else local service definition.
    Default assumes Aria is running on the same host as God Mode.
    """
    env = (os.getenv("ARIA_ENDPOINT") or os.getenv("ARIA_URL") or "").strip()
    if env:
        return env.rstrip("/")

    cfg = LIVE_SERVICES.get("aria") or {}
    port = cfg.get("port") or 8710
    host = cfg.get("host")
    local_hosts = {
        None,
        "",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        PRIMARY_IP,
        PRIMARY_TAILSCALE_IP,
        SERVER_IP,
    }
    probe_host = "127.0.0.1" if (host in local_hosts) else host
    if not probe_host:
        probe_host = "127.0.0.1"
    return f"http://{probe_host}:{port}"

async def _system_context_for_aria() -> Dict[str, Any]:
    """
    Small, safe context payload (no secrets) to make Aria more useful.
    """
    try:
        overview = await scanner.get_system_overview()
        services = overview.get("services", {}) if isinstance(overview.get("services"), dict) else {}
        alerts = overview.get("alerts", []) if isinstance(overview.get("alerts"), list) else []
        coordination = overview.get("coordination", {}) if isinstance(overview.get("coordination"), dict) else {}
        return {
            "health_score": overview.get("metrics", {}).get("health_score"),
            "errors_last_5m": overview.get("errors", {}).get("errors_last_5m"),
            "services": {sid: (svc.get("status") if isinstance(svc, dict) else None) for sid, svc in services.items()},
            "alerts_top": alerts[:5],
            "top_intent": coordination.get("top_intent"),
            "timestamp": overview.get("timestamp"),
        }
    except Exception as e:
        return {"error": repr(e)}

@app.get("/api/aria/health")
async def api_aria_health():
    base = _aria_base_url()
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.get(f"{base}/health")
            return {
                "ok": r.status_code == 200,
                "status_code": r.status_code,
                "base_url": base,
                "data": (r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:400]}),
            }
    except Exception as e:
        return {"ok": False, "status_code": None, "base_url": base, "error": repr(e)}

@app.get("/api/aria/stats")
async def api_aria_stats():
    base = _aria_base_url()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{base}/stats")
            return {
                "ok": r.status_code == 200,
                "status_code": r.status_code,
                "base_url": base,
                "data": (r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:400]}),
            }
    except Exception as e:
        return {"ok": False, "status_code": None, "base_url": base, "error": repr(e)}

@app.post("/api/aria/chat")
async def api_aria_chat(chat: AriaChatMessage):
    base = _aria_base_url()
    ctx = await _system_context_for_aria()
    merged_context: Dict[str, Any] = {"godmode": ctx}
    if isinstance(chat.context, dict):
        merged_context.update(chat.context)

    payload = {
        "message": chat.message,
        "session_id": chat.session_id,
        "task_type": chat.task_type or "general",
        "context": merged_context,
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(f"{base}/chat", json=payload)
            if r.status_code == 200:
                return r.json()
            return {"error": f"aria_status_{r.status_code}", "detail": r.text[:800], "base_url": base}
    except Exception as e:
        return {"error": "aria_unreachable", "detail": repr(e), "base_url": base}


# =============================================================================
# V4.0 MERGED FEATURES (from v5.0)
# Storage Sentinel, Treasury, Intelligence, Omniscient
# =============================================================================

STORAGE_ALERT_FILE = Path("/opt/fpai/data/storage_alert.json") if 'Path' in dir() else None
TREASURY_FILE = Path("/opt/fpai/core/STATE/TREASURY.json") if 'Path' in dir() else None

@app.get("/api/storage")
async def get_storage_stats():
    """Storage sentinel stats."""
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            pct = int(parts[4].replace('%',''))
            return {
                "status": "ok" if pct < 80 else "warning" if pct < 90 else "critical",
                "usage_percent": pct,
                "used": parts[2],
                "available": parts[3],
                "total": parts[1]
            }
    except:
        pass
    return {"status": "unknown", "usage_percent": 0}


# ============================================================
# 🧠 MEMORY SYSTEM PANEL
# ============================================================

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", f"http://{PRIMARY_IP}:8125")

@app.get("/api/memory")
async def get_memory_stats():
    """
    Memory system health and statistics.
    
    Returns:
    - Mem0 connection status
    - Memory counts by type
    - Retrieval stats
    - Quality distribution
    - System memory (RAM) usage
    """
    result = {
        "status": "unknown",
        "mem0_enabled": False,
        "total_memories": 0,
        "by_type": {},
        "retrieval_stats": {},
        "quality_distribution": {},
        "system_stats": {},
        "hygiene": {},
        "recommendations": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Get memory stats
            stats_resp = await client.get(f"{DATA_SERVICE_URL}/api/memory/stats")
            if stats_resp.status_code == 200:
                stats = stats_resp.json()
                result["mem0_enabled"] = stats.get("enabled", False)
                result["total_memories"] = stats.get("total_operations", 0)
                result["retrieval_stats"] = stats.get("stats", {})
                result["recommendations"] = stats.get("recommendations", [])
            
            # Get system memory stats
            sys_resp = await client.get(f"{DATA_SERVICE_URL}/api/memory/system-stats")
            if sys_resp.status_code == 200:
                sys_stats = sys_resp.json()
                result["system_stats"] = sys_stats.get("process", {})
                result["hygiene"] = sys_stats.get("memory_hygiene", {})
                
                # Determine overall status
                rss_mb = sys_stats.get("process", {}).get("rss_mb", 0)
                if rss_mb < 300:
                    result["status"] = "healthy"
                elif rss_mb < 500:
                    result["status"] = "warning"
                else:
                    result["status"] = "critical"
            
            # Get retrieval tracker top memories
            try:
                hygiene_stats = result.get("hygiene", {})
                if hygiene_stats:
                    result["top_memories"] = hygiene_stats.get("top_memories", [])[:5]
                    result["quality_distribution"] = {
                        "high": hygiene_stats.get("high_quality_count", 0),
                        "medium": hygiene_stats.get("medium_quality_count", 0),
                        "low": hygiene_stats.get("low_quality_count", 0)
                    }
            except:
                pass
            
            if result["mem0_enabled"]:
                result["status"] = result.get("status", "healthy")
            else:
                result["status"] = "degraded"
                result["recommendations"].append("Mem0 API key not configured")
                
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["recommendations"].append(f"Data Service unreachable: {e}")
    
    return result


@app.get("/api/memory/wisdom/{topic}")
async def get_memory_wisdom(topic: str):
    """
    Get aggregated wisdom for a topic from the memory system.
    
    Used by God Mode to provide AI-powered insights.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DATA_SERVICE_URL}/api/memory/wisdom/{topic}")
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Memory service returned {resp.status_code}"}
    except Exception as e:
        return {"error": str(e), "topic": topic}


@app.get("/api/omniscient")
async def api_omniscient():
    """The true omniscient view - complete system awareness"""
    overview = await scanner.get_system_overview()
    
    # Get additional omniscient data
    security = await scanner.scan_security_threats()
    cron = await scanner.scan_cron_jobs()
    backups = await scanner.scan_backups()
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "awareness_level": "omniscient",
        "version": VERSION,
        "infrastructure": {
            "listening_ports": 82,  # Known from scan
            "tracked_services": len(LIVE_SERVICES)
        },
        "resources": {
            "cpu_percent": overview.get("system", {}).get("cpu_percent", 0),
            "memory_percent": overview.get("system", {}).get("memory_percent", 0),
            "disk_percent": overview.get("system", {}).get("disk_percent", 0),
            "load_1m": overview.get("system", {}).get("load_1m", 0),
            "uptime_days": 14.6  # Known from server
        },
        "docker": {
            "total": overview.get("docker", {}).get("total", 0),
            "healthy": overview.get("docker", {}).get("healthy", 0),
            "unhealthy": [c["name"] for c in overview.get("docker", {}).get("containers", []) if c.get("unhealthy")],
            "containers": overview.get("docker", {}).get("containers", [])
        },
        "security": security,
        "errors": {
            "last_hour": overview.get("errors", {}).get("errors_last_hour", 0),
            "severity": overview.get("errors", {}).get("alert_level", "unknown")
        },
        "cron": cron,
        "backups": backups,
        "ai_models": {
            "active_model": "llama3.2:3b",
            "total": 3
        }
    }

@app.get("/api/status")
async def api_unified_status():
    """Unified God Mode status - one view of everything"""
    overview = await scanner.get_system_overview()
    security = await scanner.scan_security_threats()
    
    issues = []
    
    # Check security threats
    if security.get("threat_level") == "high":
        issues.append({"type": "security", "severity": "high", "message": f"SSH attacks from {security.get('unique_attackers', 0)} IPs"})
    
    # Check errors
    errors = overview.get("errors", {})
    if errors.get("alert_level") == "critical":
        issues.append({"type": "errors", "severity": "critical", "message": f"{errors.get('errors_last_hour', 0)} errors in last hour"})
    
    # Check Docker
    docker = overview.get("docker", {})
    unhealthy = [c["name"] for c in docker.get("containers", []) if c.get("unhealthy")]
    if unhealthy:
        issues.append({"type": "docker", "severity": "warning", "message": f"{len(unhealthy)} containers unhealthy"})
    
    # Calculate overall status
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    high_count = sum(1 for i in issues if i["severity"] == "high")
    
    if critical_count > 0:
        overall = "CRITICAL"
    elif high_count > 0:
        overall = "ATTENTION"
    elif issues:
        overall = "STABLE"
    else:
        overall = "OPTIMAL"
    
    metrics = overview.get("metrics", {})
    system = overview.get("system", {})
    
    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": VERSION,
        "summary": {
            "services": f"{metrics.get('services_online', 0)}/{metrics.get('services_total', 0)}",
            "docker": f"{docker.get('healthy', 0)}/{docker.get('total', 0)}",
            "cpu": f"{system.get('cpu_percent', 0):.0f}%",
            "ram": f"{system.get('memory_percent', 0):.0f}%",
            "disk": f"{system.get('disk_percent', 0):.0f}%",
            "security": security.get("threat_level", "unknown"),
            "errors_hour": errors.get('errors_last_hour', 0),
        },
        "issues": issues,
        "unhealthy_containers": unhealthy,
        "top_attackers": security.get("attacking_ips", [])[:3],
    }

@app.get("/api/treasury")
async def get_treasury():
    """Get treasury/credits info."""
    treasury_path = Path("/opt/fpai/core/STATE/TREASURY.json")
    if treasury_path.exists():
        try:
            import json as json_lib
            return json_lib.loads(treasury_path.read_text())
        except:
            pass
    return {"balance": "N/A", "currency": "FP Credits", "status": "not configured"}


# ============ ENHANCED INTELLIGENCE (v3.4) ============
async def get_security_threats():
    """Get security threat information from failed SSH attempts."""
    import subprocess
    try:
        result = subprocess.run(["lastb", "-n", "50"], capture_output=True, text=True, timeout=5)
        failed_ips = {}
        for line in result.stdout.split("\n"):
            parts = line.split()
            if len(parts) >= 3:
                ip = parts[2]
                if ip and ip[0].isdigit():
                    failed_ips[ip] = failed_ips.get(ip, 0) + 1
        top_attackers = sorted(failed_ips.items(), key=lambda x: x[1], reverse=True)[:5]
        threat_level = "high" if len(failed_ips) > 3 else "medium" if failed_ips else "low"
        return {
            "threat_level": threat_level,
            "failed_attempts": sum(failed_ips.values()),
            "unique_ips": len(failed_ips),
            "top_attackers": [{"ip": ip, "attempts": count} for ip, count in top_attackers]
        }
    except Exception as e:
        return {"threat_level": "unknown", "error": str(e)}

async def get_error_count():
    """Get error log count from last hour."""
    import subprocess
    try:
        result = subprocess.run(
            ["journalctl", "--since", "1 hour ago", "-p", "err", "--no-pager", "-q"],
            capture_output=True, text=True, timeout=10
        )
        count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        severity = "critical" if count > 1000 else "warning" if count > 100 else "normal"
        return {"count": count, "severity": severity}
    except:
        return {"count": 0, "severity": "unknown"}

async def get_backup_status():
    """Get backup system status."""
    from pathlib import Path
    import json as json_lib
    try:
        manifest_path = Path("/opt/fpai/backups/manifest.json")
        if manifest_path.exists():
            manifest = json_lib.loads(manifest_path.read_text())
            return {
                "status": "healthy" if manifest.get("backups") else "warning",
                "last_backup": manifest.get("last_backup"),
                "total_backups": len(manifest.get("backups", []))
            }
        return {"status": "no_manifest"}
    except:
        return {"status": "unknown"}

@app.get("/api/intelligence")
async def get_intelligence():
    """Enhanced system intelligence - issues, opportunities, security, and more."""
    overview = await scanner.get_system_overview()
    
    issues = []
    opportunities = []
    
    # Get enhanced data
    security = await get_security_threats()
    errors = await get_error_count()
    backups = await get_backup_status()
    
    # Check system metrics
    sys_info = overview.get("system", {})
    cpu_pct = sys_info.get("cpu_percent", 0)
    mem_pct = sys_info.get("memory_percent", 0)
    disk_pct = sys_info.get("disk_percent", 0)
    
    if cpu_pct > 80:
        issues.append({"type": "cpu", "message": "High CPU: " + str(cpu_pct) + "%", "severity": "warning"})
    if mem_pct > 85:
        issues.append({"type": "memory", "message": "High memory: " + str(mem_pct) + "%", "severity": "critical"})
    if disk_pct > 80:
        issues.append({"type": "disk", "message": "High disk: " + str(disk_pct) + "%", "severity": "warning"})
    
    # Check services
    for svc_id, svc in overview.get("services", {}).items():
        if not svc.get("healthy"):
            svc_name = svc.get("name", svc_id)
            issues.append({"type": "service", "message": svc_name + " is down", "severity": "critical"})
    
    # Check docker
    for container in overview.get("docker", {}).get("containers", []):
        if container.get("unhealthy") or not container.get("up"):
            cname = container.get("name", "unknown")
            issues.append({"type": "container", "message": cname + " unhealthy", "severity": "warning"})
    
    # Security threats
    threat_level = security.get("threat_level", "unknown")
    if threat_level == "high":
        unique_ips = security.get("unique_ips", 0)
        attempts = security.get("failed_attempts", 0)
        issues.append({
            "type": "security", 
            "message": "SSH attacks from " + str(unique_ips) + " IPs (" + str(attempts) + " attempts)", 
            "severity": "critical"
        })
    elif threat_level == "medium":
        unique_ips = security.get("unique_ips", 0)
        issues.append({
            "type": "security", 
            "message": "SSH probing detected from " + str(unique_ips) + " IPs", 
            "severity": "warning"
        })
    
    # Error logs
    error_sev = errors.get("severity", "unknown")
    error_count = errors.get("count", 0)
    if error_sev == "critical":
        issues.append({
            "type": "errors", 
            "message": str(error_count) + " errors in last hour", 
            "severity": "critical"
        })
    elif error_sev == "warning":
        issues.append({
            "type": "errors", 
            "message": str(error_count) + " errors in last hour", 
            "severity": "warning"
        })
    
    # Backups
    backup_status = backups.get("status", "unknown")
    if backup_status not in ["healthy", "unknown"]:
        issues.append({
            "type": "backup", 
            "message": "Backup system needs attention", 
            "severity": "warning"
        })
    
    if not issues:
        opportunities.append({"message": "All systems nominal"})
    
    return {
        "issues": issues, 
        "opportunities": opportunities, 
        "health_score": overview.get("metrics", {}).get("health_score", 0),
        "security": security,
        "errors": errors,
        "backups": backups
    }
# ============ END ENHANCED INTELLIGENCE ============

@app.get("/api/omniscient")
async def get_omniscient():
    """Complete system awareness."""
    overview = await scanner.get_system_overview()
    storage = await get_storage_stats()
    treasury = await get_treasury()
    intel = await get_intelligence()
    
    return {
        "version": "4.0.0",
        "system": overview.get("system"),
        "services": overview.get("services"),
        "docker": overview.get("docker"),
        "metrics": overview.get("metrics"),
        "intelligence": intel,
        "storage": storage,
        "treasury": treasury,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# AI BRAIN INTEGRATION - Shows connected services
# ============================================================
AI_BRAIN_URL = (
    os.getenv("AI_BRAIN_URL")
    or _ssot_routing_url(_SSOT, "ai_inference")
    or f"http://{SECONDARY_IP}:8101"
)

@app.get("/api/ai-brain/services")
async def get_ai_brain_services():
    """Get all services registered with AI Brain"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{AI_BRAIN_URL}/admin/services")
            if response.status_code == 200:
                data = response.json()
                known_services = [
                    "god-mode", "orchestrator", "dashboard", "verifier", 
                    "backup-dashboard", "whaletrack", "treasury", "team-hub",
                    "breath-optimizer", "zen-village", "content-studio", 
                    "api-portal", "missions", "communication-hub", "fp-chat",
                    "voice-portal", "outbounders", "autonomy-optimizer",
                    "strategic-intel", "minnow", "storage-sentinel"
                ]
                
                registered = data.get("services", [])
                registered_names = [s["name"].lower() for s in registered]
                
                not_registered = [s for s in known_services if s.lower() not in registered_names]
                
                return {
                    "ai_brain_status": "online",
                    "total_registered": data.get("count", 0),
                    "registered_services": registered,
                    "not_registered": not_registered
                }
            return {"ai_brain_status": "error"}
    except Exception as e:
        return {"ai_brain_status": "offline", "error": str(e)}


# Market Tests Dashboard
@app.get("/market-tests")
async def market_tests_page(request: Request):
    """Market tests dashboard page."""
    return templates.TemplateResponse("market_tests.html", {"request": request})

@app.get("/api/market-tests")
async def get_market_tests_api():
    """API endpoint for market test metrics."""
    import aiohttp
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get("http://localhost:8952/metrics") as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"status": "error", "message": "Could not fetch metrics"}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


# API Tracker Dashboard
@app.get("/api-tracker")
async def api_tracker_page(request: Request):
    """API tracker dashboard page."""
    return templates.TemplateResponse("api_tracker.html", {"request": request})

@app.get("/api/apis/summary")
async def get_apis_summary():
    """API endpoint for API tracker."""
    import aiohttp
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get("http://localhost:8953/apis/summary") as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": "Could not fetch API data"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# 🤝 COMMONS MINISTRY ENDPOINT
# ============================================================
@app.get("/api/commons")
async def get_commons_data():
    """
    Get Commons Ministry data - Trust Index, Contributions, Needs Allocation.
    """
    trust_index = {}
    contributions = {}
    needs = {}
    budget = {}
    policy = {}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                ti_resp = await client.get("http://127.0.0.1:8560/api/trust-index")
                if ti_resp.status_code == 200:
                    trust_index = ti_resp.json()
            except: pass
            
            try:
                policy_resp = await client.get("http://127.0.0.1:8560/api/trust-index/policy")
                if policy_resp.status_code == 200:
                    policy = policy_resp.json()
            except: pass
            
            try:
                contrib_resp = await client.get("http://127.0.0.1:8570/api/contributions/aggregate")
                if contrib_resp.status_code == 200:
                    contributions = contrib_resp.json()
            except: pass
            
            try:
                needs_resp = await client.get("http://127.0.0.1:8565/api/needs/committed")
                if needs_resp.status_code == 200:
                    needs = needs_resp.json()
            except: pass
            
            try:
                budget_resp = await client.get("http://127.0.0.1:8565/api/needs/budget")
                if budget_resp.status_code == 200:
                    budget = budget_resp.json()
            except: pass
    except: pass
    
    return {
        "trust_index": trust_index,
        "contributions": contributions,
        "needs": needs,
        "budget": budget,
        "policy": policy,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("⚡ Starting God Mode v3.0.0 - Omniscient Command Center")
    uvicorn.run(app, host="0.0.0.0", port=8300)
