"""
UDC /state endpoint
Reports resource usage and performance metrics
"""

import psutil
from fastapi import APIRouter

from app.models.udc import StateResponse
from app.utils.state import request_count, error_count, get_uptime_seconds

router = APIRouter()


@router.get("/state", response_model=StateResponse)
async def state():
    """
    UDC Compliant: CPU, memory, and performance metrics
    Reports current resource usage and request statistics
    """
    return {
        "cpu_percent": round(psutil.cpu_percent(interval=0.1), 2),
        "memory_mb": round(psutil.virtual_memory().used / (1024 * 1024), 2),
        "uptime_seconds": get_uptime_seconds(),
        "requests_total": request_count,
        "errors_total": error_count,
        "status": "active"
    }
