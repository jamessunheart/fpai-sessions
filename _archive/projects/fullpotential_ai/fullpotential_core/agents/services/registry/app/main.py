"""Registry FastAPI application - Fully UDC Compliant.

The Registry is the Single Source of Truth (SSOT) for all droplets in the system.
It provides service registration, discovery, and identity management.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import Dict, Any, List
import time
import uuid
import logging
import httpx

from app.models import (
    HealthResponse,
    CapabilitiesResponse,
    StateResponse,
    DependenciesResponse,
    DependencyStatus,
    MessageRequest,
    MessageResponse,
    SendRequest,
    SendResponse,
    Droplet,
    RegisterDropletRequest,
    UpdateDropletRequest,
    DropletsListResponse,
    DropletResponse,
    DeleteResponse,
    ErrorResponse,
    ErrorDetail,
)
from app.udc_config import SYSTEM_TOPOLOGY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application start time for uptime tracking
start_time = time.time()
request_count = 0
error_count = 0


def utc_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp with trailing Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# In-memory storage for droplets
droplets: Dict[int, Droplet] = {}
next_droplet_id = 1

app = FastAPI(
    title="Registry",
    version="1.0.0",
    description="Service registry and identity management for Full Potential AI - Fully UDC Compliant",
)


# Middleware to track requests
@app.middleware("http")
async def track_requests(request, call_next):
    """Track request count for metrics."""
    global request_count
    request_count += 1
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        global error_count
        error_count += 1
        logger.error(f"Request error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )


# ============================================================================
# UDC COMPLIANCE ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """UDC /health endpoint.

    Returns service health status using UDC-compliant status values.
    """
    # Determine health status
    overall_status = "active"

    # Check if we have any droplets registered
    if len(droplets) == 0:
        overall_status = "inactive"  # Service is idle

    return HealthResponse(
        status=overall_status,
        service="registry",
        version="1.0.0",
        timestamp=utc_timestamp(),
    )


@app.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    """UDC /capabilities endpoint.

    Returns what this droplet provides and its dependencies.
    """
    return CapabilitiesResponse(
        version="1.0.0",
        features=[
            "service_registry",
            "droplet_discovery",
            "identity_management",
            "status_tracking",
            "jwt_tokens",  # TODO: Implement
            "endpoint_directory",
        ],
        dependencies=[],  # Registry has no dependencies - it's the foundation
        udc_version="1.0",
        metadata={
            "build_date": "2024-11-14",
            "description": "Single Source of Truth for Full Potential AI droplet mesh",
            "registered_droplets": len(droplets),
        },
    )


@app.get("/state", response_model=StateResponse)
async def state() -> StateResponse:
    """UDC /state endpoint.

    Returns current resource usage and performance metrics.
    """
    uptime_seconds = int(time.time() - start_time)

    # Calculate requests per minute
    requests_per_minute = None
    if uptime_seconds > 0:
        requests_per_minute = round((request_count / uptime_seconds) * 60, 2)

    return StateResponse(
        uptime_seconds=uptime_seconds,
        requests_total=request_count,
        requests_per_minute=requests_per_minute,
        errors_last_hour=error_count,
        last_restart=datetime.fromtimestamp(start_time).isoformat() + "Z",
    )


@app.get("/dependencies", response_model=DependenciesResponse)
async def dependencies() -> DependenciesResponse:
    """UDC /dependencies endpoint.

    Returns required and optional service dependencies.
    Registry has NO dependencies - it's the foundation of the system.
    """
    return DependenciesResponse(
        required=[],
        optional=[],
        missing=[]
    )


@app.post("/message", response_model=MessageResponse)
async def message(msg: MessageRequest) -> MessageResponse:
    """UDC /message endpoint.

    Receives inter-droplet messages.
    """
    logger.info(f"Received message from {msg.source}: {msg.message_type}")

    # Handle different message types
    if msg.message_type == "status":
        # Update droplet status if it's registered
        for droplet_id, droplet in droplets.items():
            if droplet.name == msg.source:
                logger.info(f"Status update from {msg.source}: {msg.payload}")
                break

    return MessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=utc_timestamp(),
        result="success",
    )


@app.get("/registry/map")
async def registry_map() -> Dict[str, Any]:
    """Return the system topology derived from local udc_config data."""

    topology = SYSTEM_TOPOLOGY.get("droplets", [])
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []

    # Build helper lookup tables for registered droplets
    registered_by_name = {droplet.name.lower(): droplet for droplet in droplets.values()}

    existing_ids = set()
    for droplet_cfg in topology:
        cfg_id = droplet_cfg.get("id")
        cfg_name = droplet_cfg.get("name")
        fallback_id = cfg_name.lower() if cfg_name else None
        node_id = cfg_id or fallback_id
        if node_id is None:
            node_id = f"node-{len(nodes) + 1}"

        # Default to config-defined status but prefer live registry data
        status_value = droplet_cfg.get("status", "inactive")
        match = None
        if cfg_name:
            match = registered_by_name.get(cfg_name.lower())

        if match:
            cfg_name = match.name
            status_value = match.status or status_value

        nodes.append(
            {
                "id": node_id,
                "name": cfg_name or node_id,
                "status": status_value,
                "type": droplet_cfg.get("type"),
                "metadata": droplet_cfg.get("metadata"),
            }
        )
        existing_ids.add(node_id)

        for dependency_id in droplet_cfg.get("dependencies", []):
            edges.append({"from": dependency_id, "to": node_id})

    # Include any dynamically registered droplets that are not in the static config
    for droplet in droplets.values():
        node_id = droplet.name.lower()
        if node_id not in existing_ids:
            nodes.append(
                {
                    "id": node_id,
                    "name": droplet.name,
                    "status": droplet.status,
                    "metadata": droplet.metadata,
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "source": SYSTEM_TOPOLOGY.get("version", "udc_config"),
        "timestamp": utc_timestamp(),
        "metadata": {
            "generated_at": utc_timestamp(),
            "registered_total": len(droplets),
        },
    }


@app.post("/send", response_model=SendResponse)
async def send_message(request: SendRequest) -> SendResponse:
    """UDC /send endpoint.

    Sends messages to other droplets.
    """
    trace_id = str(uuid.uuid4())

    # Find target droplet
    target_droplet = None
    for droplet in droplets.values():
        if droplet.name == request.target:
            target_droplet = droplet
            break

    if not target_droplet:
        logger.warning(f"Target droplet '{request.target}' not found in registry")
        return SendResponse(
            sent=False,
            trace_id=trace_id,
            target=request.target,
            timestamp=utc_timestamp(),
            result="error",
        )

    # Send the message via HTTP to target droplet's /message endpoint
    logger.info(f"Sending {request.message_type} message to {request.target} at {target_droplet.endpoint}")

    # Build the message payload
    message_payload = {
        "trace_id": trace_id,
        "source": "registry",
        "target": request.target,
        "message_type": request.message_type,
        "payload": request.payload,
        "timestamp": utc_timestamp(),
    }

    try:
        # Send HTTP POST to target droplet's /message endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Construct the full URL - try both with and without /message suffix
            message_url = f"{target_droplet.endpoint.rstrip('/')}/message"

            response = await client.post(
                message_url,
                json=message_payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                logger.info(f"Message delivered successfully to {request.target}")
                return SendResponse(
                    sent=True,
                    trace_id=trace_id,
                    target=request.target,
                    timestamp=utc_timestamp(),
                    result="success",
                )
            else:
                logger.error(f"Failed to deliver message to {request.target}: HTTP {response.status_code}")
                return SendResponse(
                    sent=False,
                    trace_id=trace_id,
                    target=request.target,
                    timestamp=utc_timestamp(),
                    result="error",
                )

    except httpx.TimeoutException:
        logger.error(f"Timeout sending message to {request.target}")
        return SendResponse(
            sent=False,
            trace_id=trace_id,
            target=request.target,
            timestamp=utc_timestamp(),
            result="error",
        )
    except Exception as e:
        logger.error(f"Error sending message to {request.target}: {str(e)}")
        return SendResponse(
            sent=False,
            trace_id=trace_id,
            target=request.target,
            timestamp=utc_timestamp(),
            result="error",
        )


# ============================================================================
# REGISTRY CORE ENDPOINTS
# ============================================================================

@app.post("/droplets", response_model=DropletResponse, status_code=status.HTTP_201_CREATED)
async def register_droplet(request: RegisterDropletRequest) -> DropletResponse:
    """Register a new droplet in the registry.

    Args:
        request: Droplet registration information

    Returns:
        Registered droplet with assigned ID
    """
    global next_droplet_id

    # Check if droplet name already exists
    for droplet in droplets.values():
        if droplet.name == request.name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Droplet with name '{request.name}' already exists"
            )

    # Assign ID
    droplet_id = request.id if request.id else next_droplet_id
    if request.id:
        next_droplet_id = max(next_droplet_id, request.id + 1)
    else:
        next_droplet_id += 1

    # Create droplet
    now = utc_timestamp()
    droplet = Droplet(
        id=droplet_id,
        name=request.name,
        steward=request.steward,
        endpoint=request.endpoint,
        status="active",
        metadata=request.metadata or {},
        registered_at=now,
        updated_at=now,
    )

    droplets[droplet_id] = droplet
    logger.info(f"Registered droplet: {droplet.name} (ID: {droplet_id})")

    return DropletResponse(
        droplet=droplet,
        timestamp=now
    )


@app.get("/droplets", response_model=DropletsListResponse)
async def list_droplets() -> DropletsListResponse:
    """List all registered droplets.

    Returns:
        List of all droplets in the registry
    """
    droplet_list = list(droplets.values())

    return DropletsListResponse(
        droplets=droplet_list,
        total=len(droplet_list),
        timestamp=utc_timestamp(),
    )


@app.get("/droplets/{droplet_id}", response_model=DropletResponse)
async def get_droplet(droplet_id: int) -> DropletResponse:
    """Get information about a specific droplet.

    Args:
        droplet_id: ID of the droplet to retrieve

    Returns:
        Droplet information
    """
    if droplet_id not in droplets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Droplet with ID {droplet_id} not found"
        )

    return DropletResponse(
        droplet=droplets[droplet_id],
        timestamp=utc_timestamp(),
    )


@app.get("/droplets/name/{droplet_name}", response_model=DropletResponse)
async def get_droplet_by_name(droplet_name: str) -> DropletResponse:
    """Get information about a droplet by name.

    Args:
        droplet_name: Name of the droplet to retrieve

    Returns:
        Droplet information
    """
    for droplet in droplets.values():
        if droplet.name == droplet_name:
            return DropletResponse(
                droplet=droplet,
                timestamp=utc_timestamp(),
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Droplet with name '{droplet_name}' not found"
    )


@app.patch("/droplets/{droplet_id}", response_model=DropletResponse)
async def update_droplet(droplet_id: int, request: UpdateDropletRequest) -> DropletResponse:
    """Update droplet information.

    Args:
        droplet_id: ID of the droplet to update
        request: Fields to update

    Returns:
        Updated droplet information
    """
    if droplet_id not in droplets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Droplet with ID {droplet_id} not found"
        )

    droplet = droplets[droplet_id]

    # Update fields
    if request.status is not None:
        droplet.status = request.status
    if request.endpoint is not None:
        droplet.endpoint = request.endpoint
    if request.metadata is not None:
        droplet.metadata = request.metadata
    if request.proof is not None:
        droplet.proof = request.proof
    if request.cost_usd is not None:
        droplet.cost_usd = request.cost_usd
    if request.yield_usd is not None:
        droplet.yield_usd = request.yield_usd

    droplet.updated_at = utc_timestamp()

    logger.info(f"Updated droplet: {droplet.name} (ID: {droplet_id})")

    return DropletResponse(
        droplet=droplet,
        timestamp=droplet.updated_at
    )


@app.delete("/droplets/{droplet_id}", response_model=DeleteResponse)
async def delete_droplet(droplet_id: int) -> DeleteResponse:
    """Delete a droplet from the registry.

    Args:
        droplet_id: ID of the droplet to delete

    Returns:
        Deletion confirmation
    """
    if droplet_id not in droplets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Droplet with ID {droplet_id} not found"
        )

    droplet_name = droplets[droplet_id].name
    del droplets[droplet_id]

    logger.info(f"Deleted droplet: {droplet_name} (ID: {droplet_id})")

    return DeleteResponse(
        success=True,
        message=f"Droplet '{droplet_name}' deleted successfully",
        deleted_at=utc_timestamp(),
    )


# ============================================================================
# LEGACY/COMPATIBILITY ENDPOINTS
# ============================================================================

@app.post("/register")
async def legacy_register(droplet_data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy registration endpoint for backward compatibility.

    Maps old format to new RegisterDropletRequest format.
    """
    request = RegisterDropletRequest(
        id=droplet_data.get("id"),
        name=droplet_data.get("name"),
        steward=droplet_data.get("steward"),
        endpoint=droplet_data.get("url") or droplet_data.get("endpoint"),
        metadata={"version": droplet_data.get("version")}
    )

    response = await register_droplet(request)

    # Return in old format
    return {
        "success": True,
        "droplet_id": response.droplet.id,
        "message": f"Droplet '{response.droplet.name}' registered successfully"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
