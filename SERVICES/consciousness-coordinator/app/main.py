"""
Consciousness Coordinator - The Central Nervous System
======================================================

Connects all consciousness components into a unified perception-decision-action-verification loop.

Port: 8190
Server: Secondary (162.0.208.88)

Architecture:
    Perception (God Mode) -> Decision (This Service + Decision Engine) -> Action (ARIA/Builder/I-Match) -> Verification (Verifier/Evolution)
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# ==================== CONFIGURATION ====================

# Service URLs
GOD_MODE_URL = os.getenv("GOD_MODE_URL", "http://198.54.123.234:8300")
DECISION_ENGINE_URL = os.getenv("DECISION_ENGINE_URL", "http://localhost:8150")
OPTIMIZER_URL = os.getenv("OPTIMIZER_URL", "http://localhost:8160")
ARIA_URL = os.getenv("ARIA_URL", "http://localhost:8180")
VERIFIER_URL = os.getenv("VERIFIER_URL", "http://localhost:8230")
EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://localhost:8140")
IMATCH_URL = os.getenv("IMATCH_URL", "http://198.54.123.234:8401")
BUILDER_URL = os.getenv("BUILDER_URL", "http://localhost:8120")

# Cycle configuration
CYCLE_INTERVAL_SECONDS = int(os.getenv("CYCLE_INTERVAL_SECONDS", "60"))
MAX_ACTIONS_PER_CYCLE = int(os.getenv("MAX_ACTIONS_PER_CYCLE", "5"))

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("consciousness-coordinator")

# ==================== DATA MODELS ====================

class ActionType(str, Enum):
    RESTART_SERVICE = "restart_service"
    QUEUE_IMPROVEMENT = "queue_improvement"
    TRIGGER_MATCHING = "trigger_matching"
    ALERT_HUMAN = "alert_human"
    LOG_LEARNING = "log_learning"
    RUN_EVOLUTION = "run_evolution"

class ActionPriority(str, Enum):
    CRITICAL = "critical"  # Execute immediately
    HIGH = "high"          # Execute this cycle
    MEDIUM = "medium"      # Execute when resources available
    LOW = "low"            # Batch for later

class Action(BaseModel):
    id: str
    type: ActionType
    priority: ActionPriority
    target: str
    description: str
    parameters: Dict[str, Any] = {}
    created_at: datetime = None
    executed_at: Optional[datetime] = None
    result: Optional[str] = None
    
    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.utcnow()
        super().__init__(**data)

class ConsciousnessState(BaseModel):
    cycle_count: int = 0
    last_cycle_at: Optional[datetime] = None
    actions_taken_today: int = 0
    improvements_queued: int = 0
    matches_triggered: int = 0
    services_restarted: int = 0
    learnings_logged: int = 0
    health_score: float = 0.0
    issues_detected: int = 0
    opportunities_identified: int = 0
    is_running: bool = False

class CycleResult(BaseModel):
    cycle_id: int
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    perception: Dict[str, Any]
    decisions_made: int
    actions_taken: List[Dict[str, Any]]
    errors: List[str] = []

# ==================== GLOBAL STATE ====================

STATE = ConsciousnessState()
ACTION_LOG: List[Action] = []
CYCLE_HISTORY: List[CycleResult] = []
PENDING_ACTIONS: List[Action] = []

# ==================== HTTP CLIENT ====================

async def safe_get(url: str, timeout: float = 5.0) -> Optional[Dict]:
    """Safe HTTP GET with error handling."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"GET {url} returned {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"GET {url} failed: {e}")
        return None

