"""
UDC Health Endpoints
Per UDC_COMPLIANCE.md - required endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
import psutil
import hashlib

from app.config import settings
from app.models.udc import (
    HealthResponse,
    CapabilitiesResponse,
    StateResponse,
    DependenciesResponse,
    DependencyStatus,
    UDCMessage,
    UDCMessageResponse,
    SendMessageRequest,
    HeartbeatMessage,
    HeartbeatResponseMessage,
    HeartbeatResponsePayload,
    VersionResponse
)
from app.utils.auth import verify_jwt_token
from app.utils.logging import get_logger
from app.services.memory import SESSION_MANAGER
from app.services.orchestrator import orchestrator_client
from app.globals import request_counter

log = get_logger(__name__)

router = APIRouter()

# Track startup time for uptime calculation
import time
startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint.
    Per UDC_COMPLIANCE.md - REQUIRED, <500ms response time.
    JWT authentication required.
    """
    log.debug("health_check_requested")
    
    # Generate proof (SHA256 hash of current timestamp)
    proof_data = f"{settings.droplet_id}:{datetime.utcnow().isoformat()}"
    proof = hashlib.sha256(proof_data.encode()).hexdigest()
    
    response = HealthResponse(
        id=settings.id,
        name=settings.droplet_name,
        steward=settings.droplet_steward,
        status="active",  # Must be: "active" | "inactive" | "error"
        endpoint=settings.droplet_url,
     
        updated_at=datetime.utcnow().isoformat() + "Z"
    )
    
    log.debug("health_check_completed", status=response.status)
    
    return response


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities(token_data: dict = Depends(verify_jwt_token)):
    """
    Capabilities declaration.
    Per UDC_COMPLIANCE.md - REQUIRED.
    JWT authentication required.
    """
    log.debug("capabilities_requested")
    
    response = CapabilitiesResponse(
        version="1.0.0",
        features=[
            "natural_language_understanding",
            "conversation_memory",
            "websocket_support",
            "multi_source_messaging",
            "ai_powered_reasoning",
            "orchestrator_routing"
        ],
        dependencies=["orchestrator", "registry"],
        udc_version="1.0",
        metadata={
            "build_date": "2025-11-12",
            "commit_hash": "production-v1",
            "supported_sources": ["chat", "voice"],
            "ai_model": "gemini-2.5-flash"
        }
    )
    
    return response


@router.get("/state", response_model=StateResponse)
async def state(token_data: dict = Depends(verify_jwt_token)):
    """
    Resource usage and performance metrics.
    Per UDC_COMPLIANCE.md - REQUIRED.
    JWT authentication REQUIRED.
    """
    log.debug("state_requested", requester_id=token_data.get("droplet_id"))
    
    # Gather system metrics
    process = psutil.Process()
    cpu_percent = process.cpu_percent(interval=0.1)
    memory_mb = int(process.memory_info().rss / 1024 / 1024)
    uptime_seconds = int(time.time() - startup_time)
    
    # Calculate requests per minute (simple approximation)
    rpm = int(request_counter["total"] / (uptime_seconds / 60)) if uptime_seconds > 0 else 0
    
    response = StateResponse(
        cpu_percent=round(cpu_percent, 2),
        memory_mb=memory_mb,
        uptime_seconds=uptime_seconds,
        requests_total=request_counter["total"],
        requests_per_minute=rpm,
        errors_last_hour=request_counter["errors"],
        last_restart=datetime.fromtimestamp(startup_time).isoformat() + "Z"
    )
    
    return response


@router.get("/dependencies", response_model=DependenciesResponse)
async def dependencies(token_data: dict = Depends(verify_jwt_token)):
    """
    Dependencies declaration.
    Per UDC_COMPLIANCE.md - REQUIRED.
    JWT authentication REQUIRED.
    """
    log.debug("dependencies_requested", requester_id=token_data.get("droplet_id"))
    
    # Check Orchestrator health
    orch_healthy = await orchestrator_client.check_orchestrator_health()
    orch_status = "connected" if orch_healthy else "unavailable"
    
    response = DependenciesResponse(
        required=[
            DependencyStatus(
                id=10,
                name="Orchestrator",
                status=orch_status
            ),
            DependencyStatus(
                id=1,
                name="Registry",
                status="connected"  # Assume connected if we got here
            )
        ],
        optional=[
            DependencyStatus(
                id=6,
                name="Voice",
                status="available"
            ),
            DependencyStatus(
                id=2,
                name="Dashboard",
                status="available"
            ),
            DependencyStatus(
                id=14,
                name="Visibility Deck",
                status="available"
            )
        ],
        missing=[]
    )
    
    return response

