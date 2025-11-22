"""Orchestrator FastAPI application."""

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import time

from .config import settings
from .models import (
    TaskRequest,
    TaskResponse,
    TaskListResponse,
    DropletsResponse,
    InfoResponse,
    Task,
    CapabilitiesResponse,
    StateResponse,
    DependenciesResponse,
    DependencyStatus,
    MessageRequest,
    MessageResponse,
    SendRequest,
    SendResponse,
)
from .registry_client import registry_client, call_droplet_with_retry
from .error_handling import (
    OrchestratorError,
    DropletNotFoundError,
    DropletUnreachableError,
    InvalidRequestError,
    format_error_response,
)
from .metrics import metrics

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# Task storage (in-memory)
tasks_store: Dict[str, Task] = {}

# Self registration tracking
orchestrator_registered: bool = False


async def register_with_registry() -> None:
    """Register Orchestrator instance with Registry."""
    global orchestrator_registered
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.registry_url}/register",
                json={
                    "name": "orchestrator",
                    "id": 2,
                    "url": "http://localhost:8001",
                    "version": settings.version,
                },
            )
            if response.status_code == 200:
                orchestrator_registered = True
                log.info("Successfully registered with Registry")
            else:
                log.warning(
                    f"Registry registration returned {response.status_code}"
                )
    except Exception as e:
        log.warning(f"Failed to register with Registry: {e}")


async def periodic_registry_sync() -> None:
    """Periodically sync droplet list from Registry."""
    while True:
        try:
            await asyncio.sleep(settings.registry_sync_interval)
            log.debug("Running periodic Registry sync...")
            await registry_client.sync_droplets()
        except Exception as e:
            log.error(f"Periodic Registry sync failed: {e}")


def truncate_response_body(body: Optional[Any], max_size_kb: int = 10) -> Optional[Any]:
    """Truncate response body if it exceeds size limit.

    Args:
        body: Response body (dict, list, or string)
        max_size_kb: Maximum size in kilobytes

    Returns:
        Original body if under limit, truncated dict with info if over limit
    """
    if body is None:
        return None

    import json

    # Convert to JSON string to measure size
    try:
        body_str = json.dumps(body) if isinstance(body, (dict, list)) else str(body)
        body_size_kb = len(body_str.encode("utf-8")) / 1024

        if body_size_kb <= max_size_kb:
            return body

        # Body too large - return truncated info
        return {
            "_truncated": True,
            "_original_size_kb": round(body_size_kb, 2),
            "_max_size_kb": max_size_kb,
            "_message": "Response body exceeded size limit and was truncated",
        }
    except Exception:
        # If we can't serialize it, just return None
        return None


async def periodic_task_cleanup() -> None:
    """Periodically clean up old tasks from memory.

    Removes tasks that:
    - Are older than 24 hours, OR
    - Exceed the max history limit (keeping newest tasks)
    """
    while True:
        try:
            # Run cleanup every 5 minutes
            await asyncio.sleep(300)

            current_time = datetime.utcnow().timestamp()
            max_age_seconds = 24 * 3600  # 24 hours
            max_tasks = settings.task_max_history

            # Remove tasks older than 24 hours
            old_task_ids = [
                task_id
                for task_id, task in tasks_store.items()
                if (current_time - task.created_at) > max_age_seconds
            ]

            for task_id in old_task_ids:
                del tasks_store[task_id]

            if old_task_ids:
                log.info(f"Cleaned up {len(old_task_ids)} tasks older than 24 hours")

            # If still over limit, remove oldest tasks
            if len(tasks_store) > max_tasks:
                # Sort by created_at, keep newest max_tasks
                sorted_tasks = sorted(
                    tasks_store.items(),
                    key=lambda x: x[1].created_at,
                    reverse=True,
                )

                # Keep only the newest max_tasks
                tasks_to_keep = dict(sorted_tasks[:max_tasks])
                removed_count = len(tasks_store) - len(tasks_to_keep)

                tasks_store.clear()
                tasks_store.update(tasks_to_keep)

                log.info(f"Cleaned up {removed_count} tasks to enforce {max_tasks} limit")

        except Exception as e:
            log.error(f"Periodic task cleanup failed: {e}")


