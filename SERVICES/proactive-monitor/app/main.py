"""
Proactive Monitor Service - Main Application

Continuously monitors critical services and sends signals to Chief of Staff.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import asyncio
import time

from app.config import settings
from app.monitor import monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track service start time
service_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Proactive Monitor Service...")

    # Start monitoring in background
    asyncio.create_task(monitor.run_forever())

    logger.info("Proactive Monitor Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Proactive Monitor Service...")
    logger.info("Proactive Monitor Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Proactive Monitor Service",
    description="Continuously monitors services and sends signals to Chief of Staff",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# UDC ENDPOINTS
# ============================================================================

@app.get("/health", tags=["UDC"])
async def health_check():
    """UDC Health Check"""
    uptime_seconds = int(time.time() - service_start_time)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "version": settings.APP_VERSION
    }


@app.get("/capabilities", tags=["UDC"])
async def capabilities():
    """UDC Capabilities"""
    return {
        "service_name": settings.SERVICE_NAME,
        "droplet_id": settings.DROPLET_ID,
        "capabilities": [
            "service_monitoring",
            "health_checking",
            "performance_tracking",
            "proactive_alerting",
            "anomaly_detection"
        ],
        "monitored_services": [s['name'] for s in settings.services],
        "check_interval_seconds": settings.CHECK_INTERVAL_SECONDS
    }


@app.get("/state", tags=["UDC"])
async def state():
    """UDC State"""
    status = monitor.get_status()

    healthy_count = sum(
        1 for s in status['services'].values()
        if s.get('status') == 'healthy'
    )

    return {
        "status": "active",
        "total_services": status['total_services'],
        "healthy": healthy_count,
        "unhealthy": status['total_services'] - healthy_count,
        "last_check": max(
            (s.get('last_check', '') for s in status['services'].values()),
            default=None
        )
    }


@app.get("/dependencies", tags=["UDC"])
async def dependencies():
    """UDC Dependencies"""
    return {
        "required_services": [
            {
                "name": "Chief of Staff",
                "url": settings.CHIEF_OF_STAFF_URL,
                "purpose": "Signal routing and filtering"
            }
        ],
        "monitored_services": [
            {
                "name": s['name'],
                "port": s['port'],
                "priority": s['priority']
            }
            for s in settings.services
        ]
    }


# ============================================================================
# MONITORING ENDPOINTS
# ============================================================================

@app.get("/status", tags=["Monitoring"])
async def get_status():
    """Get detailed monitoring status"""
    return monitor.get_status()


@app.post("/check/now", tags=["Monitoring"])
async def run_check_now():
    """
    Trigger an immediate monitoring check
    (normally runs every 5 minutes automatically)
    """
    asyncio.create_task(monitor.run_check_cycle())
    return {
        "message": "Monitoring check triggered",
        "will_complete_in": "~30 seconds"
    }


@app.get("/history/{service_name}", tags=["Monitoring"])
async def get_service_history(service_name: str):
    """Get check history for a specific service"""
    history = list(monitor.check_history.get(service_name, []))

    if not history:
        return {
            "service": service_name,
            "checks": [],
            "message": "No checks performed yet"
        }

    return {
        "service": service_name,
        "total_checks": len(history),
        "latest_status": history[-1]['status'],
        "latest_response_time": history[-1]['response_time'],
        "checks": [
            {
                "status": c['status'],
                "response_time": c['response_time'],
                "timestamp": c['timestamp'].isoformat()
            }
            for c in history[-20:]  # Last 20 checks
        ]
    }


@app.get("/server-health/local", tags=["Monitoring"])
async def get_local_server_health():
    """
    Get server metrics for local machine only

    Used by remote proactive-monitor instances to fetch metrics
    """
    metrics = monitor.get_local_server_metrics()
    if metrics:
        return metrics
    else:
        return {"error": "Could not collect server metrics"}


@app.get("/server-health", tags=["Monitoring"])
async def get_server_health():
    """
    Get server health for both primary and secondary

    Returns:
        {
            "primary": {"ram_free_gb": 1.9, "disk_free_gb": 350, ...},
            "secondary": {"ram_free_gb": 12.0, "disk_free_gb": 420, ...}
        }
    """
    return await monitor.get_server_health()


# ============================================================================
# ROOT
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Service info"""
    return {
        "service": "Proactive Monitor",
        "version": settings.APP_VERSION,
        "droplet_id": settings.DROPLET_ID,
        "purpose": "Continuously monitors services and alerts via Chief of Staff",
        "monitoring": {
            "services": len(settings.services),
            "interval_seconds": settings.CHECK_INTERVAL_SECONDS,
            "chief_of_staff": settings.CHIEF_OF_STAFF_URL
        },
        "docs": "/docs",
        "status": "/status",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
