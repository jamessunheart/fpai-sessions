"""
Orchestrator FastAPI Application
Main application initialization and lifecycle management

Droplet #10: Orchestrator
Version: 2.0.0
Steward: Tnsae
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from time import time
import structlog

from app.config import settings
from app.database import init_db, close_db, verify_database_schema
from app.utils.logging import configure_logging, log_api_request, log_error
from app.services.registry_client import registry_client, sync_droplets_from_registry
from app.services.health_monitor import check_droplet_health, cleanup_old_heartbeats
from app.services.task_router import route_pending_tasks
from app.services.websocket_manager import websocket_manager
# ============================================================================
# INITIALIZE LOGGING
# ============================================================================
configure_logging()
log = structlog.get_logger()

# ============================================================================
# INITIALIZE SCHEDULER
# ============================================================================
scheduler = AsyncIOScheduler()


# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles all startup and shutdown tasks
    """
    # ========================================================================
    # STARTUP SEQUENCE
    # ========================================================================
    log.info(
        "orchestrator_starting",
        version=settings.app_version,
        environment=settings.environment,
        droplet_id=settings.droplet_id,
        endpoint=settings.droplet_endpoint
    )
    
    # ------------------------------------------------------------------------
    # Step 1: Initialize Database
    # ------------------------------------------------------------------------
    try:
        log.info("initializing_database")
        await init_db()
        
        # Verify schema
        schema_valid = await verify_database_schema()
        if not schema_valid:
            log.error("database_schema_invalid")
            raise RuntimeError("Database schema verification failed. Run schema.sql first.")
        
        log.info("database_initialized")
        
    except Exception as e:
        log.error("database_initialization_failed", error=str(e))
        raise RuntimeError(f"Database initialization failed: {str(e)}")
    
    # ------------------------------------------------------------------------
    # Step 2: Register with Registry
    # ------------------------------------------------------------------------
    try:
        log.info("registering_with_registry", registry_url=settings.registry_url)
        await registry_client.register_self()
        log.info("registry_registration_successful")
    except Exception as e:
        log.warning(
            "registry_registration_failed",
            error=str(e),
            note="Continuing without Registry (degraded mode)"
        )
    
    # ------------------------------------------------------------------------
    # Step 3: Start Background Scheduler
    # ------------------------------------------------------------------------
    try:
        log.info("starting_background_scheduler")
        
        # Job 1: Health Monitor - Check droplet heartbeats every 60 seconds
        scheduler.add_job(
            check_droplet_health,
            'interval',
            seconds=settings.heartbeat_check_interval,
            id='health_monitor',
            name='Droplet Health Monitor',
            max_instances=1,
            coalesce=True
        )
        log.debug("scheduled_health_monitor", interval_seconds=settings.heartbeat_check_interval)
        
        # Job 2: Task Router - Route pending tasks every 10 seconds
        scheduler.add_job(
            route_pending_tasks,
            'interval',
            seconds=10,
            id='task_router',
            name='Task Router',
            max_instances=1,
            coalesce=True
        )
        log.debug("scheduled_task_router", interval_seconds=10)
        
        # Job 3: Registry Sync - Sync droplet directory every 5 minutes
        scheduler.add_job(
            sync_droplets_from_registry,
            'interval',
            seconds=settings.registry_sync_interval,
            id='registry_sync',
            name='Registry Sync',
            max_instances=1,
            coalesce=True
        )
        log.debug("scheduled_registry_sync", interval_seconds=settings.registry_sync_interval)
        
        # Job 4: Heartbeat Cleanup - Remove old heartbeats every hour
        scheduler.add_job(
            cleanup_old_heartbeats,
            'interval',
            hours=1,
            id='heartbeat_cleanup',
            name='Heartbeat Cleanup',
            max_instances=1,
            coalesce=True
        )
        log.debug("scheduled_heartbeat_cleanup", interval_hours=1)
        
        # Job 5: WebSocket Ping - Keep connections alive every 30 seconds
        scheduler.add_job(
            websocket_manager.ping_all_connections,
            'interval',
            seconds=settings.ws_heartbeat_interval,
            id='websocket_ping',
            name='WebSocket Ping',
            max_instances=1,
            coalesce=True
        )
        log.debug("scheduled_websocket_ping", interval_seconds=settings.ws_heartbeat_interval)
        
        # Start the scheduler
        scheduler.start()
        log.info("background_scheduler_started", total_jobs=len(scheduler.get_jobs()))
        
    except Exception as e:
        log.error("scheduler_initialization_failed", error=str(e))
        raise RuntimeError(f"Scheduler initialization failed: {str(e)}")
    
    # ------------------------------------------------------------------------
    # Startup Complete
    # ------------------------------------------------------------------------
    log.info(
        "orchestrator_ready",
        status="operational",
        endpoint=settings.droplet_endpoint,
        database_connected=True,
        scheduler_running=True,
        scheduled_jobs=len(scheduler.get_jobs())
    )
    
    # Application is now running - yield control
    yield
    
    # ========================================================================
    # SHUTDOWN SEQUENCE
    # ========================================================================
    log.info("orchestrator_shutting_down")
    
    # Stop scheduler
    if scheduler.running:
        log.info("stopping_scheduler")
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
    
    # Close Registry client
    log.info("closing_registry_client")
    await registry_client.close()
    
    # Close database connections
    log.info("closing_database_connections")
    await close_db()
    
    log.info("orchestrator_shutdown_complete")


