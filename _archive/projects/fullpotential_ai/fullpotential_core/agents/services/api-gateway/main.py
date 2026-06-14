"""
Unified API Gateway - Single Entry Point for All 64 Services
Routes requests to appropriate services based on catalog
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FPAI Unified API Gateway",
    description="Single entry point for all 64 services in the FPAI mesh",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service catalog
CATALOG_PATH = Path("/Users/jamessunheart/Development/agents/services/SERVICE_CATALOG.json")
SERVICE_CACHE = {}
CACHE_TTL = 60  # Reload catalog every 60 seconds


def load_service_catalog():
    """Load and cache service catalog"""
    global SERVICE_CACHE

    try:
        with open(CATALOG_PATH) as f:
            catalog = json.load(f)

        # Build service lookup
        SERVICE_CACHE = {
            'services': {},
            'loaded_at': datetime.utcnow(),
            'total': 0
        }

        for service in catalog['services']:
            if service.get('port'):
                SERVICE_CACHE['services'][service['name']] = {
                    'port': service['port'],
                    'status': service['status'],
                    'url': f"http://localhost:{service['port']}",
                    'capabilities': service.get('capabilities', []),
                    'description': service.get('description', '')
                }

        SERVICE_CACHE['total'] = len(SERVICE_CACHE['services'])
        logger.info(f"Loaded {SERVICE_CACHE['total']} services from catalog")

    except Exception as e:
        logger.error(f"Failed to load catalog: {e}")


def get_service(service_name: str) -> Optional[dict]:
    """Get service info from cache, reload if stale"""
    # Reload if cache is stale
    if not SERVICE_CACHE or \
       (datetime.utcnow() - SERVICE_CACHE.get('loaded_at', datetime.min)).total_seconds() > CACHE_TTL:
        load_service_catalog()

    return SERVICE_CACHE.get('services', {}).get(service_name)


@app.on_event("startup")
async def startup():
    """Load catalog on startup"""
    load_service_catalog()
    logger.info("🌐 Unified API Gateway started")


# ==================== GATEWAY ENDPOINTS ====================

@app.get("/")
async def root():
    """Gateway info"""
    return {
        "gateway": "fpai-unified-api-gateway",
        "version": "1.0.0",
        "services_available": SERVICE_CACHE.get('total', 0),
        "catalog_updated": SERVICE_CACHE.get('loaded_at'),
        "usage": {
            "route_to_service": "/api/{service_name}/{path}",
            "list_services": "/services",
            "service_info": "/services/{service_name}",
            "health_check": "/health"
        }
    }


@app.get("/health")
async def health():
    """Gateway health"""
    return {
        "status": "active",
        "service": "api-gateway",
        "version": "1.0.0",
        "services_loaded": SERVICE_CACHE.get('total', 0),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/services")
async def list_services():
    """List all available services"""
    services = SERVICE_CACHE.get('services', {})

    return {
        "total": len(services),
        "services": [
            {
                "name": name,
                "url": info['url'],
                "status": info['status'],
                "capabilities": info['capabilities'][:3],  # First 3
                "description": info['description'][:100] if info['description'] else None
            }
            for name, info in services.items()
        ]
    }


@app.get("/services/{service_name}")
async def get_service_info(service_name: str):
    """Get detailed service info"""
    service = get_service(service_name)

    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    return {
        "name": service_name,
        **service,
        "gateway_route": f"/api/{service_name}"
    }


@app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_service(service_name: str, path: str, request: Request):
    """
    Proxy requests to services
    Example: /api/nexus-event-bus/health -> http://localhost:8450/health
    """
    service = get_service(service_name)

    if not service:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found. Use /services to see available services."
        )

    # Check if service is online
    if service['status'] != 'online':
        raise HTTPException(
            status_code=503,
            detail=f"Service '{service_name}' is currently {service['status']}"
        )

    # Build target URL
    target_url = f"{service['url']}/{path}"

    # Get request body
    body = await request.body()

    # Proxy the request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=body,
                params=dict(request.query_params)
            )

            logger.info(f"Proxied: {request.method} {service_name}/{path} -> {response.status_code}")

            return JSONResponse(
                content=response.json() if response.headers.get('content-type', '').startswith('application/json') else {"response": response.text},
                status_code=response.status_code
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Service '{service_name}' timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Service '{service_name}' unreachable")
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reload")
async def reload_catalog():
    """Manually reload service catalog"""
    load_service_catalog()
    return {
        "status": "reloaded",
        "services": SERVICE_CACHE.get('total', 0),
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== SERVICE DISCOVERY HELPERS ====================

@app.get("/discover/by-capability/{capability}")
async def discover_by_capability(capability: str):
    """Find services by capability"""
    services = SERVICE_CACHE.get('services', {})

    matches = [
        {
            "name": name,
            "url": f"/api/{name}",
            "status": info['status'],
            "capabilities": info['capabilities']
        }
        for name, info in services.items()
        if capability.lower() in [c.lower() for c in info['capabilities']]
    ]

    return {
        "capability": capability,
        "matches": len(matches),
        "services": matches
    }


@app.get("/discover/online")
async def discover_online():
    """List only online services"""
    services = SERVICE_CACHE.get('services', {})

    online = [
        {
            "name": name,
            "url": f"/api/{name}",
            "port": info['port']
        }
        for name, info in services.items()
        if info['status'] == 'online'
    ]

    return {
        "total_online": len(online),
        "services": online
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8891)