def validate_config() -> None:
    """Validate configuration settings at startup."""
    errors = []

    # Validate URLs
    if not settings.registry_url.startswith(("http://", "https://")):
        errors.append(f"Invalid registry_url: {settings.registry_url}")

    # Validate timeouts and intervals
    if settings.registry_timeout <= 0:
        errors.append(f"registry_timeout must be > 0, got {settings.registry_timeout}")

    if settings.registry_sync_interval <= 0:
        errors.append(f"registry_sync_interval must be > 0, got {settings.registry_sync_interval}")

    if settings.task_timeout <= 0:
        errors.append(f"task_timeout must be > 0, got {settings.task_timeout}")

    if settings.task_max_retries < 0:
        errors.append(f"task_max_retries must be >= 0, got {settings.task_max_retries}")

    # Validate environment
    valid_envs = ["development", "staging", "production"]
    if settings.environment not in valid_envs:
        errors.append(f"Invalid environment: {settings.environment}, must be one of {valid_envs}")

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.log_level.upper() not in valid_levels:
        errors.append(f"Invalid log_level: {settings.log_level}, must be one of {valid_levels}")

    if errors:
        error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        log.error(error_msg)
        raise ValueError(error_msg)

    log.info("Configuration validated successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    log.info(f"Starting Orchestrator v{settings.version}")

    # Validate configuration
    validate_config()

    # Load cache from disk
    registry_client._load_cache_from_disk()

    # Try to sync from Registry
    await registry_client.sync_droplets()

    # Register self with Registry
    await register_with_registry()

    # Start background tasks
    asyncio.create_task(periodic_registry_sync())
    asyncio.create_task(periodic_task_cleanup())

    log.info("Orchestrator started successfully")

    yield

    # Shutdown - close connections gracefully
    log.info("Orchestrator shutting down")
    await registry_client.close()
    log.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Orchestrator",
    version="1.1.0",
    description="Central task orchestration service for Full Potential AI",
    lifespan=lifespan,
)


