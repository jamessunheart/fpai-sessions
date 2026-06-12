"""NEXUS Event Bus - Main FastAPI Application"""
import httpx
import logging
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from src.models import (
    Event, EventType, ConnectedSession, SessionStatus,
    HealthResponse, CapabilitiesResponse, StateResponse,
    DependenciesResponse, DependencyStatus, InterDropletMessage,
    WorkClaimRequest, EventHistoryQuery, SubscribeRequest, PublishRequest
)
from src.websocket_manager import WebSocketManager
from src.event_router import EventRouter
from src.ssot_sync import SSOTSync
from src.work_coordinator import WorkCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service configuration
SERVICE_NAME = "nexus-event-bus"
SERVICE_VERSION = "1.0.0"
SERVICE_PORT = 8450
REGISTRY_URL = "http://localhost:8000"

# Initialize components
ws_manager = WebSocketManager()
event_router = EventRouter(max_history=1000, retention_hours=1)
ssot_sync = SSOTSync()
work_coordinator = WorkCoordinator()

# Service start time
start_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"{SERVICE_NAME} v{SERVICE_VERSION} starting on port {SERVICE_PORT}")

    # Register with Registry
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{REGISTRY_URL}/register",
                json={
                    "name": SERVICE_NAME,
                    "id": f"{SERVICE_NAME}-001",
                    "url": f"http://localhost:{SERVICE_PORT}",
                    "version": SERVICE_VERSION,
                    "capabilities": [
                        "event-streaming",
                        "session-coordination",
                        "work-management",
                        "ssot-sync"
                    ]
                },
                timeout=5.0
            )
        logger.info(f"Registered with Registry at {REGISTRY_URL}")
    except Exception as e:
        logger.warning(f"Could not register with Registry: {e}")

    yield

    # Shutdown
    logger.info(f"{SERVICE_NAME} shutting down")


app = FastAPI(
    title="NEXUS Event Bus",
    description="Real-time session coordination and event streaming",
    version=SERVICE_VERSION,
    lifespan=lifespan
)


# ==================== UDC ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health():
    """UDC: Health check endpoint"""
    return HealthResponse(
        status="active",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        timestamp=datetime.utcnow()
    )


@app.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    """UDC: Service capabilities"""
    return CapabilitiesResponse(
        version=SERVICE_VERSION,
        features=[
            "websocket-streaming",
            "pubsub-topics",
            "session-discovery",
            "work-coordination",
            "ssot-sync",
            "event-history"
        ],
        dependencies=["registry", "filesystem-ssot"],
        udc_version="1.0",
        metadata={
            "max_connections": 50,
            "event_retention": "1 hour",
            "supported_event_types": len(EventType),
            "websocket_endpoint": f"/ws/session/{{session_id}}"
        }
    )


@app.get("/state", response_model=StateResponse)
async def state():
    """UDC: Service operational state"""
    uptime = (datetime.utcnow() - start_time).total_seconds()
    metrics = event_router.get_metrics()

    return StateResponse(
        uptime_seconds=int(uptime),
        connected_sessions=ws_manager.get_connection_count(),
        events_total=metrics["events_total"],
        events_per_second=event_router.get_events_per_second(60),
        errors_last_hour=0,  # TODO: Implement error tracking
        last_restart=start_time,
        event_latency_ms=15.0  # TODO: Implement latency tracking
    )


@app.get("/dependencies", response_model=DependenciesResponse)
async def dependencies():
    """UDC: Dependency status"""
    deps = []

    # Check Registry
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{REGISTRY_URL}/health", timeout=2.0)
            registry_status = "available" if resp.status_code == 200 else "unavailable"
    except:
        registry_status = "unavailable"

    deps.append(DependencyStatus(
        name="registry",
        status=registry_status,
        url=REGISTRY_URL
    ))

    # Check SSOT filesystem
    ssot_status = "available" if ssot_sync.ssot_file.exists() else "unavailable"
    deps.append(DependencyStatus(
        name="ssot-filesystem",
        status=ssot_status,
        path=str(ssot_sync.coordination_path)
    ))

    return DependenciesResponse(
        required=deps,
        optional=[],
        missing=[d.name for d in deps if d.status == "unavailable"]
    )


@app.post("/message")
async def message(msg: InterDropletMessage):
    """UDC: Receive inter-droplet messages"""
    logger.info(f"Received message from {msg.source}: {msg.message_type}")

    # Handle different message types
    if msg.message_type == "query":
        if msg.payload.get("query") == "connected_sessions":
            return {
                "status": "processed",
                "result": {"connected_sessions": ws_manager.get_connection_count()}
            }

    return {"status": "processed", "result": {}}