async def safe_post(url: str, data: Dict = None, timeout: float = 10.0) -> Optional[Dict]:
    """Safe HTTP POST with error handling."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=data or {})
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.warning(f"POST {url} returned {response.status_code}: {response.text[:200]}")
                return None
    except Exception as e:
        logger.error(f"POST {url} failed: {e}")
        return None

# ==================== PERCEPTION ====================

async def perceive() -> Dict[str, Any]:
    """Gather perception from God Mode and other sources."""
    perception = {
        "timestamp": datetime.utcnow().isoformat(),
        "god_mode": None,
        "aria": None,
        "imatch": None,
        "services_healthy": 0,
        "services_total": 0,
        "issues": [],
        "opportunities": [],
    }
    
    # Get God Mode overview
    god_mode = await safe_get(f"{GOD_MODE_URL}/api/overview")
    if god_mode:
        perception["god_mode"] = god_mode
        metrics = god_mode.get("metrics", {})
        perception["services_healthy"] = metrics.get("services_healthy", 0)
        perception["services_total"] = metrics.get("services_total", 0)
        perception["health_score"] = metrics.get("health_score", 0)
    
    # Get God Mode intelligence (issues + opportunities)
    intelligence = await safe_get(f"{GOD_MODE_URL}/api/intelligence")
    if intelligence:
        perception["issues"] = intelligence.get("issues", [])
        perception["opportunities"] = intelligence.get("opportunities", [])
    
    # Get ARIA status
    aria = await safe_get(f"{ARIA_URL}/stats")
    if aria:
        perception["aria"] = aria
    
    # Get I-Match status
    imatch = await safe_get(f"{IMATCH_URL}/state")
    if imatch:
        perception["imatch"] = imatch
    
    return perception

# ==================== DECISION ====================

async def decide(perception: Dict[str, Any]) -> List[Action]:
    """Analyze perception and decide on actions."""
    actions = []
    action_id_counter = 0
    
    def new_action_id():
        nonlocal action_id_counter
        action_id_counter += 1
        return f"action_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{action_id_counter}"
    
    # Check for critical issues (services down)
    for issue in perception.get("issues", []):
        severity = issue.get("severity", "info")
        message = issue.get("message", "")
        
        if severity == "critical" and "down" in message.lower():
            # Extract service name from message
            service_name = message.replace(" is down", "").replace("is down", "").strip()
            actions.append(Action(
                id=new_action_id(),
                type=ActionType.RESTART_SERVICE,
                priority=ActionPriority.CRITICAL,
                target=service_name,
                description=f"Restart {service_name} - detected as down",
                parameters={"service": service_name}
            ))
    
    # Check ARIA for needed improvements
    aria_stats = perception.get("aria", {})
    if aria_stats:
        fallback_rate = aria_stats.get("fallback_rate", 0)
        error_rate = aria_stats.get("failed_responses", 0) / max(1, aria_stats.get("total_conversations", 1))
        
        if fallback_rate > 0.1:
            actions.append(Action(
                id=new_action_id(),
                type=ActionType.QUEUE_IMPROVEMENT,
                priority=ActionPriority.MEDIUM,
                target="aria",
                description=f"ARIA fallback rate is {fallback_rate:.1%} - queue quality improvement",
                parameters={
                    "area": "quality_scoring",
                    "description": f"Reduce ARIA fallback rate from {fallback_rate:.1%} to under 10%"
                }
            ))
        
        if error_rate > 0.05:
            actions.append(Action(
                id=new_action_id(),
                type=ActionType.QUEUE_IMPROVEMENT,
                priority=ActionPriority.HIGH,
                target="aria",
                description=f"ARIA error rate is {error_rate:.1%} - queue error handling improvement",
                parameters={
                    "area": "error_handling",
                    "description": f"Improve ARIA error handling - current error rate {error_rate:.1%}"
                }
            ))
    
    # Check I-Match for pending matches or customers
    imatch = perception.get("imatch", {})
    if imatch:
        customers = imatch.get("customers_active", 0)
        matches_pending = imatch.get("matches_pending", 0)
        
        # If there are customers but no pending/completed matches, trigger matching
        if customers > 0 and matches_pending == 0:
            actions.append(Action(
                id=new_action_id(),
                type=ActionType.TRIGGER_MATCHING,
                priority=ActionPriority.HIGH,
                target="imatch",
                description=f"Trigger matching for {customers} active customers",
                parameters={"customer_count": customers}
            ))
    
    # Check health score
    health_score = perception.get("health_score", 100)
    if health_score < 70:
        actions.append(Action(
            id=new_action_id(),
            type=ActionType.ALERT_HUMAN,
            priority=ActionPriority.HIGH,
            target="human",
            description=f"System health score is {health_score}/100 - needs attention",
            parameters={"health_score": health_score}
        ))
    
    # Log learnings if cycle was successful
    if perception.get("services_healthy", 0) == perception.get("services_total", 0) and perception.get("services_total", 0) > 0:
        actions.append(Action(
            id=new_action_id(),
            type=ActionType.LOG_LEARNING,
            priority=ActionPriority.LOW,
            target="evolution",
            description="Log successful cycle to evolution service",
            parameters={
                "health_score": health_score,
                "services_total": perception.get("services_total", 0)
            }
        ))
    
    # Sort by priority
    priority_order = {
        ActionPriority.CRITICAL: 0,
        ActionPriority.HIGH: 1,
        ActionPriority.MEDIUM: 2,
        ActionPriority.LOW: 3
    }
    actions.sort(key=lambda a: priority_order.get(a.priority, 99))
    
    return actions[:MAX_ACTIONS_PER_CYCLE]

# ==================== ACTION ====================

async def execute_action(action: Action) -> bool:
    """Execute a single action."""
    logger.info(f"Executing action: {action.type.value} on {action.target}")
    
    try:
        if action.type == ActionType.RESTART_SERVICE:
            # Call God Mode to restart service
            result = await safe_post(
                f"{GOD_MODE_URL}/api/services/{action.target}/restart",
                timeout=30.0
            )
            action.result = "restarted" if result else "failed"
            STATE.services_restarted += 1 if result else 0
            return result is not None
            
        elif action.type == ActionType.QUEUE_IMPROVEMENT:
            # Call ARIA to queue improvement
            result = await safe_post(
                f"{ARIA_URL}/improvements/trigger",
                timeout=15.0
            )
            action.result = "queued" if result else "failed"
            STATE.improvements_queued += 1 if result else 0
            return result is not None
            
        elif action.type == ActionType.TRIGGER_MATCHING:
            # Trigger I-Match matching (would need to implement customer iteration)
            # For now, just log that we would trigger matching
            logger.info(f"Would trigger matching for {action.parameters.get('customer_count', 0)} customers")
            action.result = "logged"
            STATE.matches_triggered += 1
            return True
            
        elif action.type == ActionType.ALERT_HUMAN:
            # Log alert (in production, send to notification service)
            logger.warning(f"HUMAN ALERT: {action.description}")
            action.result = "alerted"
            return True
            
        elif action.type == ActionType.LOG_LEARNING:
            # Log to evolution service
            result = await safe_post(
                f"{EVOLUTION_URL}/log",
                data=action.parameters,
                timeout=10.0
            )
            action.result = "logged" if result else "failed"
            STATE.learnings_logged += 1 if result else 0
            return True  # Don't fail cycle if evolution logging fails
            
        elif action.type == ActionType.RUN_EVOLUTION:
            # Trigger evolution run
            result = await safe_post(f"{EVOLUTION_URL}/run", timeout=60.0)
            action.result = "ran" if result else "failed"
            return result is not None
            
        else:
            logger.warning(f"Unknown action type: {action.type}")
            action.result = "unknown_type"
            return False
            
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        action.result = f"error: {str(e)[:100]}"
        return False
    finally:
        action.executed_at = datetime.utcnow()
        ACTION_LOG.append(action)

# ==================== CONSCIOUSNESS CYCLE ====================

async def run_cycle() -> CycleResult:
    """Run one complete consciousness cycle."""
    STATE.cycle_count += 1
    cycle_id = STATE.cycle_count
    started_at = datetime.utcnow()
    errors = []
    actions_taken = []
    
    logger.info(f"=== Starting Consciousness Cycle {cycle_id} ===")
    
    try:
        # 1. PERCEIVE
        logger.info("Phase 1: Perception")
        perception = await perceive()
        STATE.health_score = perception.get("health_score", 0)
        STATE.issues_detected = len(perception.get("issues", []))
        STATE.opportunities_identified = len(perception.get("opportunities", []))
        
        # 2. DECIDE
        logger.info("Phase 2: Decision")
        actions = await decide(perception)
        logger.info(f"Decided on {len(actions)} actions")
        
        # 3. ACT
        logger.info("Phase 3: Action")
        for action in actions:
            success = await execute_action(action)
            actions_taken.append({
                "id": action.id,
                "type": action.type.value,
                "target": action.target,
                "success": success,
                "result": action.result
            })
            STATE.actions_taken_today += 1
        
        # 4. VERIFY (implicit - next cycle will perceive results)
        logger.info("Phase 4: Verification scheduled for next cycle")
        
    except Exception as e:
        logger.error(f"Cycle error: {e}")
        errors.append(str(e))
    
    completed_at = datetime.utcnow()
    STATE.last_cycle_at = completed_at
    
    result = CycleResult(
        cycle_id=cycle_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=(completed_at - started_at).total_seconds(),
        perception=perception,
        decisions_made=len(actions),
        actions_taken=actions_taken,
        errors=errors
    )
    
    CYCLE_HISTORY.append(result)
    
    # Keep only last 100 cycles
    if len(CYCLE_HISTORY) > 100:
        CYCLE_HISTORY.pop(0)
    
    logger.info(f"=== Cycle {cycle_id} complete in {result.duration_seconds:.2f}s ===")
    return result

# ==================== BACKGROUND LOOP ====================

async def consciousness_loop():
    """Main consciousness loop - runs continuously."""
    STATE.is_running = True
    logger.info(f"Consciousness loop started. Cycle interval: {CYCLE_INTERVAL_SECONDS}s")
    
    while STATE.is_running:
        try:
            await run_cycle()
        except Exception as e:
            logger.error(f"Consciousness loop error: {e}")
        
        await asyncio.sleep(CYCLE_INTERVAL_SECONDS)

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management."""
    logger.info("Consciousness Coordinator starting...")
    
    # Start background consciousness loop
    loop_task = asyncio.create_task(consciousness_loop())
    
    yield
    
    # Shutdown
    STATE.is_running = False
    loop_task.cancel()
    logger.info("Consciousness Coordinator stopped")

