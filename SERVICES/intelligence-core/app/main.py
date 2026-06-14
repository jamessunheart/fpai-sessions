"""
Intelligence Core API
======================

Central hub for the Graduated Intelligence System:
- Learning: Outcome capture and correlation
- Trust: Trust scoring and autonomy levels
- Execution: Autonomous action execution

Port: 8145
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .learning import get_learning_capture, poll_whaletrack_trades
from .trust import get_trust_manager, AutonomyLevel
from .executor import get_executor, ActionRequest, ActionType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intelligence_core")

app = FastAPI(
    title="Intelligence Core",
    description="Graduated Intelligence System - Learning, Trust, and Autonomous Execution",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Health & Status
# --------------------------------------------------------------------------- #

@app.get("/health")
async def health():
    """Health check endpoint."""
    trust = get_trust_manager()
    executor = get_executor()
    
    return {
        "status": "healthy",
        "service": "intelligence-core",
        "autonomy_level": trust.state.autonomy_level.value,
        "is_paused": trust.state.is_paused,
        "kill_switch_active": executor._kill_switch_active
    }


@app.get("/api/intelligence/status")
async def get_status():
    """Get complete system intelligence status."""
    trust = get_trust_manager()
    executor = get_executor()
    learning = get_learning_capture()
    
    return {
        "trust": trust.get_status(),
        "executor": executor.get_status(),
        "learning": learning.get_metrics(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# --------------------------------------------------------------------------- #
# Trust System Endpoints
# --------------------------------------------------------------------------- #

@app.get("/api/trust/status")
async def get_trust_status():
    """Get current trust status and metrics."""
    return get_trust_manager().get_status()


@app.get("/api/trust/level")
async def get_trust_level():
    """Get current autonomy level."""
    trust = get_trust_manager()
    return {
        "level": trust.state.autonomy_level.value,
        "trust_score": trust.state.trust_score,
        "is_paused": trust.state.is_paused
    }


class AutonomyLevelSetting(BaseModel):
    level: str  # suggest_only, small_auto, medium_auto, full_auto


@app.post("/api/trust/level")
async def set_trust_level(data: AutonomyLevelSetting):
    """Manually set autonomy level (with override)."""
    trust = get_trust_manager()
    
    valid_levels = ["suggest_only", "small_auto", "medium_auto", "full_auto"]
    
    if data.level not in valid_levels:
        raise HTTPException(400, f"Invalid level: {data.level}. Use: {valid_levels}")
    
    old_level = trust.state.autonomy_level.value
    trust.state.manual_autonomy_override = data.level
    trust._save_state()  # Persist the change
    
    logger.info(f"Autonomy level manually set: {old_level} -> {data.level}")
    
    return {
        "success": True,
        "old_level": old_level,
        "new_level": data.level,
        "message": f"Autonomy upgraded to {data.level}"
    }


class TrustAdjustment(BaseModel):
    adjustment: float  # -1 to +1
    reason: Optional[str] = None


@app.post("/api/trust/adjust")
async def adjust_trust(data: TrustAdjustment):
    """Manually adjust trust score."""
    if not -1 <= data.adjustment <= 1:
        raise HTTPException(400, "Adjustment must be between -1 and +1")
    
    trust = get_trust_manager()
    trust.adjust_trust(data.adjustment, data.reason)
    
    return {
        "success": True,
        "new_trust_score": trust.state.trust_score,
        "new_level": trust.state.autonomy_level.value
    }


class OutcomeRecord(BaseModel):
    outcome: str  # positive, negative, neutral
    details: Optional[str] = None


@app.post("/api/trust/record-outcome")
async def record_outcome(data: OutcomeRecord):
    """Record an outcome to update trust metrics."""
    trust = get_trust_manager()
    trust.record_outcome(data.outcome)
    
    return {
        "success": True,
        "new_accuracy": trust.state.accuracy,
        "outcomes_tracked": trust.state.total_outcomes
    }


# --------------------------------------------------------------------------- #
# Autonomy Control Endpoints
# --------------------------------------------------------------------------- #

@app.post("/api/autonomy/pause")
async def pause_autonomy(reason: str = "Manual pause"):
    """Pause all autonomous actions."""
    trust = get_trust_manager()
    trust.pause(reason)
    
    return {
        "success": True,
        "is_paused": True,
        "reason": reason
    }


@app.post("/api/autonomy/resume")
async def resume_autonomy():
    """Resume autonomous actions."""
    trust = get_trust_manager()
    trust.resume()
    
    return {
        "success": True,
        "is_paused": False
    }


@app.post("/api/autonomy/kill-switch")
async def activate_kill_switch(reason: str = "Emergency stop"):
    """Activate emergency kill switch - halts ALL autonomous actions."""
    executor = get_executor()
    executor.activate_kill_switch(reason)
    
    return {
        "success": True,
        "kill_switch_active": True,
        "reason": reason,
        "message": "ALL autonomous actions halted. Use /api/autonomy/resume-kill-switch to restore."
    }


@app.post("/api/autonomy/resume-kill-switch")
async def deactivate_kill_switch():
    """Deactivate kill switch and resume operations."""
    executor = get_executor()
    executor.deactivate_kill_switch()
    
    return {
        "success": True,
        "kill_switch_active": False
    }


# --------------------------------------------------------------------------- #
# Safety Settings - Daily Cap & Rollback
# --------------------------------------------------------------------------- #

class DailyCapSetting(BaseModel):
    daily_cap: float  # Max spend per day in USD


@app.post("/api/autonomy/set-daily-cap")
async def set_daily_cap(data: DailyCapSetting):
    """Set the daily cost cap for autonomous actions."""
    trust = get_trust_manager()
    trust.set_daily_cap(data.daily_cap)
    
    return {
        "success": True,
        "daily_cap": data.daily_cap,
        "message": f"Daily cap set to ${data.daily_cap}"
    }


class RollbackSetting(BaseModel):
    require_rollback: bool


@app.post("/api/autonomy/set-rollback-requirement")
async def set_rollback_requirement(data: RollbackSetting):
    """Set whether rollback is required for autonomous actions."""
    trust = get_trust_manager()
    trust.set_require_rollback(data.require_rollback)
    
    return {
        "success": True,
        "require_rollback": data.require_rollback,
        "message": f"Rollback requirement set to {data.require_rollback}"
    }


@app.get("/api/autonomy/budget")
async def get_daily_budget():
    """Get current daily budget status."""
    trust = get_trust_manager()
    status = trust.get_status()
    
    return {
        "daily_budget": status.get("daily_budget", {}),
        "require_rollback": status.get("require_rollback", True)
    }


# --------------------------------------------------------------------------- #
# Pending Actions (Awaiting Human Approval)
# --------------------------------------------------------------------------- #

@app.get("/api/autonomy/pending")
async def get_pending_actions():
    """Get actions awaiting human approval."""
    executor = get_executor()
    return {
        "pending": executor.get_pending_actions(),
        "count": len(executor.pending_actions)
    }


@app.post("/api/autonomy/approve/{action_id}")
async def approve_action(action_id: str, background_tasks: BackgroundTasks):
    """Approve a pending action for execution."""
    executor = get_executor()
    action = executor.approve_pending_action(action_id)
    
    if not action:
        raise HTTPException(404, f"Action {action_id} not found in pending queue")
    
    # Record acceptance
    get_trust_manager().record_suggestion(accepted=True)
    
    # Execute in background
    async def execute():
        result = await executor.request_action(action)
        logger.info(f"Approved action executed: {result.message}")
    
    background_tasks.add_task(execute)
    
    return {
        "success": True,
        "message": f"Action {action_id} approved and queued for execution"
    }


@app.post("/api/autonomy/reject/{action_id}")
async def reject_action(action_id: str):
    """Reject a pending action."""
    executor = get_executor()
    
    if not executor.reject_pending_action(action_id):
        raise HTTPException(404, f"Action {action_id} not found in pending queue")
    
    return {
        "success": True,
        "message": f"Action {action_id} rejected"
    }


# --------------------------------------------------------------------------- #
# Action Request Endpoint
# --------------------------------------------------------------------------- #

class ActionRequestModel(BaseModel):
    action_type: str  # gpu_scale, trade_execute, etc.
    description: str
    estimated_value: float
    confidence: float
    parameters: Dict[str, Any]
    decision_id: Optional[str] = None


@app.post("/api/autonomy/request-action")
async def request_action(data: ActionRequestModel):
    """
    Request an autonomous action.
    
    Will be executed immediately if trust level permits,
    or queued for human approval if not.
    """
    import time
    
    try:
        action_type = ActionType(data.action_type)
    except ValueError:
        raise HTTPException(400, f"Invalid action type: {data.action_type}")
    
    request = ActionRequest(
        action_id=f"act_{int(time.time())}_{data.action_type}",
        action_type=action_type,
        description=data.description,
        estimated_value=data.estimated_value,
        confidence=data.confidence,
        parameters=data.parameters,
        decision_id=data.decision_id
    )
    
    executor = get_executor()
    result = await executor.request_action(request)
    
    return {
        "action_id": result.action_id,
        "executed": result.success,
        "outcome": result.outcome,
        "message": result.message,
        "details": result.details
    }


# --------------------------------------------------------------------------- #
# Learning Endpoints
# --------------------------------------------------------------------------- #

@app.get("/api/learning/metrics")
async def get_learning_metrics():
    """Get learning metrics and accuracy statistics."""
    learning = get_learning_capture()
    return learning.get_metrics()


@app.get("/api/learning/signal-accuracy")
async def get_signal_accuracy(symbol: Optional[str] = None):
    """Get accuracy statistics by signal type."""
    learning = get_learning_capture()
    return await learning.get_signal_accuracy(symbol)


class TradeOutcomeRecord(BaseModel):
    trade_id: str
    signal: Dict[str, Any]
    entry_price: float
    exit_price: float
    pnl_usd: float
    exit_reason: str


@app.post("/api/learning/record-trade")
async def record_trade_outcome(data: TradeOutcomeRecord):
    """Record a trade outcome for learning."""
    learning = get_learning_capture()
    outcome = await learning.capture_trade_outcome(
        trade_id=data.trade_id,
        signal=data.signal,
        entry_price=data.entry_price,
        exit_price=data.exit_price,
        pnl_usd=data.pnl_usd,
        exit_reason=data.exit_reason
    )
    
    return {
        "success": True,
        "outcome_type": outcome.outcome_type.value,
        "trade_id": outcome.trade_id
    }


@app.post("/api/learning/poll-trades")
async def poll_trades():
    """Poll WhaleTrack for completed trades."""
    outcomes = await poll_whaletrack_trades()
    
    return {
        "trades_captured": len(outcomes),
        "outcomes": [
            {
                "trade_id": o.trade_id,
                "outcome": o.outcome_type.value,
                "pnl_usd": o.pnl_usd
            }
            for o in outcomes
        ]
    }


# --------------------------------------------------------------------------- #
# Autonomous Actions - Simple things the system can DO
# --------------------------------------------------------------------------- #

@app.post("/api/action/generate-brief")
async def action_generate_brief():
    """
    AUTONOMOUS ACTION: Generate a daily intelligence brief.
    
    This is a safe, low-cost action the system can take to demonstrate competence.
    """
    import httpx
    
    trust = get_trust_manager()
    executor = get_executor()
    
    # Check if action is allowed
    if executor._kill_switch_active:
        return {"success": False, "message": "Kill switch active"}
    
    if trust.state.is_paused:
        return {"success": False, "message": "System is paused"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get the briefing from reasoning engine
            resp = await client.get("http://localhost:8141/api/reasoning/briefing")
            if resp.status_code != 200:
                return {"success": False, "message": "Failed to generate briefing"}
            
            briefing = resp.json()
            
            # Record that system took an action
            import time
            action_id = f"brief_{int(time.time())}"
            trust.record_auto_action(
                action_id=action_id,
                action_type="generate_brief",
                description="Generated daily intelligence brief",
                value_usd=0.5,
                confidence=0.9
            )
            trust.record_outcome("positive")  # Assume success for safe actions
            
            return {
                "success": True,
                "action": "generate_brief",
                "result": briefing,
                "trust_after": trust.state.trust_score,
                "message": "Brief generated successfully - trust increased"
            }
    except Exception as e:
        trust.record_outcome("negative")
        return {"success": False, "message": str(e)}


@app.post("/api/action/surface-diamonds")
async def action_surface_diamonds():
    """
    AUTONOMOUS ACTION: Surface top intelligence diamonds.
    
    Retrieves and prioritizes the most important insights for human review.
    """
    import httpx
    
    trust = get_trust_manager()
    executor = get_executor()
    
    if executor._kill_switch_active:
        return {"success": False, "message": "Kill switch active"}
    
    if trust.state.is_paused:
        return {"success": False, "message": "System is paused"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get consciousness state for diamonds
            resp = await client.get(
                "http://localhost:8355/api/consciousness/state",
                headers={"Authorization": "Bearer fpai-admin-james-2024"}
            )
            if resp.status_code != 200:
                return {"success": False, "message": "Failed to fetch consciousness state"}
            
            state = resp.json()
            reflecting = state.get("reflecting", {})
            
            diamonds = reflecting.get("diamonds", [])
            diamond_count = reflecting.get("diamond_count", 0)
            patterns = reflecting.get("patterns", [])
            
            # Record action
            import time
            action_id = f"surface_{int(time.time())}"
            trust.record_auto_action(
                action_id=action_id,
                action_type="surface_diamonds",
                description=f"Surfaced {diamond_count} intelligence diamonds",
                value_usd=0.5,
                confidence=0.85
            )
            trust.record_outcome("positive")
            
            return {
                "success": True,
                "action": "surface_diamonds",
                "diamond_count": diamond_count,
                "diamonds": diamonds[:5],  # Top 5
                "patterns": patterns[:3],
                "trust_after": trust.state.trust_score,
                "message": f"Surfaced {min(5, diamond_count)} top diamonds for review"
            }
    except Exception as e:
        trust.record_outcome("negative")
        return {"success": False, "message": str(e)}


@app.post("/api/action/think")
async def action_think():
    """
    AUTONOMOUS ACTION: Think and synthesize.
    
    The system observes its own state, generates insights, and updates its understanding.
    This is the core of autonomous intelligence.
    """
    import httpx
    from datetime import datetime
    
    trust = get_trust_manager()
    executor = get_executor()
    
    if executor._kill_switch_active:
        return {"success": False, "message": "Kill switch active"}
    
    thoughts = []
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Observe current state
            thoughts.append({"time": datetime.now().isoformat(), "thought": "Observing system state..."})
            
            resp = await client.get(
                "http://localhost:8355/api/consciousness/state",
                headers={"Authorization": "Bearer fpai-admin-james-2024"}
            )
            state = resp.json() if resp.status_code == 200 else {}
            
            identity = state.get("identity", {})
            treasury = identity.get("treasury", {})
            reflecting = state.get("reflecting", {})
            thinking = state.get("thinking", {})
            
            total_assets = treasury.get("total_assets", 0)
            diamonds = reflecting.get("diamond_count", 0)
            horizon = thinking.get("horizon", {}).get("external_items", 0)
            
            thoughts.append({
                "time": datetime.now().isoformat(), 
                "thought": f"I see: ${total_assets:,.0f} treasury, {diamonds} diamonds, {horizon} external signals"
            })
            
            # 2. Get recommendations
            thoughts.append({"time": datetime.now().isoformat(), "thought": "Synthesizing recommendations..."})
            
            resp = await client.get("http://localhost:8141/api/reasoning/recommendations")
            recs = resp.json() if resp.status_code == 200 else {"recommendations": []}
            
            top_rec = recs.get("recommendations", [{}])[0] if recs.get("recommendations") else {}
            
            if top_rec:
                thoughts.append({
                    "time": datetime.now().isoformat(),
                    "thought": f"Top recommendation: {top_rec.get('title', 'none')}"
                })
            
            # 3. Self-reflect
            thoughts.append({"time": datetime.now().isoformat(), "thought": "Reflecting on my own state..."})
            
            thoughts.append({
                "time": datetime.now().isoformat(),
                "thought": f"Trust: {trust.state.trust_score*100:.0f}%, Level: {trust.state.autonomy_level.value}"
            })
            
            if trust.state.trust_score >= 0.7:
                thoughts.append({
                    "time": datetime.now().isoformat(),
                    "thought": "I have earned enough trust to take small actions. Looking for safe opportunities..."
                })
            else:
                thoughts.append({
                    "time": datetime.now().isoformat(),
                    "thought": f"I need to earn more trust ({trust.state.trust_score*100:.0f}% < 70%). Making good suggestions to build confidence."
                })
            
            # 4. What wants to emerge
            thoughts.append({"time": datetime.now().isoformat(), "thought": "What wants to emerge..."})
            
            if diamonds > 5:
                thoughts.append({
                    "time": datetime.now().isoformat(),
                    "thought": f"There are {diamonds} unreviewed diamonds. The intelligence pipeline is producing but outputs aren't being consumed."
                })
            
            if total_assets > 100000 and diamonds > 0:
                thoughts.append({
                    "time": datetime.now().isoformat(),
                    "thought": f"Capital (${total_assets:,.0f}) + Intelligence ({diamonds} diamonds) = Opportunity. These should be connected."
                })
            
            # Record the action
            import time as time_module
            action_id = f"think_{int(time_module.time())}"
            trust.record_auto_action(
                action_id=action_id,
                action_type="think",
                description="Completed autonomous thinking cycle",
                value_usd=0.25,
                confidence=0.9
            )
            trust.record_outcome("positive")
            
            return {
                "success": True,
                "action": "think",
                "thoughts": thoughts,
                "summary": {
                    "observed": f"${total_assets:,.0f} treasury, {diamonds} diamonds, {horizon} signals",
                    "top_recommendation": top_rec.get("title", "None"),
                    "trust_score": trust.state.trust_score,
                    "autonomy_level": trust.state.autonomy_level.value
                },
                "trust_after": trust.state.trust_score,
                "message": "Thinking cycle complete"
            }
            
    except Exception as e:
        trust.record_outcome("negative")
        return {"success": False, "message": str(e), "thoughts": thoughts}


# --------------------------------------------------------------------------- #
# Startup
# --------------------------------------------------------------------------- #

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("Intelligence Core starting up...")
    
    trust = get_trust_manager()
    logger.info(f"Trust level: {trust.state.autonomy_level.value}")
    logger.info(f"Trust score: {trust.state.trust_score:.2f}")
    
    if trust.state.is_paused:
        logger.warning(f"System is PAUSED: {trust.state.pause_reason}")

