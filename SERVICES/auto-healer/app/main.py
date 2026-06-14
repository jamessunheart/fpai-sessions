"""
Auto-Healer - Smart service healing with diagnosis and learning

Main FastAPI application that orchestrates health checking, failure diagnosis,
healing execution, and escalation.
"""
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import SERVICE_NAME, SERVICE_PORT, LOG_LEVEL, HEALTH_CHECK_INTERVAL
from .registry import registry, ServiceDefinition
from .health_checker import health_checker, HealthCheckResult, ServiceStatus
from .failure_analyzer import failure_analyzer, FailureDiagnosis
from .healing_executor import healing_executor, HealingOutcome, HealingResult
from .knowledge_base import knowledge_base
from .escalation import escalation_manager, AlertSeverity

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Background task for continuous monitoring
async def healing_loop():
    """
    Main healing loop that continuously monitors and heals services.
    """
    logger.info("Starting auto-healing loop...")
    
    while True:
        try:
            # Check all services
            results = await health_checker.check_all_services()
            
            # Process unhealthy services
            for result in health_checker.get_unhealthy_services():
                service = registry.get(result.service_name)
                if not service:
                    continue
                
                # Check for critical down time
                critical_alert = escalation_manager.check_critical_down_time(
                    result.service_name, 
                    service.critical, 
                    result.is_healthy()
                )
                if critical_alert:
                    await escalation_manager.send_alert(critical_alert)
                
                # Only attempt healing if consecutive failures exceed threshold
                if result.consecutive_failures >= 2:
                    # Diagnose the failure
                    diagnosis = failure_analyzer.diagnose(service)
                    knowledge_base.record_diagnosis(diagnosis)
                    
                    logger.info(
                        f"Diagnosed {service.name}: {diagnosis.failure_type.value} "
                        f"(confidence: {diagnosis.confidence:.0%})"
                    )
                    
                    # Attempt healing
                    outcome = healing_executor.heal(service, diagnosis)
                    knowledge_base.record_outcome(outcome)
                    
                    logger.info(
                        f"Healing {service.name}: {outcome.action_name} -> {outcome.result.value}"
                    )
                    
                    # Check if we need to escalate
                    should_escalate, reason = escalation_manager.should_escalate(service.name, outcome)
                    if should_escalate:
                        alert = escalation_manager.create_alert(service.name, outcome, diagnosis)
                        await escalation_manager.send_alert(alert)
                        logger.warning(f"Escalated: {service.name} - {reason}")
                    
                    # Check for recurring patterns
                    pattern_alert = escalation_manager.check_recurring_pattern(
                        service.name, 
                        diagnosis.failure_type.value
                    )
                    if pattern_alert:
                        await escalation_manager.send_alert(pattern_alert)
            
            # Reset attempt counts for healthy services
            for result in results.values():
                if result.is_healthy():
                    healing_executor.reset_attempts(result.service_name)
            
            # Record health history
            for name, result in results.items():
                knowledge_base.record_health_check(
                    name, 
                    result.status.value, 
                    result.response_time_ms, 
                    result.error
                )
            
        except Exception as e:
            logger.error(f"Healing loop error: {e}")
        
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info(f"Starting {SERVICE_NAME} on port {SERVICE_PORT}")
    
    # Start the healing loop in the background
    task = asyncio.create_task(healing_loop())
    
    yield
    
    # Shutdown
    task.cancel()
    health_checker.stop()
    logger.info("Auto-healer stopped")


# Create FastAPI app
app = FastAPI(
    title="Auto-Healer",
    description="Smart service healing with diagnosis and learning",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API Models
# =============================================================================

class ServiceRequest(BaseModel):
    name: str
    systemd_name: str
    port: int
    working_dir: str
    health_endpoint: str = "/health"
    venv_path: Optional[str] = ".venv"
    requirements_file: str = "requirements.txt"
    main_file: str = "main.py"
    critical: bool = False


class SuppressRequest(BaseModel):
    duration_minutes: int = 60


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    summary = health_checker.get_summary()
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "monitored_services": summary["total_services"],
        "healthy_services": summary["healthy"],
        "health_score": summary["health_score"],
    }


@app.get("/api/status")
async def get_status():
    """Get comprehensive auto-healer status."""
    health_summary = health_checker.get_summary()
    kb_stats = knowledge_base.get_stats()
    healing_stats = healing_executor.get_stats()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "health": health_summary,
        "healing": healing_stats,
        "knowledge_base": kb_stats,
        "recent_alerts": escalation_manager.get_recent_alerts(limit=10),
        "suppressed_services": escalation_manager.get_suppressed_services(),
    }


# =============================================================================
# Service Registry Endpoints
# =============================================================================

@app.get("/api/services")
async def list_services():
    """List all monitored services."""
    return registry.to_dict()


