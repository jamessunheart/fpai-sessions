"""Intent Queue - Universal queue for autonomous system intents"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Dict, Optional
import httpx

from app.config import settings
from app.models import (
    Intent, IntentSubmitRequest, IntentResponse,
    QueueStatus, LifecycleEvent
)

# Initialize FastAPI
app = FastAPI(
    title="Intent Queue",
    description="Unified, persistent, prioritized queue for system intents",
    version=settings.service_version
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (will be replaced with database)
intents_db: Dict[str, Intent] = {}
start_time = datetime.now()
requests_count = 0

# Priority mapping
PRIORITY_ORDER = {"critical": 1, "high": 2, "medium": 3, "low": 4}

#############################################################################
# UDC ENDPOINTS (5/5)
#############################################################################

@app.get("/health")
async def health():
    """1. UDC Health endpoint"""
    return {
        "status": "active",
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": datetime.now().isoformat(),
        "queue_depth": len(intents_db),
        "processing": len([i for i in intents_db.values() if i.status == "processing"])
    }

@app.get("/capabilities")
async def capabilities():
    """2. UDC Capabilities endpoint"""
    return {
        "version": settings.service_version,
        "features": [
            "unified_queue",
            "priority_management",
            "deduplication",
            "persistence",
            "websocket_subscriptions",
            "governance_integration"
        ],
        "dependencies": ["registry", "governance"],
        "udc_version": "1.0",
        "metadata": {
            "max_queue_size": settings.max_queue_size,
            "supported_priorities": ["critical", "high", "medium", "low"],
            "persistence": "in-memory"  # Will be SQLite/PostgreSQL
        }
    }

@app.get("/state")
async def state():
    """3. UDC State endpoint"""
    uptime = (datetime.now() - start_time).total_seconds()
    statuses = {}
    for intent in intents_db.values():
        statuses[intent.status] = statuses.get(intent.status, 0) + 1
    
    return {
        "uptime_seconds": int(uptime),
        "requests_total": requests_count,
        "errors_last_hour": 0,
        "last_restart": start_time.isoformat(),
        "queue_depth": len(intents_db),
        "queued": statuses.get("queued", 0),
        "processing": statuses.get("processing", 0),
        "awaiting_approval": statuses.get("awaiting_approval", 0),
        "completed_today": statuses.get("completed", 0),
        "failed_today": statuses.get("failed", 0)
    }

@app.get("/dependencies")
async def dependencies():
    """4. UDC Dependencies endpoint"""
    # Check registry
    registry_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.registry_url}/health")
            registry_status = "available" if resp.status_code == 200 else "unavailable"
    except:
        registry_status = "unavailable"
    
    # Check governance (optional)
    governance_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.governance_url}/health")
            governance_status = "available" if resp.status_code == 200 else "unavailable"
    except:
        governance_status = "unavailable"
    
    return {
        "required": [
            {"name": "registry", "status": registry_status, "url": settings.registry_url}
        ],
        "optional": [
            {"name": "governance", "status": governance_status, "url": settings.governance_url}
        ],
        "missing": []
    }

@app.post("/message")
async def message(msg: dict):
    """5. UDC Message endpoint"""
    # Handle inter-service messages
    return {
        "received": True,
        "trace_id": msg.get("trace_id"),
        "timestamp": datetime.now().isoformat()
    }

#############################################################################
# SERVICE ENDPOINTS
#############################################################################

@app.post("/intents/submit", response_model=IntentResponse)
async def submit_intent(request: IntentSubmitRequest):
    """Submit new intent to queue"""
    global requests_count
    requests_count += 1
    
    # Create intent
    intent = Intent(
        submitted_by=request.submitted_by,
        source=request.source,
        service_name=request.service_name,
        service_type=request.service_type,
        priority=request.priority,
        purpose=request.purpose,
        key_features=request.key_features,
        dependencies=request.dependencies,
        port=request.port,
        target_tier=request.target_tier,
        blueprint_context=request.blueprint_context,
        auto_build=request.auto_build,
        auto_deploy=request.auto_deploy,
        metadata=request.metadata
    )
    
    # Add lifecycle event
    intent.lifecycle.append(LifecycleEvent(
        phase="submitted",
        status="completed"
    ))
    
    # Calculate queue position
    queued_intents = [i for i in intents_db.values() if i.status == "queued"]
    queued_intents.sort(key=lambda x: (PRIORITY_ORDER.get(x.priority, 99), x.submitted_at))
    intent.queue_position = len(queued_intents) + 1
    
    # Store intent
    intents_db[intent.intent_id] = intent
    
    # Return response
    return IntentResponse(
        intent_id=intent.intent_id,
        status=intent.status,
        queue_position=intent.queue_position,
        priority=intent.priority,
        estimated_start=None,  # TODO: Calculate based on queue
        governance_status="pending_check",
        track_url=f"/intents/{intent.intent_id}",
        subscribe_url=f"ws://localhost:{settings.service_port}/intents/{intent.intent_id}/subscribe"
    )

@app.get("/intents/{intent_id}")
async def get_intent(intent_id: str):
    """Get specific intent details"""
    if intent_id not in intents_db:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    intent = intents_db[intent_id]
    return intent.model_dump()

@app.get("/intents/queue")
async def get_queue():
    """Get current queue status"""
    # Count by status
    by_status = {}
    for intent in intents_db.values():
        by_status[intent.status] = by_status.get(intent.status, 0) + 1
    
    # Count by priority
    by_priority = {}
    for intent in intents_db.values():
        if intent.status == "queued":
            by_priority[intent.priority] = by_priority.get(intent.priority, 0) + 1
    
    # Get next processing
    queued = [i for i in intents_db.values() if i.status == "queued"]
    queued.sort(key=lambda x: (PRIORITY_ORDER.get(x.priority, 99), x.submitted_at))
    next_processing = [
        {
            "intent_id": i.intent_id,
            "service_name": i.service_name,
            "priority": i.priority,
            "queue_position": idx + 1
        }
        for idx, i in enumerate(queued[:5])
    ]
    
    return {
        "total": len(intents_db),
        "by_status": by_status,
        "by_priority": by_priority,
        "next_processing": next_processing,
        "processing_rate": {
            "avg_time_to_start_minutes": 0,  # TODO: Calculate
            "avg_completion_time_minutes": 0,  # TODO: Calculate
            "throughput_per_hour": 0  # TODO: Calculate
        }
    }

@app.get("/intents")
async def list_intents(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    submitted_by: Optional[str] = None,
    limit: int = 20
):
    """List intents with filters"""
    results = list(intents_db.values())
    
    # Apply filters
    if status:
        results = [i for i in results if i.status == status]
    if priority:
        results = [i for i in results if i.priority == priority]
    if submitted_by:
        results = [i for i in results if i.submitted_by == submitted_by]
    
    # Limit
    results = results[:limit]
    
    return {
        "intents": [
            {
                "intent_id": i.intent_id,
                "service_name": i.service_name,
                "submitted_by": i.submitted_by,
                "priority": i.priority,
                "status": i.status,
                "queue_position": i.queue_position,
                "submitted_at": i.submitted_at.isoformat()
            }
            for i in results
        ],
        "total": len(intents_db),
        "filtered": len(results),
        "page": 1,
        "pages": 1
    }

@app.delete("/intents/{intent_id}")
async def cancel_intent(intent_id: str):
    """Cancel queued intent"""
    if intent_id not in intents_db:
        raise HTTPException(status_code=404, detail="Intent not found")
    
    intent = intents_db[intent_id]
    
    if intent.status not in ["queued", "awaiting_approval"]:
        raise HTTPException(status_code=409, detail="Cannot cancel intent in current status")
    
    intent.status = "cancelled"
    intent.cancelled_at = datetime.now()
    
    return {
        "intent_id": intent_id,
        "status": "cancelled",
        "cancelled_at": intent.cancelled_at.isoformat(),
        "cancelled_by": "user",
        "reason": "User requested cancellation"
    }

#############################################################################
# STARTUP / SHUTDOWN
#############################################################################

@app.on_event("startup")
async def startup_event():
    """Register with Registry on startup"""
    print(f"🚀 Starting {settings.service_name} v{settings.service_version}")
    print(f"📡 Port: {settings.service_port}")
    print(f"🎯 TIER: {settings.tier}")
    
    # Register with Registry
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            registration = {
                "name": settings.service_name,
                "id": f"{settings.service_name}-{settings.service_version}",
                "url": f"http://localhost:{settings.service_port}",
                "version": settings.service_version,
                "tier": settings.tier,
                "capabilities": ["intent_queue", "priority_management"]
            }
            resp = await client.post(
                f"{settings.registry_url}/droplets/register",
                json=registration,
                timeout=5.0
            )
            if resp.status_code in [200, 201]:
                print(f"✅ Registered with Registry")
            else:
                print(f"⚠️  Registry registration failed: {resp.status_code}")
    except Exception as e:
        print(f"⚠️  Could not register with Registry: {e}")
    
    print(f"✅ {settings.service_name} is LIVE!")
    print(f"🔄 Ready for recursive self-building!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print(f"👋 Shutting down {settings.service_name}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=settings.service_port)
