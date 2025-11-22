from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .utils.logging import configure_logging, get_logger
from .utils.metrics import metrics
from .services.registry import RegistryService
from .services.orchestrator import OrchestratorService
from .services.auth_manager import auth_manager
from .services.heartbeat import heartbeat_service
from .api.routes import health_router, message_router, management_router, emergency_router, airtable_router

# Configure logging
configure_logging()
log = get_logger(__name__)

# Services
registry_service = RegistryService()
orchestrator_service = OrchestratorService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    log.info(
        f"Droplet starting - ID: {settings.droplet_id}, Name: {settings.droplet_name}, Environment: {settings.environment}"
    )
    
    # Start auth manager (auto-registration and token refresh)
    try:
        await auth_manager.start()
        log.info("Auth manager started successfully")
    except Exception as e:
        log.error(f"Auth manager startup failed: {str(e)}")
    
    # Start heartbeat service
    try:
        import asyncio
        asyncio.create_task(heartbeat_service.start())
        log.info("Heartbeat service started")
    except Exception as e:
        log.error(f"Heartbeat service failed: {str(e)}")
    
    yield
    
    # Shutdown
    log.info("Droplet shutting down")
    await auth_manager.stop()
    await orchestrator_service.stop_heartbeat()


# Create FastAPI app
app = FastAPI(
    title=f"Droplet #{settings.droplet_id} - {settings.droplet_name}",
    description="UDC-compliant droplet server",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://dashboard.fullpotential.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track requests and errors for metrics"""
    metrics.increment_requests()
    
    response = await call_next(request)
    
    if response.status_code >= 400:
        metrics.increment_errors()
    
    return response


# Include routers
app.include_router(health_router)
app.include_router(message_router)
app.include_router(management_router)
app.include_router(emergency_router)
app.include_router(airtable_router)


@app.get("/")
async def root():
    """Root endpoint with droplet info"""
    return {
        "droplet_id": settings.droplet_id,
        "name": settings.droplet_name,
        "steward": settings.droplet_steward,
        "status": "active",
        "udc_version": "1.0",
        "docs": "/docs"
    }