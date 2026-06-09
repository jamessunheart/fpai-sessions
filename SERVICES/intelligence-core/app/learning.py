"""
Learning Layer - Outcome Capture and Correlation
=================================================

The foundation of graduated intelligence. Captures every decision outcome
and stores learnings that feed into reasoning and agency layers.

Flow:
1. Hook into WhaleTrack trade events
2. Capture: signal → action → outcome
3. Store in Mem0 for persistent learning
4. Calculate correlation between signals and outcomes
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

import httpx

logger = logging.getLogger("intelligence.learning")

# Configuration
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8600")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://162.0.208.88:8125")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# Memory entity for learnings
ENTITY_LEARNINGS = "fpai_intelligence_learnings"
ENTITY_OUTCOMES = "fpai_trade_outcomes"


class OutcomeType(str, Enum):
    POSITIVE = "positive"  # Profitable trade or accepted suggestion
    NEGATIVE = "negative"  # Loss or rejected suggestion
    NEUTRAL = "neutral"    # Break-even or no clear outcome
    PENDING = "pending"    # Outcome not yet known


@dataclass
class TradeSignal:
    """Represents a trading signal that led to a decision."""
    signal_id: str
    symbol: str
    direction: str  # LONG or SHORT
    confidence: float
    ai_votes: Dict[str, str]  # Which AIs voted what
    magnet_distance: float
    timestamp: str


@dataclass
class TradeOutcome:
    """Represents the outcome of a trade."""
    trade_id: str
    signal: TradeSignal
    entry_price: float
    exit_price: Optional[float]
    pnl_usd: Optional[float]
    pnl_percent: Optional[float]
    duration_minutes: Optional[int]
    outcome_type: OutcomeType
    exit_reason: Optional[str]  # stop_loss, take_profit, manual, etc.
    timestamp: str


@dataclass
class DecisionOutcome:
    """Represents the outcome of a system decision/recommendation."""
    decision_id: str
    decision_type: str  # SCALE, INVESTIGATE, ALERT, etc.
    recommended_action: str
    user_action: str  # executed, dismissed, modified
    actual_outcome: Optional[str]
    outcome_type: OutcomeType
    confidence_at_decision: float
    timestamp: str


class LearningCapture:
    """
    Captures outcomes from trades and decisions, stores learnings in Mem0.
    """
    
    def __init__(self):
        self.outcomes: List[TradeOutcome] = []
        self.decision_outcomes: List[DecisionOutcome] = []
        self.signal_accuracy: Dict[str, Dict] = {}  # signal_type -> {correct, total}
        self._mem0_headers = {
            "Authorization": f"Token {MEM0_API_KEY}",
            "Content-Type": "application/json"
        } if MEM0_API_KEY else {}
    
    async def capture_trade_outcome(
        self,
        trade_id: str,
        signal: Dict[str, Any],
        entry_price: float,
        exit_price: float,
        pnl_usd: float,
        exit_reason: str
    ) -> TradeOutcome:
        """
        Capture outcome of a completed trade.
        """
        # Parse signal
        trade_signal = TradeSignal(
            signal_id=signal.get("id", f"sig_{int(time.time())}"),
            symbol=signal.get("symbol", "UNKNOWN"),
            direction=signal.get("direction", "UNKNOWN"),
            confidence=signal.get("confidence", 0),
            ai_votes=signal.get("ai_votes", {}),
            magnet_distance=signal.get("magnet_distance", 0),
            timestamp=signal.get("timestamp", datetime.now(timezone.utc).isoformat())
        )
        
        # Determine outcome type
        if pnl_usd > 0:
            outcome_type = OutcomeType.POSITIVE
        elif pnl_usd < 0:
            outcome_type = OutcomeType.NEGATIVE
        else:
            outcome_type = OutcomeType.NEUTRAL
        
        # Calculate duration if timestamps available
        duration = None
        
        outcome = TradeOutcome(
            trade_id=trade_id,
            signal=trade_signal,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_usd=pnl_usd,
            pnl_percent=(exit_price - entry_price) / entry_price * 100 if entry_price else 0,
            duration_minutes=duration,
            outcome_type=outcome_type,
            exit_reason=exit_reason,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self.outcomes.append(outcome)
        
        # Update signal accuracy tracking
        await self._update_signal_accuracy(trade_signal, outcome_type)
        
        # Store learning in Mem0
        await self._store_trade_learning(outcome)
        
        logger.info(f"Captured trade outcome: {trade_id} -> {outcome_type.value} (${pnl_usd:.2f})")
        
        return outcome
    
    async def capture_decision_outcome(
        self,
        decision_id: str,
        decision_type: str,
        recommended_action: str,
        user_action: str,
        actual_outcome: Optional[str],
        confidence: float
    ) -> DecisionOutcome:
        """
        Capture outcome of a system decision/recommendation.
        """
        # Determine outcome type based on user action and result
        if user_action == "dismissed":
            outcome_type = OutcomeType.NEGATIVE  # User disagreed
        elif user_action == "executed":
            if actual_outcome and "success" in actual_outcome.lower():
                outcome_type = OutcomeType.POSITIVE
            elif actual_outcome and ("fail" in actual_outcome.lower() or "error" in actual_outcome.lower()):
                outcome_type = OutcomeType.NEGATIVE
            else:
                outcome_type = OutcomeType.PENDING
        else:
            outcome_type = OutcomeType.NEUTRAL
        
        outcome = DecisionOutcome(
            decision_id=decision_id,
            decision_type=decision_type,
            recommended_action=recommended_action,
            user_action=user_action,
            actual_outcome=actual_outcome,
            outcome_type=outcome_type,
            confidence_at_decision=confidence,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self.decision_outcomes.append(outcome)
        
        # Store learning
        await self._store_decision_learning(outcome)
        
        logger.info(f"Captured decision outcome: {decision_id} -> {outcome_type.value}")
        
        return outcome
    
    async def _update_signal_accuracy(self, signal: TradeSignal, outcome: OutcomeType):
        """Track accuracy by signal type/confidence level."""
        # Key by symbol and confidence bucket
        conf_bucket = f"{int(signal.confidence / 10) * 10}-{int(signal.confidence / 10) * 10 + 10}"
        key = f"{signal.symbol}_{conf_bucket}"
        
        if key not in self.signal_accuracy:
            self.signal_accuracy[key] = {"correct": 0, "total": 0}
        
        self.signal_accuracy[key]["total"] += 1
        if outcome == OutcomeType.POSITIVE:
            self.signal_accuracy[key]["correct"] += 1
    
    async def _store_trade_learning(self, outcome: TradeOutcome):
        """Store trade learning in Mem0."""
        if not MEM0_API_KEY:
            logger.warning("MEM0_API_KEY not set, skipping persistent storage")
            return
        
        # Format learning message
        signal = outcome.signal
        result = "profitable" if outcome.outcome_type == OutcomeType.POSITIVE else "loss"
        
        lesson = f"""