# Request ID and logging middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests and log request/response."""

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        log.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start_time) * 1000)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log response
            log.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return response
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            log.error(
                f"Request failed: {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise


app.add_middleware(RequestIDMiddleware)


@app.get("/orchestrator/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint with dependency checks.

    Returns:
        Service status, version, and dependency health.
    """
    health_status = {
        "status": "active",  # UDC compliant: active|inactive|error
        "service": "orchestrator",
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Check dependencies
    dependencies = {}

    # Check Registry connectivity
    try:
        client = await registry_client._get_client()
        check_url = f"{registry_client.base_url}/health"
        resp = await client.get(check_url, timeout=2.0)
        dependencies["registry"] = {
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "url": registry_client.base_url,
        }
    except Exception as e:
        dependencies["registry"] = {
            "status": "unhealthy",
            "error": str(e),
            "url": registry_client.base_url,
        }
        health_status["status"] = "error"  # UDC compliant

    # Check cache status
    cache_status = registry_client._get_cache_status()
    cache_age = registry_client._get_cache_age()
    dependencies["cache"] = {
        "status": cache_status,
        "age_seconds": int(cache_age),
        "droplet_count": len(registry_client.droplets),
    }

    if cache_status == "unavailable":
        health_status["status"] = "error"  # UDC compliant

    health_status["dependencies"] = dependencies

    return health_status


@app.get("/orchestrator/capabilities")
async def capabilities() -> CapabilitiesResponse:
    """UDC capabilities endpoint.

    Returns:
        Service capabilities, features, and dependencies.
    """
    return CapabilitiesResponse(
        version=settings.version,
        features=[
            "task_routing",
            "inter_droplet_messaging",
            "heartbeat_collection",
            "retry_logic",
            "registry_sync",
            "cache_fallback",
        ],
        dependencies=["registry"],
        udc_version="1.0",
        metadata={
            "build_date": "2025-11-14",
            "registry_url": settings.registry_url,
        },
    )


@app.get("/orchestrator/state")
async def state() -> StateResponse:
    """UDC state endpoint.

    Returns:
        Resource usage and performance metrics.
    """
    uptime_seconds = int(datetime.utcnow().timestamp() - metrics.start_time)

    # Calculate requests per minute (based on uptime)
    requests_per_minute = None
    if uptime_seconds > 0:
        requests_per_minute = round((metrics.tasks_total / uptime_seconds) * 60, 2)

    return StateResponse(
        uptime_seconds=uptime_seconds,
        requests_total=metrics.tasks_total,
        requests_per_minute=requests_per_minute,
        errors_last_hour=metrics.tasks_error,  # Approximation
        last_restart=datetime.fromtimestamp(metrics.start_time).isoformat() + "Z",
    )


@app.get("/orchestrator/dependencies")
async def dependencies() -> DependenciesResponse:
    """UDC dependencies endpoint.

    Returns:
        Required and optional service dependencies with their status.
    """
    # Check Registry connectivity
    registry_connected = False
    try:
        client = await registry_client._get_client()
        resp = await client.get(f"{registry_client.base_url}/health", timeout=2.0)
        registry_connected = resp.status_code == 200
    except Exception:
        registry_connected = False

    registry_dep = DependencyStatus(
        id=1,
        name="registry",
        status="connected" if registry_connected else "unavailable"
    )

    # Check cache status as a dependency indicator
    cache_status = registry_client._get_cache_status()
    cache_dep = DependencyStatus(
        name="registry_cache",
        status="connected" if cache_status == "active" else "degraded"
    )

    return DependenciesResponse(
        required=[registry_dep],
        optional=[cache_dep],
        missing=[]
    )


@app.post("/orchestrator/message")
async def message(msg: MessageRequest) -> MessageResponse:
    """UDC message endpoint.

    Receives inter-droplet messages for coordination and status updates.

    Args:
        msg: UDC-compliant message

    Returns:
        Message acknowledgment with processing status
    """
    log.info(
        f"Received message from {msg.source}: {msg.message_type}",
        extra={
            "trace_id": msg.trace_id,
            "source": msg.source,
            "target": msg.target,
            "message_type": msg.message_type,
        },
    )

    # Handle different message types
    if msg.message_type == "status":
        # Status update from another droplet
        log.info(f"Status update from {msg.source}: {msg.payload}")
    elif msg.message_type == "event":
        # Event notification
        log.info(f"Event from {msg.source}: {msg.payload}")
    elif msg.message_type == "command":
        # Command to execute
        log.info(f"Command from {msg.source}: {msg.payload}")
    elif msg.message_type == "query":
        # Query for information
        log.info(f"Query from {msg.source}: {msg.payload}")

    return MessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success",
    )


@app.post("/orchestrator/send")
async def send_message(request: SendRequest) -> SendResponse:
    """UDC send endpoint.

    Sends messages to other droplets via Registry's routing system.

    Args:
        request: Send request with target and message details

    Returns:
        Send acknowledgment with trace ID
    """
    log.info(
        f"Sending {request.message_type} message to {request.target}",
        extra={
            "target": request.target,
            "message_type": request.message_type,
            "priority": request.priority,
        },
    )

    # Route message through Registry
    sent, result, trace_id = await registry_client.send_message(
        target=request.target,
        message_type=request.message_type,
        payload=request.payload,
        priority=request.priority,
        retry_count=request.retry_count
    )

    return SendResponse(
        sent=sent,
        trace_id=trace_id or str(uuid.uuid4()),
        target=request.target,
        timestamp=datetime.utcnow().isoformat() + "Z",
        result=result  # type: ignore
    )


@app.get("/orchestrator/info")
async def info() -> InfoResponse:
    """Get Orchestrator information.
    
    Returns:
        Orchestrator metadata and Registry status.
    """
    droplets, cache_status, _ = await registry_client.get_droplets()
    cache_age = registry_client._get_cache_age()

    return InfoResponse(
        id=2,
        name="orchestrator",
        version=settings.version,
        registry_url=settings.registry_url,
        registered=orchestrator_registered,
        last_registry_sync=registry_client.cache_timestamp.timestamp()
        if registry_client.cache_timestamp
        else None,
        cache_status=cache_status,  # type: ignore
        cache_age_seconds=cache_age,
    )


@app.get("/orchestrator/droplets")
async def get_droplets() -> DropletsResponse:
    """Get list of known droplets.
    
    Returns:
        Droplet list with cache status.
    """
    droplets, cache_status, served_from = await registry_client.get_droplets()

    if not droplets and cache_status == "unavailable":
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "error": {
                    "code": "REGISTRY_ERROR",
                    "message": "Cannot reach Registry and no cached droplets available",
                },
            },
        )

    metrics.update_droplet_status(
        known=len(droplets), reachable=len(droplets)
    )

    return DropletsResponse(
        droplets=droplets,
        cache_status=cache_status,  # type: ignore
        served_from=served_from,  # type: ignore
    )


@app.post("/orchestrator/tasks")
async def submit_task(request: TaskRequest) -> TaskResponse:
    """Submit a task to be routed to a droplet.
    
    Args:
        request: Task request with droplet_name, method, path, payload.
        
    Returns:
        Task response with task_id and status.
        
    Raises:
        400: If droplet not found or request invalid.
        503: If droplet unreachable after retries.
    """
    try:
        # Get current droplets
        droplets, cache_status, _ = await registry_client.get_droplets()

        if not droplets:
            raise DropletNotFoundError(request.droplet_name, [])

        # Find target droplet
        target_droplet = None
        for d in droplets:
            if d.name.lower() == request.droplet_name.lower():
                target_droplet = d
                break

        if target_droplet is None:
            available = [d.name for d in droplets]
            raise DropletNotFoundError(request.droplet_name, available)

        # Construct target URL
        target_url = f"{target_droplet.url}{request.path}"

        # Create task record
        task_id = str(uuid.uuid4())
        task_start = datetime.utcnow().timestamp()

        try:
            # Call droplet with retry
            status_code, response_body, retry_count, error_msg = (
                await call_droplet_with_retry(
                    url=target_url,
                    method=request.method,
                    payload=request.payload,
                    max_retries=settings.task_max_retries,
                )
            )

            task_end = datetime.utcnow().timestamp()
            duration_ms = int((task_end - task_start) * 1000)

            # Determine task status
            if status_code == 0:
                task_status = "timeout"
            elif status_code >= 200 and status_code < 300:
                task_status = "success"
            elif error_msg is not None:
                task_status = "error"
            else:
                task_status = "error"

            # Truncate response body if too large (10KB limit)
            truncated_body = truncate_response_body(response_body, max_size_kb=10)

            # Record task
            task = Task(
                id=task_id,
                droplet_name=request.droplet_name,
                target_url=target_url,
                method=request.method,
                status=task_status,  # type: ignore
                response_status=status_code if status_code > 0 else None,
                response_body=truncated_body,
                retry_count=retry_count,
                created_at=task_start,
                completed_at=task_end,
                duration_ms=duration_ms,
                error_message=error_msg,
            )

            tasks_store[task_id] = task

            # Record metrics
            metrics.record_task(
                status=task_status,
                duration_ms=duration_ms,
                retry_count=retry_count,
            )

            if task_status == "error" and error_msg:
                log.warning(
                    f"Task {task_id} failed: {error_msg} "
                    f"(retries: {retry_count})"
                )

            return TaskResponse(
                task_id=task_id,
                status=task_status,  # type: ignore
                target_url=target_url,
                response_status=status_code if status_code > 0 else None,
                response_body=response_body,
                retry_count=retry_count,
                duration_ms=duration_ms,
            )

        except Exception as e:
            log.error(f"Task execution error: {e}")
            raise InvalidRequestError(
                message="Failed to execute task",
                details={"error": str(e)},
            )

    except OrchestratorError as e:
        response, status_code = format_error_response(e)
        raise HTTPException(status_code=status_code, detail=response.model_dump())


@app.get("/orchestrator/tasks")
async def list_tasks(
    status: Optional[str] = Query(None),
    droplet_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> TaskListResponse:
    """List tasks with optional filtering.
    
    Args:
        status: Filter by task status (queued, success, error, timeout).
        droplet_name: Filter by target droplet name.
        limit: Maximum number of results.
        
    Returns:
        List of tasks matching filters.
    """
    filtered_tasks = []

    for task in tasks_store.values():
        if status and task.status != status:
            continue
        if droplet_name and task.droplet_name.lower() != droplet_name.lower():
            continue
        filtered_tasks.append(task)

    # Sort by created_at descending (newest first)
    filtered_tasks.sort(key=lambda t: t.created_at, reverse=True)

    # Apply limit
    limited_tasks = filtered_tasks[:limit]

    return TaskListResponse(
        tasks=limited_tasks,
        total=len(filtered_tasks),
        limit=limit,
    )


@app.get("/orchestrator/tasks/{task_id}")
async def get_task(task_id: str) -> Task:
    """Get details of a specific task.
    
    Args:
        task_id: The task ID.
        
    Returns:
        Full task record.
        
    Raises:
        404: If task not found.
    """
    if task_id not in tasks_store:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Task {task_id} not found",
                },
            },
        )

    return tasks_store[task_id]


@app.get("/orchestrator/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get operational metrics.
    
    Returns:
        Metrics including task stats, retry stats, and Registry info.
    """
    metrics_data = metrics.get_metrics()
    return metrics_data.model_dump()


# Error handler for OrchestratorError
@app.exception_handler(OrchestratorError)
async def orchestrator_error_handler(
    request, exc: OrchestratorError
) -> JSONResponse:
    """Handle OrchestratorError exceptions."""
    response, status_code = format_error_response(exc)
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )


@app.get("/health")
async def health_check():
    return {
        "status": "active",
        "service": "orchestrator",
        "version": "1.0.0",
        "dependencies": ["registry"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
