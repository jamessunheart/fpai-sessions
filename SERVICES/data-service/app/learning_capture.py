"""
🧠 Automatic Learning Capture System
=====================================

Watches for significant events across services and automatically
stores learnings in the memory system.

Usage:
    from learning_capture import LearningCapture, capture_learning

    # Decorator for automatic capture
    @capture_learning(category="trading")
    async def execute_trade(...):
        ...

    # Manual capture
    learner = LearningCapture()
    await learner.capture_event(event_type, data, outcome)
"""

import os
import time
import logging
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("learning_capture")

# Memory endpoints
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8125")


class LearningCapture:
    """
    Automatic learning capture from system events.
    
    Captures:
    - Trading outcomes (profit/loss)
    - Deployment results (success/failure)
    - Error patterns (recurring issues)
    - Performance metrics (latency, throughput)
    """
    
    # Thresholds for when to capture learnings
    THRESHOLDS = {
        "trading": {
            "profit_min": 50,  # Capture if profit > $50
            "loss_min": 25,    # Capture if loss > $25
        },
        "deployment": {
            "always": True,    # Always capture deployment outcomes
        },
        "error": {
            "recurrence_min": 3,  # Capture if error occurs 3+ times
        },
        "performance": {
            "latency_high_ms": 5000,   # Capture if latency > 5s
            "success_rate_low": 0.9,    # Capture if success rate < 90%
        }
    }
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.base_url = DATA_SERVICE_URL
    
    async def _store_learning(
        self,
        context: str,
        action: str,
        outcome: str,
        lesson: str
    ) -> bool:
        """Store a learning via Data Service API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/data/memory/learn",
                    json={
                        "context": context,
                        "action": action,
                        "outcome": outcome,
                        "lesson": lesson
                    }
                )
                if resp.status_code == 200:
                    logger.info(f"📚 Auto-captured learning: {lesson[:50]}...")
                    return True
                else:
                    logger.warning(f"Failed to store learning: {resp.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Learning capture error: {e}")
            return False
    
    async def _store_unified(
        self,
        content: str,
        memory_type: str,
        metadata: Dict = None
    ) -> bool:
        """Store via unified memory API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/memory/store",
                    json={
                        "content": content,
                        "memory_type": memory_type,
                        "metadata": metadata or {}
                    }
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Unified memory error: {e}")
            return False
    
    # =========================================================================
    # TRADING EVENTS
    # =========================================================================
    
    async def capture_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl_usd: float,
        strategy: str,
        duration_minutes: float,
        metadata: Dict = None
    ) -> bool:
        """
        Capture learning from a completed trade.
        
        Only captures significant trades (profit > $50 or loss > $25).
        """
        # Check if significant enough to capture
        if abs(pnl_usd) < self.THRESHOLDS["trading"]["profit_min"] and pnl_usd >= 0:
            if abs(pnl_usd) < self.THRESHOLDS["trading"]["loss_min"]:
                return False  # Not significant enough
        
        success = pnl_usd > 0
        pnl_pct = ((exit_price - entry_price) / entry_price * 100) if direction == "long" else ((entry_price - exit_price) / entry_price * 100)
        
        context = f"Trading {symbol} ({direction}) using {strategy}"
        action = f"Entered at ${entry_price:.2f}, exited at ${exit_price:.2f} after {duration_minutes:.0f} min"
        outcome = f"{'Profit' if success else 'Loss'}: ${abs(pnl_usd):.2f} ({pnl_pct:.1f}%)"
        
        if success:
            lesson = f"Strategy {strategy} works well for {symbol} {direction} positions in these conditions"
        else:
            lesson = f"Caution: {strategy} underperformed on {symbol} {direction}. Review entry/exit timing."
        
        return await self._store_learning(context, action, outcome, lesson)
    
    async def capture_trading_signal(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        was_correct: bool,
        actual_move_pct: float
    ) -> bool:
        """Capture learning from a trading signal's accuracy."""
        context = f"Signal: {signal_type} on {symbol} (confidence: {confidence:.0%})"
        action = f"Generated {signal_type} signal"
        outcome = f"Correct: {was_correct}. Actual move: {actual_move_pct:.1f}%"
        
        if was_correct and confidence > 0.7:
            lesson = f"High-confidence {signal_type} signals on {symbol} are reliable"
        elif not was_correct and confidence > 0.7:
            lesson = f"WARNING: High-confidence {signal_type} failed on {symbol}. Review signal logic."
        else:
            lesson = f"Signal {signal_type} accuracy needs monitoring for {symbol}"
        
        return await self._store_learning(context, action, outcome, lesson)
    
    # =========================================================================
    # DEPLOYMENT EVENTS
    # =========================================================================
    
    async def capture_deployment(
        self,
        service_name: str,
        version: str,
        success: bool,
        duration_seconds: float,
        error_message: str = None
    ) -> bool:
        """Capture learning from a deployment."""
        context = f"Deploying {service_name} version {version}"
        action = f"Deployment took {duration_seconds:.0f} seconds"
        outcome = "Success" if success else f"Failed: {error_message}"
        
        if success:
            lesson = f"{service_name} deploys reliably. v{version} took {duration_seconds:.0f}s."
        else:
            lesson = f"DEPLOYMENT FAILURE: {service_name} v{version} failed. Error: {error_message}"
        
        return await self._store_learning(context, action, outcome, lesson)
    
    # =========================================================================
    # ERROR PATTERNS
    # =========================================================================
    
    async def capture_error(
        self,
        service: str,
        error_type: str,
        error_message: str,
        stack_trace: str = None
    ) -> bool:
        """
        Capture learning from recurring errors.
        
        Only captures after error occurs 3+ times to avoid noise.
        """
        error_key = f"{service}:{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        if self.error_counts[error_key] < self.THRESHOLDS["error"]["recurrence_min"]:
            return False  # Not recurring enough yet
        
        # Reset counter after capturing
        count = self.error_counts[error_key]
        self.error_counts[error_key] = 0
        
        context = f"Recurring error in {service}"
        action = f"Error type: {error_type}"
        outcome = f"Occurred {count} times. Message: {error_message[:200]}"
        lesson = f"RECURRING ERROR: {service} has {error_type} issue. Needs investigation."
        
        return await self._store_learning(context, action, outcome, lesson)
    
    # =========================================================================
    # PERFORMANCE EVENTS
    # =========================================================================
    
    async def capture_slow_operation(
        self,
        operation: str,
        latency_ms: float,
        expected_ms: float = 1000
    ) -> bool:
        """Capture learning from slow operations."""
        if latency_ms < self.THRESHOLDS["performance"]["latency_high_ms"]:
            return False
        
        context = f"Performance issue: {operation}"
        action = f"Operation took {latency_ms:.0f}ms (expected: {expected_ms:.0f}ms)"
        outcome = f"Latency {latency_ms/expected_ms:.1f}x higher than expected"
        lesson = f"SLOW: {operation} is taking {latency_ms:.0f}ms. Optimize or add caching."
        
        return await self._store_learning(context, action, outcome, lesson)
    
    async def capture_low_success_rate(
        self,
        operation: str,
        success_rate: float,
        sample_size: int
    ) -> bool:
        """Capture learning from low success rates."""
        if success_rate >= self.THRESHOLDS["performance"]["success_rate_low"]:
            return False
        
        context = f"Reliability issue: {operation}"
        action = f"Success rate: {success_rate:.0%} over {sample_size} attempts"
        outcome = f"Below acceptable threshold of {self.THRESHOLDS['performance']['success_rate_low']:.0%}"
        lesson = f"LOW RELIABILITY: {operation} has {success_rate:.0%} success rate. Needs debugging."
        
        return await self._store_learning(context, action, outcome, lesson)
    
    # =========================================================================
    # GENERIC EVENT CAPTURE
    # =========================================================================
    
    async def capture_event(
        self,
        event_type: str,
        context: str,
        action: str,
        outcome: str,
        lesson: str,
        metadata: Dict = None
    ) -> bool:
        """Generic event capture for custom learnings."""
        return await self._store_learning(context, action, outcome, lesson)