Trade {outcome.trade_id} on {signal.symbol} was {result}.
Signal: {signal.direction} with {signal.confidence:.0f}% confidence.
Entry: ${outcome.entry_price:.2f}, Exit: ${outcome.exit_price:.2f}
P&L: ${outcome.pnl_usd:.2f} ({outcome.pnl_percent:.1f}%)
Exit reason: {outcome.exit_reason}
AI votes: {json.dumps(signal.ai_votes)}
Lesson: {signal.direction} signals at {signal.confidence:.0f}% confidence on {signal.symbol} 
have this outcome pattern.
"""
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.mem0.ai/v1/memories/",
                    headers=self._mem0_headers,
                    json={
                        "messages": [{"role": "user", "content": lesson}],
                        "user_id": ENTITY_OUTCOMES,
                        "metadata": {
                            "type": "trade_outcome",
                            "symbol": signal.symbol,
                            "direction": signal.direction,
                            "confidence": signal.confidence,
                            "outcome": outcome.outcome_type.value,
                            "pnl_usd": outcome.pnl_usd,
                            "trade_id": outcome.trade_id
                        }
                    }
                )
                if resp.status_code == 200:
                    logger.info(f"Stored trade learning in Mem0")
                else:
                    logger.error(f"Mem0 store failed: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to store trade learning: {e}")
    
    async def _store_decision_learning(self, outcome: DecisionOutcome):
        """Store decision learning in Mem0."""
        if not MEM0_API_KEY:
            return
        
        result = "accepted and successful" if outcome.outcome_type == OutcomeType.POSITIVE else \
                 "rejected by user" if outcome.user_action == "dismissed" else \
                 "executed with uncertain outcome"
        
        lesson = f"""
