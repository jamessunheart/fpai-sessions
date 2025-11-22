"""
FastAPI application initialization
UDC v1.0 Compliant Multi-Cloud Manager
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logging import log, log_event
from app.services.registry import register_with_registry, heartbeat_task
from app.services.jwt_service import startup_fetch_jwks, fetch_registry_jwt_token

# Import UDC Core routers (these export 'router' objects)
from app.api.routes.health import router as health_router
from app.api.routes.capabilities import router as capabilities_router
from app.api.routes.state_router import router as state_router
from app.api.routes.dependencies import router as dependencies_router
from app.api.routes.message import router as message_router
from app.api.routes.send import router as send_router

# Import UDC Extended routers (these are APIRouter objects directly)
from app.api.routes.extended import version, metrics, logs, events, proof
from app.api.routes.shutdown import shutdown, reload_config, emergency_stop

# Import cloud provider routers (these export 'router' objects)
from app.api.routes import do_routes, hetzner_routes, vultr_routes, multi_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    log.info(
        "droplet_startup",
        droplet_id=settings.droplet_id,
        version=settings.version,
        udc_version=settings.udc_version
    )
    log_event("droplet_startup", {
        "version": settings.version,
        "udc_version": settings.udc_version,
        "droplet_name": settings.droplet_name
    })
    
    # Test outgoing JWT authentication (RS256)
    log.info("jwt_test", message="Testing Registry v2 JWT authentication (RS256)...")
    token = await fetch_registry_jwt_token()
    if token:
        log.info("jwt_test_success", message="RS256 JWT authentication working")
    else:
        log.error("jwt_test_failed", message="RS256 JWT authentication failed")
    
    # Fetch JWKS for incoming token verification
    await startup_fetch_jwks()
    
    # Register with Registry v2
    await register_with_registry()
    
    # Start heartbeat task
    heartbeat = asyncio.create_task(heartbeat_task())
    
    yield
    
    # Shutdown
    heartbeat.cancel()
    log_event("droplet_shutdown", {"graceful": True})
    log.info(
        "droplet_shutdown",
        droplet_id=settings.droplet_id,
        message="Shutting down gracefully"
    )


# Initialize FastAPI app
app = FastAPI(
    title="Multi-Cloud Droplet Manager",
    version=settings.version,
    lifespan=lifespan,
    description="UDC v1.0 Compliant Multi-Cloud Management System with JWT JWKS"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# UDC v1.0 REQUIRED ENDPOINTS
# ============================================================================

# Core UDC endpoints
app.include_router(health_router, tags=["UDC Core"])
app.include_router(capabilities_router, tags=["UDC Core"])
app.include_router(state_router, tags=["UDC Core"])
app.include_router(dependencies_router, tags=["UDC Core"])
app.include_router(message_router, tags=["UDC Core"])
app.include_router(send_router, tags=["UDC Core"])

# UDC Extended endpoints
app.include_router(version, tags=["UDC Extended"])
app.include_router(metrics, tags=["UDC Extended"])
app.include_router(logs, tags=["UDC Extended"])
app.include_router(events, tags=["UDC Extended"])
app.include_router(proof, tags=["UDC Extended"])
app.include_router(reload_config, tags=["UDC Extended"])
app.include_router(shutdown, tags=["UDC Extended"])
app.include_router(emergency_stop, tags=["UDC Extended"])

# ============================================================================
# CLOUD PROVIDER ENDPOINTS
# ============================================================================

app.include_router(do_routes.router, prefix="/do", tags=["DigitalOcean"])
app.include_router(hetzner_routes.router, prefix="/hetzner", tags=["Hetzner"])
app.include_router(vultr_routes.router, prefix="/vultr", tags=["Vultr"])
app.include_router(multi_routes.router, prefix="/multi", tags=["Multi-Cloud"])
