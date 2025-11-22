"""
Chat Orchestrator Droplet 12 - Main Application
Per TECH_STACK.md and UDC_COMPLIANCE.md
"""
from jose import jwt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import httpx
from datetime import datetime
import uuid
import sys
import platform

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from datetime import datetime, timedelta
from app.services.memory import SESSION_MANAGER
from app.models.udc import ErrorResponse
from app.globals import request_counter
from app.services.orchestrator import orchestrator_client

# Setup logging first
setup_logging(settings.log_level)
log = get_logger(__name__)

# Fix console encoding for Windows
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Startup/shutdown state
startup_time = datetime.utcnow()


async def authenticate_with_orchestrator():
    """
    Generate a JWT token on startup.
    This replaces the previous method of fetching from Orchestrator #10.
    """
    try:
        print("Generating JWT token...")
        with open("private_key.pem", "r") as f:
            private_key = f.read()

            payload = { "droplet_id": 12,  "steward": "Zainab", "permissions": ["read", "write"], "iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(hours=24)}

            token = jwt.encode(payload, private_key, algorithm="RS256")
         
            settings.set_orchestrator_jwt(token)
            log.info("orchestrator_authentication_success", method="local_generation")
    except Exception as e:
        log.error("orchestrator_auth_failed", reason=str(e))
        raise RuntimeError(f"Failed to generate JWT token: {e}")


async def authenticate_and_set_jwt_key():
    """
    Authenticate with drop18 and set JWT_KEY in environment.
    This function runs automatically when users login.
    """
    auth_url = "https://drop18.fullpotential.ai/auth/token"
    registry_key = settings.get_droplet_secret()
    droplet_id = int(settings.id)
    
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{auth_url}?droplet_id={droplet_id}",
                    headers={
                        "X-Registry-Key": registry_key
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    token = result.get("token")
                    if token:
                        settings.set_jwt_key(token)
                        log.info("jwt_key_authentication_success", auth_url=auth_url)
                        return token
                    else:
                        log.error("jwt_key_auth_failed", reason="No token in response", response=result)
                else:
                    log.warning(
                        "jwt_key_auth_failed",
                        status_code=response.status_code,
                        response=response.text,
                        attempt=attempt + 1
                    )
        
        except Exception as e:
            log.error(
                "jwt_key_auth_unreachable",
                error=str(e),
                attempt=attempt + 1,
            )
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
    
    raise RuntimeError("Failed to authenticate and set JWT_KEY after multiple attempts")


async def register_with_orchestrator():
    """
    Register this droplet with Orchestrator #10 on startup.
    Per the new UDC API reference.
    """
    registration_url = f"{settings.orchestrator_url}/droplets/register"
    
    # Using the DropletRegister model we defined earlier
    from app.models.udc import DropletRegister
    droplet_data = DropletRegister(
        droplet_id=int(settings.id),
        name=settings.droplet_name,
        endpoint=settings.droplet_url,
        steward=settings.droplet_steward,
        capabilities=[
            "natural_language_understanding",
            "conversation_memory",
            "websocket_support",
            "multi_source_messaging"
        ]
    )

    # UDC envelope using the flat structure from the docs
    udc_payload = {
        "message_type": "command",
        "payload": droplet_data.dict(),
        "source": f"droplet-{settings.id}",
        "target": "droplet-10",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": str(uuid.uuid4()),
        "udc_version": "1.0"
    }

    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=settings.orchestrator_timeout) as client:
                response = await client.post(
                    registration_url,
                    json=udc_payload,
                    headers={"Authorization": f"Bearer {settings.get_orchestrator_jwt()}"}
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    log.info("orchestrator_registration_success", orchestrator_url=settings.orchestrator_url)
                    return
                else:
                    log.warning(
                        "orchestrator_registration_failed",
                        status_code=response.status_code,
                        response=response.text,
                        attempt=attempt + 1
                    )

        except Exception as e:
            log.error(
                "orchestrator_registration_unreachable",
                error=str(e),
                attempt=attempt + 1,
            )
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay *= 2

    raise RuntimeError("Failed to register with Orchestrator #10 after multiple attempts")


async def register_with_registry():
    """
    Register this droplet with Registry on startup.
    Per INTEGRATION_GUIDE.md - REQUIRED for all droplets.
    """
    registration_data = {
        "id": settings.id,
        "droplet_id": settings.droplet_id,
        "name": settings.droplet_name,
        "steward": settings.droplet_steward,
        "status": "active",
        "endpoint": settings.droplet_url,
        "host": "drop12.fullpotential.ai"
    }
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=settings.registry_timeout) as client:
                response = await client.post(
                    f"{settings.registry_url}/registry/register",
                    json=registration_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.jwt_key.get_secret_value()}",
                        "X-Registry-Key": settings.droplet_secret.get_secret_value()
                    },
                )
           
                result = response.json()
                print(f"\n[REGISTRY] Registration response: {result}\n")
                
                if response.status_code == 200:
                    log.info(
                        "registry_registration_success",
                        droplet_id=settings.droplet_id,
                        response=result
                    )
                    return result
                else:
                    print(f"[WARNING] Registry registration failed: {response.status_code} - {result}")
                    log.warning(
                        "registry_registration_failed",
                        status_code=response.status_code,
                        response=result,
                        attempt=attempt + 1
                    )
                    
        except Exception as e:
            print(f"[ERROR] Registry unreachable: {str(e)}")
            log.error(
                "registry_unreachable",
                error=str(e),
                attempt=attempt + 1
            )
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
    
    if settings.environment == "production":
        raise RuntimeError("Failed to register with Registry after multiple attempts")
    
    log.warning("registry_registration_skipped", environment=settings.environment)