Decision {outcome.decision_id} ({outcome.decision_type}) was {result}.
Recommendation: {outcome.recommended_action}
User action: {outcome.user_action}
Confidence at time: {outcome.confidence_at_decision:.0f}%
Actual outcome: {outcome.actual_outcome or 'pending'}
Lesson: {outcome.decision_type} decisions at {outcome.confidence_at_decision:.0f}% confidence 
tend to be {result}.
"""
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.mem0.ai/v1/memories/",
                    headers=self._mem0_headers,
                    json={
                        "messages": [{"role": "user", "content": lesson}],
                        "user_id": ENTITY_LEARNINGS,
                        "metadata": {
                            "type": "decision_outcome",
                            "decision_type": outcome.decision_type,
                            "user_action": outcome.user_action,
                            "outcome": outcome.outcome_type.value,
                            "confidence": outcome.confidence_at_decision
                        }
                    }
                )
                if resp.status_code == 200:
                    logger.info(f"Stored decision learning in Mem0")
        except Exception as e:
            logger.error(f"Failed to store decision learning: {e}")
    
    async def get_signal_accuracy(self, symbol: str = None, min_trades: int = 5) -> Dict[str, Any]:
        """
        Get accuracy statistics for signals.
        """
        results = {}
        
        for key, stats in self.signal_accuracy.items():
            if stats["total"] < min_trades:
                continue
            if symbol and not key.startswith(symbol):
                continue
            
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            results[key] = {
                "accuracy": accuracy,
                "total_trades": stats["total"],
                "profitable_trades": stats["correct"]
            }
        
        return results
    
    async def search_similar_situations(self, context: str, limit: int = 5) -> List[Dict]:
        """
        Search Mem0 for learnings from similar situations.
        """
        if not MEM0_API_KEY:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.mem0.ai/v1/memories/search/",
                    headers=self._mem0_headers,
                    json={
                        "query": context,
                        "user_id": ENTITY_LEARNINGS,
                        "limit": limit
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data if isinstance(data, list) else data.get("results", [])
        except Exception as e:
            logger.error(f"Failed to search learnings: {e}")
        
        return []
    
    async def calculate_success_rate(self, learnings: List[Dict]) -> float:
        """
        Calculate success rate from a list of past learnings.
        """
        if not learnings:
            return 0.5  # Default to 50% if no data
        
        positive = 0
        total = 0
        
        for learning in learnings:
            metadata = learning.get("metadata", {})
            outcome = metadata.get("outcome")
            if outcome:
                total += 1
                if outcome == "positive":
                    positive += 1
        
        return positive / total if total > 0 else 0.5
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get learning metrics for dashboard."""
        total_trades = len(self.outcomes)
        profitable = len([o for o in self.outcomes if o.outcome_type == OutcomeType.POSITIVE])
        
        total_decisions = len(self.decision_outcomes)
        accepted = len([d for d in self.decision_outcomes if d.user_action == "executed"])
        successful = len([d for d in self.decision_outcomes 
                         if d.outcome_type == OutcomeType.POSITIVE])
        
        return {
            "trades": {
                "total": total_trades,
                "profitable": profitable,
                "win_rate": profitable / total_trades if total_trades > 0 else 0
            },
            "decisions": {
                "total": total_decisions,
                "accepted": accepted,
                "successful": successful,
                "acceptance_rate": accepted / total_decisions if total_decisions > 0 else 0,
                "success_rate": successful / accepted if accepted > 0 else 0
            },
            "signal_accuracy": self.signal_accuracy,
            "learnings_stored": total_trades + total_decisions
        }


# Singleton instance
_learning_capture: Optional[LearningCapture] = None


def get_learning_capture() -> LearningCapture:
    """Get singleton learning capture instance."""
    global _learning_capture
    if _learning_capture is None:
        _learning_capture = LearningCapture()
    return _learning_capture


# ─────────────────────────────────────────────────────────────────────────────
# WhaleTrack Integration - Poll for completed trades
# ─────────────────────────────────────────────────────────────────────────────

async def poll_whaletrack_trades() -> List[TradeOutcome]:
    """
    Poll WhaleTrack for completed trades and capture outcomes.
    """
    capture = get_learning_capture()
    outcomes = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get recent closed trades
            resp = await client.get(f"{WHALETRACK_URL}/api/trades/history?limit=50")
            if resp.status_code != 200:
                logger.warning(f"WhaleTrack trades endpoint returned {resp.status_code}")
                return []
            
            trades = resp.json()
            
            for trade in trades:
                # Skip if already captured
                trade_id = trade.get("id")
                if any(o.trade_id == trade_id for o in capture.outcomes):
                    continue
                
                # Skip if not closed
                if trade.get("status") != "closed":
                    continue
                
                # Capture outcome
                outcome = await capture.capture_trade_outcome(
                    trade_id=trade_id,
                    signal=trade.get("signal", {}),
                    entry_price=trade.get("entry_price", 0),
                    exit_price=trade.get("exit_price", 0),
                    pnl_usd=trade.get("pnl_usd", 0),
                    exit_reason=trade.get("exit_reason", "unknown")
                )
                outcomes.append(outcome)
    
    except Exception as e:
        logger.error(f"Failed to poll WhaleTrack trades: {e}")
    
    return outcomes