app = FastAPI(
    title="Consciousness Coordinator",
    description="Central nervous system connecting perception, decision, action, and verification",
    version="1.0.0",
    lifespan=lifespan
)

# ==================== ENDPOINTS ====================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy" if STATE.is_running else "starting",
        "service": "consciousness-coordinator",
        "version": "1.0.0",
        "cycle_count": STATE.cycle_count,
        "last_cycle_at": STATE.last_cycle_at.isoformat() if STATE.last_cycle_at else None,
        "is_running": STATE.is_running
    }

@app.get("/state")
async def get_state():
    """Get current consciousness state."""
    return {
        **STATE.model_dump(),
        "last_cycle_at": STATE.last_cycle_at.isoformat() if STATE.last_cycle_at else None,
        "pending_actions": len(PENDING_ACTIONS),
        "action_log_size": len(ACTION_LOG)
    }

@app.post("/cycle")
async def trigger_cycle():
    """Manually trigger a consciousness cycle."""
    result = await run_cycle()
    return result.model_dump()

@app.get("/log")
async def get_action_log(limit: int = 50):
    """Get recent action log."""
    return {
        "total": len(ACTION_LOG),
        "actions": [
            {
                "id": a.id,
                "type": a.type.value,
                "priority": a.priority.value,
                "target": a.target,
                "description": a.description,
                "result": a.result,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "executed_at": a.executed_at.isoformat() if a.executed_at else None
            }
            for a in ACTION_LOG[-limit:]
        ]
    }