async def send_heartbeat():
    """
    Send regular heartbeat to Orchestrator.
    Per INTEGRATION_GUIDE.md - REQUIRED every 60 seconds.
    """
    import psutil
    
    while True:
        try:
            # Gather metrics
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            status_data = {
                "message_type": "command",
                "payload": {
                    "metrics": {
                        "cpu_percent": cpu_percent,
                        "memory_mb": int(memory_mb),
                        "active_sessions": SESSION_MANAGER.get_session_count(),
                        "requests_total": request_counter["total"],
                        "errors_last_hour": request_counter["errors"]
                    },
                    "status": "active"
                },
                "source": "droplet-12",
                "target": "droplet-10",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "trace_id": str(uuid.uuid4()),
                "udc_version": "1.0"
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{settings.orchestrator_url}/droplets/{settings.id}/heartbeat",
                    json=status_data,
                    headers={
                        "Authorization": f"Bearer {settings.get_orchestrator_jwt()}"
                    }
                )
                
                if response.status_code == 200:
                    heart = "💓" if platform.system() != "Windows" else "<3"
                    print(f"{heart} Orchestrator heartbeat - CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f}MB")
                    log.debug("heartbeat_sent", metrics=status_data["payload"]["metrics"])
                else:
                    print(f"[WARNING] Orchestrator heartbeat failed: {response.status_code}")
                
        except Exception as e:
            print(f"[ERROR] Orchestrator heartbeat error: {str(e)}")
            log.error("heartbeat_failed", error=str(e))
        
        await asyncio.sleep(60)  # Every 60 seconds per INTEGRATION_GUIDE.md