# Global singleton
_learner: Optional[LearningCapture] = None


def get_learner() -> LearningCapture:
    """Get singleton learning capture instance."""
    global _learner
    if _learner is None:
        _learner = LearningCapture()
    return _learner


# =========================================================================
# DECORATOR FOR AUTOMATIC CAPTURE
# =========================================================================

def capture_learning(
    category: str = "general",
    capture_success: bool = True,
    capture_failure: bool = True
):
    """
    Decorator to automatically capture learnings from function execution.
    
    Usage:
        @capture_learning(category="trading")
        async def execute_trade(symbol, amount):
            ...
            return {"pnl": 100}
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            learner = get_learner()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                if capture_success:
                    await learner.capture_event(
                        event_type=category,
                        context=f"Function: {func.__name__}",
                        action=f"Executed with args: {str(args)[:100]}",
                        outcome=f"Success in {duration_ms:.0f}ms",
                        lesson=f"{func.__name__} completed successfully"
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                if capture_failure:
                    await learner.capture_error(
                        service=category,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                
                raise
        
        return wrapper
    return decorator


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

async def log_trade_outcome(
    symbol: str,
    direction: str,
    pnl_usd: float,
    strategy: str,
    entry_price: float,
    exit_price: float,
    duration_minutes: float
) -> bool:
    """Convenience function to log a trade outcome."""
    learner = get_learner()
    return await learner.capture_trade(
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        pnl_usd=pnl_usd,
        strategy=strategy,
        duration_minutes=duration_minutes
    )


async def log_deployment(
    service_name: str,
    version: str,
    success: bool,
    duration_seconds: float,
    error_message: str = None
) -> bool:
    """Convenience function to log a deployment."""
    learner = get_learner()
    return await learner.capture_deployment(
        service_name=service_name,
        version=version,
        success=success,
        duration_seconds=duration_seconds,
        error_message=error_message
    )


async def log_error(
    service: str,
    error_type: str,
    error_message: str
) -> bool:
    """Convenience function to log an error for pattern detection."""
    learner = get_learner()
    return await learner.capture_error(
        service=service,
        error_type=error_type,
        error_message=error_message
    )