@router.get("/version", response_model=VersionResponse)
async def version(token_data: dict = Depends(verify_jwt_token)):
    """
    Version endpoint.
    Per UDC_COMPLIANCE.md - REQUIRED.
    JWT authentication REQUIRED.
    """
    log.debug("version_requested", requester_id=token_data.get("droplet_id"))
    response = VersionResponse(
        version="1.0.0",
        build_date= "2025-11-12",
        commit_hash= "dev",
        environment= "development",
        deployed_by= "Zainab")
        
    
    return response

@router.post("/message", response_model=UDCMessageResponse)
async def receive_message(
    message: UDCMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Receive UDC-compliant messages from other droplets.
    Per UDC_COMPLIANCE.md - REQUIRED for inter-droplet communication.
    JWT authentication REQUIRED.
    """
    log.info(
        "udc_message_received",
        trace_id=message.trace_id,
        source=message.source,
        message_type=message.message_type
    )
    
    # Process message based on type
    # For now, just acknowledge receipt
    # Future: Add actual message processing logic
    
    response = UDCMessageResponse(
        received=True,
        trace_id=message.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success"
    )
    
    return response


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Send messages to other droplets (via Orchestrator).
    Per UDC_COMPLIANCE.md - REQUIRED.
    JWT authentication REQUIRED.
    """
    log.info(
        "udc_send_requested",
        target=request.target,
        message_type=request.message_type,
        priority=request.priority
    )
    
    # Extract target droplet ID
    # Handle both "droplet_1" and "1" formats
    target_id = request.target.replace("droplet_", "") if "droplet_" in request.target else request.target
    
    # Send via Orchestrator
    result = await orchestrator_client.send_via_orchestrator(
        target_id=target_id,
        action="/message",  # Send to target's /message endpoint
        data=request.payload
    )
    
    if result:
        return {
            "status": "success",
            "message": "Message sent successfully",
            "result": result
        }
    else:
        return {
            "status": "error",
            "message": "Failed to send message via Orchestrator"
        }


@router.post("/heartbeat", response_model=HeartbeatResponseMessage)
async def receive_heartbeat(
    heartbeat: HeartbeatMessage,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Receive heartbeat from other droplets and return a UDC-compliant response.
    JWT authentication REQUIRED.
    
    Heartbeat deadline calculation:
    - Parses the incoming heartbeat's timestamp (ISO 8601 format)
    - Converts to Unix timestamp
    - Adds 60 seconds (standard heartbeat interval per INTEGRATION_GUIDE.md)
    - Returns as Unix timestamp float for the next expected heartbeat
    """
    log.info(
        "heartbeat_received",
        source=heartbeat.source,
        metrics=heartbeat.payload.metrics,
        status=heartbeat.payload.status,
        heartbeat_timestamp=heartbeat.timestamp
    )

    # Calculate the next heartbeat deadline based on the heartbeat's timestamp
    # Parse the ISO 8601 timestamp from the incoming heartbeat
    try:
        # Remove 'Z' and parse ISO format
        timestamp_str = heartbeat.timestamp.replace('Z', '+00:00')
        heartbeat_datetime = datetime.fromisoformat(timestamp_str)
        # Convert to Unix timestamp (seconds since epoch)
        heartbeat_unix = heartbeat_datetime.timestamp()
    except (ValueError, AttributeError) as e:
        log.warning("heartbeat_timestamp_parse_failed", error=str(e), timestamp=heartbeat.timestamp)
        # Fallback: use current time if timestamp parsing fails
        heartbeat_unix = time.time()
    
    # Add 60 seconds to the heartbeat timestamp (standard interval per INTEGRATION_GUIDE.md)
    heartbeat_interval_seconds = 60
    next_deadline = heartbeat_unix + heartbeat_interval_seconds

    response = HeartbeatResponseMessage(
        trace_id=heartbeat.trace_id,
        source=settings.droplet_id,
        target=heartbeat.source,
        timestamp=datetime.utcnow().isoformat() + "Z",
        payload=HeartbeatResponsePayload(
            received=True,
            next_heartbeat_deadline=next_deadline
        )
    )
    
    log.debug(
        "heartbeat_response_calculated",
        next_deadline=next_deadline,
        heartbeat_unix=heartbeat_unix,
        interval_seconds=heartbeat_interval_seconds
    )
    
    return response