async def send_registry_heartbeat():
    """
    Send regular heartbeat to Registry.
    Per registry API requirements - sends metrics and status.
    """
    import psutil
    
    while True:
        try:
            # Gather metrics
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            uptime_seconds = int((datetime.utcnow() - startup_time).total_seconds())
            
            heartbeat_data = {
                "droplet_id": settings.droplet_id,
                "metadata": {
                    "name": settings.droplet_name,
                    "steward": settings.droplet_steward,
                    "version": "1.0.0",
                    "udc_version": "1.0",
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_mb": round(memory_mb, 1),
                    "uptime_seconds": uptime_seconds
                }
            }
            
            async with httpx.AsyncClient(timeout=settings.registry_timeout) as client:
                response = await client.post(
                    f"{settings.registry_url}/registry/heartbeat",
                    json=heartbeat_data,
                    headers={
                        "Authorization": f"Bearer {settings.jwt_key.get_secret_value()}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    heart = "💓" if platform.system() != "Windows" else "<3"
                    print(f"{heart} Registry heartbeat - CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f}MB")
                    log.debug("registry_heartbeat_sent", metrics=heartbeat_data["metadata"])
                else:
                    print(f"[WARNING] Registry heartbeat failed: {response.status_code}")
                    log.warning(
                        "registry_heartbeat_failed",
                        status_code=response.status_code,
                        response=response.text
                    )
                
        except Exception as e:
            print(f"[ERROR] Registry heartbeat error: {str(e)}")
            log.error("registry_heartbeat_error", error=str(e))
        
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    Per INTEGRATION_GUIDE.md - register on startup, deregister on shutdown.
    """
    # Startup
    is_windows = platform.system() == "Windows"
    rocket = "🚀" if not is_windows else ">>>"
    check = "✅" if not is_windows else "[OK]"
    
    print(f"\n{rocket} Starting {settings.droplet_name} (ID: {settings.droplet_id})")
    print(f"Environment: {settings.environment}")
    print(f"Registry: {settings.registry_url}")
    print(f"Orchestrator: {settings.orchestrator_url}\n")
    
    log.info(
        "droplet_starting",
        droplet_id=settings.droplet_id,
        droplet_name=settings.droplet_name,
        environment=settings.environment
    )
    
    # Authenticate with Orchestrator #10
    try:
        check = "✅" if not is_windows else "[OK]"
        print("[AUTH] Authenticating with Orchestrator...")

        await authenticate_with_orchestrator()
        print(f"{check} Orchestrator authentication successful\n")
    except Exception as e:
        print(f"[ERROR] Orchestrator authentication failed: {str(e)}\n")
        log.critical("startup_orchestrator_auth_failed", error=str(e))
        if settings.environment == "production":
            raise
    # Generate Registry JWT Key
    try:
        check = "✅" if not is_windows else "[OK]"
        print("Generate Registry JWT Key...")
        await authenticate_and_set_jwt_key()
        print(f"{check} Registry JWT Key generated\n")
    except Exception as e:
        print(f"[ERROR] Registry JWT Key generation failed: {str(e)}\n")
        log.error("startup_registry_jwt_key_generation_failed", error=str(e))
    # Register with Registry
    try:
        print("[REGISTRY] Registering with Registry...")
        await register_with_registry()
    except Exception as e:
        print(f"[ERROR] Registry registration failed: {str(e)}\n")
        log.error("startup_registration_failed", error=str(e))
        if settings.environment == "production":
            raise
    
    # Register with Orchestrator #10
    try:
        check = "✅" if not is_windows else "[OK]"
        print("[ORCHESTRATOR] Registering with Orchestrator...")
        await register_with_orchestrator()
        print(f"{check} Orchestrator registration successful\n")
    except Exception as e:
        print(f"[ERROR] Orchestrator registration failed: {str(e)}\n")
        log.critical("startup_orchestrator_registration_failed", error=str(e))
        if settings.environment == "production":
            raise

    # Start heartbeat tasks
    heartbeat_task = asyncio.create_task(send_heartbeat())
    registry_heartbeat_task = asyncio.create_task(send_registry_heartbeat())
    
    check = "✅" if not is_windows else "[OK]"
    print(f"\n{check} {settings.droplet_name} started on port {settings.port}")
    print(f"API Docs: http://localhost:{settings.port}/docs\n")
    
    log.info("droplet_started", port=settings.port)
    
    yield
    
    # Shutdown
    log.info("droplet_shutting_down", droplet_id=settings.droplet_id)
    
    # Cancel heartbeat tasks
    heartbeat_task.cancel()
    registry_heartbeat_task.cancel()
    
    # Deregister from Registry
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.registry_url}/deregister",
                json={
                    "id": settings.droplet_id,
                    "reason": "graceful_shutdown"
                }
            )
        log.info("registry_deregistration_success")
    except Exception as e:
        log.error("registry_deregistration_failed", error=str(e))


# Initialize FastAPI app
app = FastAPI(
    title="Chat Orchestrator Droplet 12",
    description="Intelligent routing service for natural language interactions",
    version="1.0.0",
    lifespan=lifespan
)


# CORS Middleware
# Per SECURITY_REQUIREMENTS.md - restrictive by default
if settings.environment == "development":
    # Development: Allow all origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production: Specific origins only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://dashboard.fullpotential.ai",
            "https://fullpotential.ai"
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


# Security Headers Middleware
# Per SECURITY_REQUIREMENTS.md
@app.middleware("http")
async def add_security_headers(request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# Request Counter Middleware
@app.middleware("http")
async def count_requests(request, call_next):
    """Count total requests and errors"""
    request_counter["total"] += 1
    
    response = await call_next(request)
    
    if response.status_code >= 400:
        request_counter["errors"] += 1
    
    return response


# Global Exception Handler
# Per CODE_STANDARDS.md - proper error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler.
    Per UDC_COMPLIANCE.md - standard error format.
    """
    log.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    error_response = ErrorResponse(
        error={
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "details": {}
        },
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


# Import and register routes
from app.api.routes import health, chat, websocket, process, sessions

app.include_router(health.router, tags=["UDC Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(process.router, prefix="/api", tags=["Inter-Droplet"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])


@app.get("/check-orchestrator-health", tags=["Debug"])
async def check_orchestrator_health_endpoint():
    """Temporary endpoint to check Orchestrator 10 health."""
    is_healthy = await orchestrator_client.check_orchestrator_health()
    if is_healthy:
        return JSONResponse(
            status_code=200,
            content={"status": "Orchestrator is healthy"}
        )
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "Orchestrator is unhealthy or unreachable"}
        )


@app.get("/")
async def root():
    """Root endpoint with droplet information"""
    return {
        "droplet_id": settings.droplet_id,
        "name": settings.droplet_name,
        "steward": settings.droplet_steward,
        "version": "1.0.0",
        "status": "active",
        "message": "Chat Orchestrator Droplet 12 - Intelligent routing service",
        "docs": "/docs",
        "health": "/health"
    }


# Development server runner
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )