#!/usr/bin/env python3
"""
Graduated Intelligence Loop
============================

The main daemon that runs the full intelligence cycle:
1. Check pending decisions from reasoning engine
2. If autonomy level allows, execute qualifying decisions
3. Record outcomes when known
4. Update trust score
5. Store learnings in Mem0

Run as: python intelligence_loop.py [interval_seconds]
Default interval: 300 seconds (5 minutes)
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

import httpx

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.learning import get_learning_capture, poll_whaletrack_trades
from app.trust import get_trust_manager, AutonomyLevel
from app.executor import get_executor, ActionRequest, ActionType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("intelligence_loop")

# Configuration
REASONING_ENGINE_URL = os.getenv("REASONING_ENGINE_URL", "http://198.54.123.234:8140")
TEAM_HUB_URL = os.getenv("TEAM_HUB_URL", "http://198.54.123.234:8355")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# Loop state
CYCLE_COUNT = 0
ACTIONS_ATTEMPTED = 0
ACTIONS_EXECUTED = 0


async def fetch_recommendations() -> List[Dict]:
    """Fetch pending recommendations from the reasoning engine."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{REASONING_ENGINE_URL}/api/reasoning/recommendations")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("recommendations", [])
    except Exception as e:
        logger.warning(f"Failed to fetch recommendations: {e}")
    return []


async def fetch_learning_metrics() -> Dict:
    """Fetch learning metrics from reasoning engine."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{REASONING_ENGINE_URL}/api/reasoning/learning-metrics")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch learning metrics: {e}")
    return {}


async def evaluate_decision_for_execution(decision: Dict) -> bool:
    """
    Evaluate whether a decision should be auto-executed.
    
    Criteria:
    - Decision status is pending
    - Trust level permits the action
    - Confidence meets threshold
    - Has executable option
    """
    if decision.get("status") != "pending":
        return False
    
    # Find executable option
    options = decision.get("options", [])
    execute_option = None
    for opt in options:
        if opt.get("api_endpoint") and opt.get("id") != "opt_dismiss":
            execute_option = opt
            break
    
    if not execute_option:
        return False
    
    # Check confidence threshold (require higher confidence for auto-execution)
    confidence = decision.get("confidence", 0)
    if confidence < 0.7:
        return False
    
    return True


def decision_to_action_request(decision: Dict) -> ActionRequest:
    """Convert a decision to an action request."""
    import time
    
    options = decision.get("options", [])
    execute_option = None
    for opt in options:
        if opt.get("api_endpoint") and opt.get("id") != "opt_dismiss":
            execute_option = opt
            break
    
    # Map decision type to action type
    decision_type = decision.get("type", "UNKNOWN")
    action_type_map = {
        "SCALE": ActionType.GPU_SCALE,
        "ALERT": ActionType.ALERT_DISMISS,
        "OPTIMIZE": ActionType.COST_OPTIMIZE,
        "INVESTIGATE": ActionType.INTELLIGENCE_TRIGGER
    }
    
    action_type = action_type_map.get(decision_type, ActionType.INTELLIGENCE_TRIGGER)
    
    # Estimate value (simplified - in production would calculate actual cost)
    value_estimate = 50.0  # Default low value
    if decision_type == "SCALE":
        value_estimate = 100.0  # GPU scaling has moderate cost
    
    return ActionRequest(
        action_id=f"auto_{decision.get('id', int(time.time()))}",
        action_type=action_type,
        description=decision.get("title", "Automated action"),
        estimated_value=value_estimate,
        confidence=decision.get("confidence", 0.5),
        parameters=execute_option.get("params", {}) if execute_option else {},
        decision_id=decision.get("id")
    )


async def send_feedback(decision_id: str, action: str, outcome: str = None):
    """Send feedback to reasoning engine."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{REASONING_ENGINE_URL}/api/reasoning/feedback",
                json={
                    "decision_id": decision_id,
                    "action": action,
                    "outcome": outcome
                }
            )
    except Exception as e:
        logger.warning(f"Failed to send feedback: {e}")


async def run_cycle():
    """Run one intelligence cycle."""
    global CYCLE_COUNT, ACTIONS_ATTEMPTED, ACTIONS_EXECUTED
    
    CYCLE_COUNT += 1
    cycle_start = time.time()
    
    logger.info(f"=== Intelligence Cycle {CYCLE_COUNT} starting ===")
    
    trust = get_trust_manager()
    executor = get_executor()
    learning = get_learning_capture()
    
    # 1. Log current trust state
    logger.info(f"Trust level: {trust.state.autonomy_level.value} (score: {trust.state.trust_score:.2f})")
    logger.info(f"Accuracy: {trust.state.accuracy:.1%} from {trust.state.total_outcomes} outcomes")
    
    if trust.state.is_paused:
        logger.warning(f"System is PAUSED: {trust.state.pause_reason}")
        return
    
    # 2. Poll for completed trades (outcome capture)
    logger.info("Polling for completed trades...")
    trade_outcomes = await poll_whaletrack_trades()
    if trade_outcomes:
        logger.info(f"Captured {len(trade_outcomes)} trade outcomes")
        for outcome in trade_outcomes:
            logger.info(f"  {outcome.trade_id}: {outcome.outcome_type.value} (${outcome.pnl_usd:.2f})")
    
    # 3. Fetch pending recommendations
    logger.info("Fetching recommendations...")
    recommendations = await fetch_recommendations()
    pending = [r for r in recommendations if r.get("status") == "pending"]
    logger.info(f"Found {len(pending)} pending recommendations")
    
    # 4. Evaluate and potentially execute recommendations
    for decision in pending:
        ACTIONS_ATTEMPTED += 1
        
        if not await evaluate_decision_for_execution(decision):
            logger.info(f"Decision {decision.get('id')} not eligible for auto-execution")
            continue
        
        # Convert to action request
        action_request = decision_to_action_request(decision)
        
        logger.info(f"Attempting auto-execution: {action_request.description}")
        logger.info(f"  Value: ${action_request.estimated_value}, Confidence: {action_request.confidence:.1%}")
        
        # Request execution through trust-gated executor
        result = await executor.request_action(action_request)
        
        if result.success:
            ACTIONS_EXECUTED += 1
            logger.info(f"✓ Action executed: {result.message}")
            await send_feedback(decision.get("id"), "executed", result.outcome)
            
            # Record as accepted suggestion
            trust.record_suggestion(accepted=True)
        elif result.outcome == "queued":
            logger.info(f"→ Action queued for human approval")
            # Don't record as suggestion yet - will be recorded when approved/rejected
        else:
            logger.warning(f"✗ Action blocked: {result.message}")
            await send_feedback(decision.get("id"), "blocked")
    
    # 5. Log learning metrics
    metrics = learning.get_metrics()
    logger.info(f"Learning metrics:")
    logger.info(f"  Trades tracked: {metrics['trades']['total']}, Win rate: {metrics['trades']['win_rate']:.1%}")
    logger.info(f"  Decisions tracked: {metrics['decisions']['total']}, Success rate: {metrics['decisions']['success_rate']:.1%}")
    
    # 6. Log next tier progress
    progress = trust.state.get_next_tier_progress()
    if not progress.get("at_max_tier"):
        logger.info(f"Progress to {progress['next_tier']}:")
        logger.info(f"  Accuracy: {progress['accuracy_current']:.1%} / {progress['accuracy_required']:.0%}")
        logger.info(f"  Suggestions: {progress['suggestions_current']} / {progress['suggestions_required']}")
        logger.info(f"  Overall: {progress['overall_progress']:.0%}")
    
    cycle_duration = time.time() - cycle_start
    logger.info(f"=== Cycle {CYCLE_COUNT} complete in {cycle_duration:.1f}s ===\n")


async def main(interval_seconds: int = 300):
    """Main loop."""
    logger.info("=" * 60)
    logger.info("Graduated Intelligence Loop Starting")
    logger.info(f"Interval: {interval_seconds} seconds")
    logger.info("=" * 60)
    
    # Initialize components
    trust = get_trust_manager()
    
    logger.info(f"Initial trust state:")
    logger.info(f"  Level: {trust.state.autonomy_level.value}")
    logger.info(f"  Score: {trust.state.trust_score:.2f}")
    logger.info(f"  Accuracy: {trust.state.accuracy:.1%}")
    logger.info(f"  Total suggestions: {trust.state.suggestions_made}")
    
    while True:
        try:
            await run_cycle()
        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)
        
        logger.info(f"Sleeping for {interval_seconds} seconds...")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    interval = 300  # Default 5 minutes
    
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print(f"Invalid interval: {sys.argv[1]}, using default {interval}s")
    
    try:
        asyncio.run(main(interval))
    except KeyboardInterrupt:
        logger.info("Intelligence loop stopped by user")
        logger.info(f"Stats: {CYCLE_COUNT} cycles, {ACTIONS_ATTEMPTED} attempted, {ACTIONS_EXECUTED} executed")