# ============================================================================
# CREATE FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Orchestrator",
    description="Central task coordination and workflow management for Full Potential AI droplet mesh",
    version=settings.app_version,
    docs_url="/docs" if settings.enable_swagger else None,
    redoc_url="/redoc" if settings.enable_swagger else None,
    lifespan=lifespan
)


# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing and trace IDs"""
    start_time = time()
    
    # Get or generate trace ID
    trace_id = request.headers.get("X-Trace-ID")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time() - start_time) * 1000
    
    # Add trace ID to response headers
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    
    # Log request (skip health checks in production to reduce noise)
    if not (settings.is_production and request.url.path == "/health"):
        log_api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
            trace_id=trace_id
        )
    
    return response


# ============================================================================
# ROUTE REGISTRATION
# ============================================================================

# Import route modules
from app.api.routes import health, tasks, droplets, websocket, metrics, message, auth, management


# UDC endpoints (public - no authentication required)
app.include_router(
    health.router,
    tags=["UDC"]
)

app.include_router(
    message.router,
    tags=["UDC"]
)

# Task management endpoints (JWT authentication required)
app.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["Tasks"]
)

# Droplet management endpoints (JWT authentication required)
app.include_router(
    droplets.router,
    prefix="/droplets",
    tags=["Droplets"]
)

# WebSocket endpoints (JWT authentication required)
app.include_router(
    websocket.router,
    prefix="/ws",
    tags=["WebSocket"]
)

# Metrics and analytics endpoints (JWT authentication required)
app.include_router(
    metrics.router,
    prefix="/metrics",
    tags=["Metrics"]
)

app.include_router(
    management.router,
    prefix="/management",
    tags=["Management"]
)



# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint - redirects to health check
    """
    return RedirectResponse(url="/health")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 Not Found errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "message": f"Endpoint not found: {request.url.path}",
            "type": "NotFound"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors
    Logs the error and returns a generic error response
    """
    log_error(
        exc,
        context="unhandled_exception",
        path=request.url.path,
        method=request.method
    )
    
    # Don't expose internal error details in production
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "type": "InternalServerError"
            }
        )
    else:
        # In development, include error details
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": str(exc),
                "type": type(exc).__name__
            }
        )


# ============================================================================
# APPLICATION STARTUP (for direct execution)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    log.info(
        "starting_uvicorn_server",
        host=settings.host,
        port=settings.port,
        workers=1 if settings.reload else settings.workers,
        reload=settings.reload
    )
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=False  # We handle logging in middleware
    )