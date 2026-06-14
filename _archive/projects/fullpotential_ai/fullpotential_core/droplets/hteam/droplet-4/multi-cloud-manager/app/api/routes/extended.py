"""
UDC Extended Endpoints - Combined File
Save this as: app/api/routes/extended.py

This file combines multiple UDC extended endpoints:
- version.py
- metrics.py  
- logs.py
- events.py
- proof.py

You can split these into separate files if preferred, or keep them combined.
"""

import sys
import psutil
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.models.udc import VersionResponse, ProofResponse
from app.utils.auth import verify_jwt_token
from app.utils.logging import get_recent_logs, get_recent_events, get_last_action
from app.utils.state import request_count, error_count, get_uptime_seconds

# ============================================================================
# VERSION
# ============================================================================

version = APIRouter()

@version.get("/version", response_model=VersionResponse)
async def version_info():
    """UDC Compliant: Build and version information"""
    return {
        "version": settings.version,
        "udc_version": settings.udc_version,
        "build_date": "2025-11-14",
        "droplet_id": settings.droplet_id,
        "name": settings.droplet_name,
        "environment": "production"
    }

# ============================================================================
# METRICS
# ============================================================================

metrics = APIRouter()

@metrics.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """UDC Compliant: Prometheus format metrics"""
    uptime = get_uptime_seconds()
    
    metrics_text = f"""# HELP droplet_requests_total Total number of requests
# TYPE droplet_requests_total counter
droplet_requests_total{{droplet_id="{settings.droplet_id}"}} {request_count}

# HELP droplet_errors_total Total number of errors
# TYPE droplet_errors_total counter
droplet_errors_total{{droplet_id="{settings.droplet_id}"}} {error_count}

# HELP droplet_uptime_seconds Uptime in seconds
# TYPE droplet_uptime_seconds gauge
droplet_uptime_seconds{{droplet_id="{settings.droplet_id}"}} {uptime}

# HELP droplet_cpu_percent CPU usage percentage
# TYPE droplet_cpu_percent gauge
droplet_cpu_percent{{droplet_id="{settings.droplet_id}"}} {psutil.cpu_percent(interval=0.1)}

# HELP droplet_memory_bytes Memory usage in bytes
# TYPE droplet_memory_bytes gauge
droplet_memory_bytes{{droplet_id="{settings.droplet_id}"}} {psutil.virtual_memory().used}
"""
    
    return metrics_text

# ============================================================================
# LOGS
# ============================================================================

logs = APIRouter()

@logs.get("/logs")
async def get_logs(
    limit: int = 100,
    level: Optional[str] = None,
    token_data: dict = Depends(verify_jwt_token)
):
    """UDC Compliant: Retrieve structured logs"""
    logs_data = get_recent_logs(limit, level)
    
    return {
        "logs": logs_data,
        "total": len(logs_data),
        "droplet_id": settings.droplet_id
    }

# ============================================================================
# EVENTS
# ============================================================================

events = APIRouter()

@events.get("/events")
async def get_events(
    limit: int = 50,
    event_type: Optional[str] = None,
    token_data: dict = Depends(verify_jwt_token)
):
    """UDC Compliant: Retrieve recent events"""
    events_data = get_recent_events(limit, event_type)
    
    return {
        "events": events_data,
        "total": len(events_data),
        "droplet_id": settings.droplet_id
    }

# ============================================================================
# PROOF
# ============================================================================

proof = APIRouter()

@proof.get("/proof", response_model=ProofResponse)
async def get_proof(token_data: dict = Depends(verify_jwt_token)):
    """UDC Compliant: Last verified action"""
    last_action = get_last_action()
    
    if not last_action:
        raise HTTPException(status_code=404, detail="No actions recorded yet")
    
    return last_action