# ==================== WEBSOCKET ENDPOINT ====================

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for session connections"""

    # Get session info from SSOT
    sessions_data = ssot_sync.load_sessions() or {}
    session_key = session_id.replace("session-", "")

    session_info = ConnectedSession(
        session_id=session_id,
        role=sessions_data.get(session_key, {}).get("role", "Unknown"),
        status=SessionStatus.ACTIVE
    )

    # Connect
    await ws_manager.connect(websocket, session_id, session_info)

    # Notify others
    connect_event = event_router.create_event(
        EventType.SESSION_CONNECTED,
        session_id,
        {"role": session_info.role}
    )
    await ws_manager.broadcast(connect_event, exclude_sender=False)

    # Sync to SSOT
    ssot_sync.on_session_connected(session_info)

    try:
        while True:
            # Receive message from session
            data = await websocket.receive_text()
            msg = json.loads(data)

            action = msg.get("action")

            if action == "subscribe":
                # Subscribe to topics
                topics = msg.get("topics", [])
                ws_manager.subscribe(session_id, topics)

            elif action == "publish":
                # Publish event
                event_type = EventType(msg["event_type"])
                payload = msg.get("payload", {})

                event = event_router.create_event(event_type, session_id, payload)

                # Broadcast to subscribers
                await ws_manager.broadcast(event, exclude_sender=True)

                # Sync to SSOT
                ssot_sync.sync_event(event)

            elif action == "unsubscribe":
                # Unsubscribe from topics
                topics = msg.get("topics", [])
                ws_manager.unsubscribe(session_id, topics)

    except WebSocketDisconnect:
        # Disconnect
        ws_manager.disconnect(session_id)

        # Release work
        released = work_coordinator.release_session_work(session_id)

        # Notify others
        disconnect_event = event_router.create_event(
            EventType.SESSION_DISCONNECTED,
            session_id,
            {"released_work": released}
        )
        await ws_manager.broadcast(disconnect_event)

        # Sync to SSOT
        ssot_sync.on_session_disconnected(session_id)

        logger.info(f"Session {session_id} disconnected")


# ==================== BUSINESS LOGIC ENDPOINTS ====================

@app.post("/events")
async def publish_event(event_type: EventType, session_id: str, payload: dict):
    """HTTP endpoint to publish events (alternative to WebSocket)"""
    event = event_router.create_event(event_type, session_id, payload)

    # Broadcast via WebSocket
    await ws_manager.broadcast(event, exclude_sender=False)

    # Sync to SSOT
    ssot_sync.sync_event(event)

    return {
        "event_id": event.event_id,
        "status": "published",
        "timestamp": event.timestamp
    }


@app.get("/events/history")
async def event_history(
    since: Optional[datetime] = None,
    event_type: Optional[str] = None,
    limit: int = 100
):
    """Retrieve event history"""
    events = event_router.get_history(since, event_type, limit)

    return {
        "count": len(events),
        "events": [e.model_dump() for e in events]
    }


@app.get("/sessions/active")
async def active_sessions():
    """List all connected sessions"""
    sessions = ws_manager.get_connected_sessions()

    return {
        "count": len(sessions),
        "sessions": [s.model_dump() for s in sessions]
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get specific session info"""
    session = ws_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.model_dump()


@app.get("/sessions/capabilities")
async def find_by_capability(skill: Optional[str] = None, available: bool = False):
    """Find sessions by capability"""
    sessions = ws_manager.get_connected_sessions()

    if skill:
        sessions = ws_manager.get_sessions_by_capability(skill)

    if available:
        sessions = [s for s in sessions if s.status == SessionStatus.IDLE]

    return {
        "matches": [s.model_dump() for s in sessions]
    }


@app.post("/work/claim")
async def claim_work(request: WorkClaimRequest):
    """Claim a work item"""
    success, message = work_coordinator.claim_work(
        request.work_id,
        request.session_id,
        request.work_description
    )

    if not success:
        raise HTTPException(status_code=409, detail=message)

    # Broadcast work claimed event
    event = event_router.create_event(
        EventType.WORK_CLAIMED,
        request.session_id,
        {
            "work_id": request.work_id,
            "work_description": request.work_description
        }
    )
    await ws_manager.broadcast(event)

    # Sync to SSOT
    ssot_sync.on_work_claimed(request.session_id, request.work_id, request.work_description)

    return {
        "status": "claimed",
        "work_id": request.work_id,
        "claimed_by": request.session_id,
        "claimed_at": datetime.utcnow()
    }


@app.post("/work/release")
async def release_work(work_id: str, session_id: str):
    """Release a work claim"""
    success, message = work_coordinator.release_work(work_id, session_id)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Broadcast work released event
    event = event_router.create_event(
        EventType.WORK_RELEASED,
        session_id,
        {"work_id": work_id}
    )
    await ws_manager.broadcast(event)

    return {"status": "released", "work_id": work_id}


@app.post("/work/complete")
async def complete_work(work_id: str, session_id: str):
    """Mark work as completed"""
    success, message = work_coordinator.complete_work(work_id, session_id)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Broadcast work completed event
    event = event_router.create_event(
        EventType.WORK_COMPLETED,
        session_id,
        {"work_id": work_id}
    )
    await ws_manager.broadcast(event)

    # Sync to SSOT
    ssot_sync.on_work_completed(session_id, work_id)

    return {"status": "completed", "work_id": work_id}


@app.get("/work/claimed")
async def get_claimed_work():
    """Get all currently claimed work"""
    claims = work_coordinator.get_claimed_work()

    return {
        "count": len(claims),
        "claims": [c.model_dump() for c in claims]
    }


# ==================== STARTUP ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