@app.get("/api/services/{name}")
async def get_service(name: str):
    """Get details for a specific service."""
    service = registry.get(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {name} not found")
    
    health = health_checker.results.get(name)
    
    return {
        "definition": service.to_dict(),
        "health": health.to_dict() if health else None,
        "mttr_minutes": knowledge_base.get_service_mttr(name),
    }


@app.post("/api/services")
async def add_service(service: ServiceRequest):
    """Add a new service to monitor."""
    svc = ServiceDefinition(
        name=service.name,
        systemd_name=service.systemd_name,
        port=service.port,
        working_dir=service.working_dir,
        health_endpoint=service.health_endpoint,
        venv_path=service.venv_path,
        requirements_file=service.requirements_file,
        main_file=service.main_file,
        critical=service.critical,
    )
    registry.add(svc)
    return {"status": "added", "service": svc.to_dict()}


@app.delete("/api/services/{name}")
async def remove_service(name: str):
    """Remove a service from monitoring."""
    if not registry.get(name):
        raise HTTPException(status_code=404, detail=f"Service {name} not found")
    registry.remove(name)
    return {"status": "removed", "service": name}


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/api/services/{name}/health")
async def check_service_health(name: str):
    """Check health of a specific service."""
    service = registry.get(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {name} not found")
    
    result = await health_checker.check_service(service)
    return result.to_dict()


@app.post("/api/health/check-all")
async def trigger_health_check():
    """Trigger immediate health check of all services."""
    results = await health_checker.check_all_services()
    return health_checker.get_summary()


# =============================================================================
# Healing Endpoints
# =============================================================================

@app.post("/api/services/{name}/heal")
async def trigger_healing(name: str, background_tasks: BackgroundTasks):
    """Manually trigger healing for a service."""
    service = registry.get(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {name} not found")
    
    # Diagnose
    diagnosis = failure_analyzer.diagnose(service)
    knowledge_base.record_diagnosis(diagnosis)
    
    # Heal
    outcome = healing_executor.heal(service, diagnosis)
    knowledge_base.record_outcome(outcome)
    
    return {
        "diagnosis": diagnosis.to_dict(),
        "outcome": outcome.to_dict(),
    }


@app.get("/api/services/{name}/diagnose")
async def diagnose_service(name: str):
    """Diagnose issues with a service without healing."""
    service = registry.get(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {name} not found")
    
    diagnosis = failure_analyzer.diagnose(service)
    return diagnosis.to_dict()


# =============================================================================
# Knowledge Base Endpoints
# =============================================================================

@app.get("/api/outcomes")
async def get_outcomes(limit: int = 50, service: Optional[str] = None):
    """Get healing outcome history."""
    return knowledge_base.get_recent_outcomes(limit=limit, service_name=service)


@app.get("/api/diagnoses")
async def get_diagnoses(limit: int = 50):
    """Get recent failure diagnoses."""
    return [d.to_dict() for d in failure_analyzer.get_recent_diagnoses(limit)]


@app.get("/api/patterns")
async def get_patterns(flagged_only: bool = False):
    """Get recurring failure patterns."""
    return knowledge_base.get_recurring_patterns(flagged_only=flagged_only)


@app.get("/api/metrics")
async def get_metrics():
    """Get healing metrics and statistics."""
    return {
        "knowledge_base": knowledge_base.get_stats(),
        "healing": healing_executor.get_stats(),
    }


# =============================================================================
# Escalation Endpoints
# =============================================================================

@app.get("/api/alerts")
async def get_alerts(limit: int = 50):
    """Get recent alerts."""
    return escalation_manager.get_recent_alerts(limit)


@app.post("/api/services/{name}/suppress")
async def suppress_alerts(name: str, request: SuppressRequest):
    """Suppress alerts for a service temporarily."""
    if not registry.get(name):
        raise HTTPException(status_code=404, detail=f"Service {name} not found")
    
    escalation_manager.suppress_alerts(name, request.duration_minutes)
    return {"status": "suppressed", "service": name, "duration_minutes": request.duration_minutes}


@app.post("/api/services/{name}/unsuppress")
async def unsuppress_alerts(name: str):
    """Remove alert suppression for a service."""
    escalation_manager.unsuppress_alerts(name)
    return {"status": "unsuppressed", "service": name}


@app.get("/api/suppressed")
async def get_suppressed():
    """Get list of services with suppressed alerts."""
    return escalation_manager.get_suppressed_services()


# =============================================================================
# God Mode Integration Endpoint
# =============================================================================

@app.get("/api/god-mode-status")
async def god_mode_status():
    """
    Endpoint for God Mode dashboard integration.
    Returns a summary suitable for display.
    """
    health = health_checker.get_summary()
    stats = knowledge_base.get_stats()
    
    # Get critical issues
    critical_down = health_checker.get_critical_down()
    
    # Get recent healing activity
    recent_outcomes = knowledge_base.get_recent_outcomes(limit=5)
    
    return {
        "status": "active" if health["critical_down"] == 0 else "alert",
        "health_score": health["health_score"],
        "services": {
            "total": health["total_services"],
            "healthy": health["healthy"],
            "unhealthy": health["unhealthy"],
            "critical_down": health["critical_down"],
        },
        "healing": {
            "total_attempts": stats["total_healing_attempts"],
            "success_rate": stats["overall_success_rate"],
            "recent_activity": [
                {
                    "service": o["service_name"],
                    "action": o["action_name"],
                    "result": o["result"],
                    "time": o["timestamp"],
                }
                for o in recent_outcomes
            ],
        },
        "critical_services_down": [
            {
                "name": r.service_name,
                "error": r.error,
                "down_since": escalation_manager.service_down_since.get(r.service_name, datetime.now()).isoformat(),
            }
            for r in critical_down
        ],
        "flagged_patterns": stats.get("flagged_patterns", 0),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)