@app.get("/cycles")
async def get_cycle_history(limit: int = 10):
    """Get recent cycle history."""
    return {
        "total": len(CYCLE_HISTORY),
        "cycles": [
            {
                "cycle_id": c.cycle_id,
                "started_at": c.started_at.isoformat(),
                "completed_at": c.completed_at.isoformat(),
                "duration_seconds": c.duration_seconds,
                "decisions_made": c.decisions_made,
                "actions_taken": len(c.actions_taken),
                "errors": c.errors
            }
            for c in CYCLE_HISTORY[-limit:]
        ]
    }

@app.get("/metrics")
async def get_metrics():
    """Get consciousness metrics for dashboards."""
    return {
        "consciousness_score": calculate_consciousness_score(),
        "cycle_count": STATE.cycle_count,
        "actions_today": STATE.actions_taken_today,
        "improvements_queued": STATE.improvements_queued,
        "matches_triggered": STATE.matches_triggered,
        "services_restarted": STATE.services_restarted,
        "learnings_logged": STATE.learnings_logged,
        "health_score": STATE.health_score,
        "issues_detected": STATE.issues_detected,
        "is_active": STATE.is_running and STATE.last_cycle_at is not None
    }

def calculate_consciousness_score() -> float:
    """Calculate overall consciousness score (0-10)."""
    score = 0.0
    
    # Is the loop running? (+2)
    if STATE.is_running and STATE.last_cycle_at:
        score += 2.0
    
    # Recent cycle? (+2)
    if STATE.last_cycle_at and (datetime.utcnow() - STATE.last_cycle_at).seconds < 120:
        score += 2.0
    
    # Taking actions? (+2)
    if STATE.actions_taken_today > 0:
        score += min(2.0, STATE.actions_taken_today * 0.2)
    
    # Health score good? (+2)
    if STATE.health_score >= 80:
        score += 2.0
    elif STATE.health_score >= 60:
        score += 1.0
    
    # Self-improving? (+2)
    if STATE.improvements_queued > 0:
        score += min(2.0, STATE.improvements_queued * 0.5)
    
    return min(10.0, score)

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8190)





