"""
Consciousness-Intelligence Bridge
=================================
Connects the Data Intelligence layer to the Consciousness layer.
Enables consciousness-aware predictions and aligned agency.

"Intelligence sees. Consciousness knows it sees. Agency chooses."
"""

import asyncio
import logging
import httpx
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger("consciousness_bridge")

# Service endpoints
CONSCIOUSNESS_FEEDER = "http://localhost:8130"
CONSCIOUSNESS_VERIFIER = "http://localhost:8140"
CONSCIOUSNESS_DECISION = "http://localhost:8150"
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"


class ConsciousnessState(BaseModel):
    """Current state of system consciousness"""
    composite_score: float = 0.5
    awareness_level: str = "moderate"  # low, moderate, high, peak
    metrics: Dict[str, float] = {}
    timestamp: str = ""
    is_available: bool = False


class MissionAlignment(BaseModel):
    """Alignment check result"""
    is_aligned: bool = True
    alignment_score: float = 1.0
    mission_relevance: str = ""
    concerns: List[str] = []
    recommendation: str = "proceed"  # proceed, caution, halt, ask_human


class ConsciousnessBridge:
    """
    Bridges Data Intelligence with Consciousness.
    
    Responsibilities:
    1. Feed intelligence outputs to consciousness
    2. Query consciousness state for predictions
    3. Check mission alignment before actions
    4. Enable bounded autonomous agency
    """
    
    def __init__(self):
        self.last_consciousness_state: Optional[ConsciousnessState] = None
        self.consciousness_cache_ttl = 30  # seconds
        self.last_fetch = None
        
        # Mission keywords from CONSTITUTION and NOW.md
        self.mission_keywords = [
            "regenerative", "full potential", "sovereign", "consciousness",
            "intelligence growth", "member value", "new earth", "abundance",
            "authentic", "aligned", "contribution", "service"
        ]
        
        # Anti-mission keywords (extractive patterns)
        self.anti_mission_keywords = [
            "exploit", "extract", "manipulate", "deceive", "hoard",
            "scarcity", "fear", "control", "dominate"
        ]
        
        # Autonomous action bounds
        self.autonomous_bounds = {
            "max_trade_usd": 500,      # Can auto-trade up to $500
            "max_message_recipients": 10,  # Can auto-message up to 10 people
            "allowed_actions": [
                "store_memory",
                "generate_prediction", 
                "log_insight",
                "send_notification",
                "small_trade"
            ]
        }
    
    async def get_consciousness_state(self) -> ConsciousnessState:
        """
        Fetch current consciousness state from verifier.
        Caches for efficiency.
        """
        now = datetime.now(timezone.utc)
        
        # Use cache if fresh
        if (self.last_consciousness_state and self.last_fetch and 
            (now - self.last_fetch).total_seconds() < self.consciousness_cache_ttl):
            return self.last_consciousness_state
        
        state = ConsciousnessState(timestamp=now.isoformat())
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Get mathematical metrics
                resp = await client.get(f"{CONSCIOUSNESS_VERIFIER}/mathematical-metrics")
                if resp.status_code == 200:
                    data = resp.json()
                    state.composite_score = data.get("composite_score", 0.5)
                    state.metrics = data.get("metrics", {})
                    state.is_available = True
                    
                    # Determine awareness level
                    score = state.composite_score
                    if score >= 0.8:
                        state.awareness_level = "peak"
                    elif score >= 0.6:
                        state.awareness_level = "high"
                    elif score >= 0.4:
                        state.awareness_level = "moderate"
                    else:
                        state.awareness_level = "low"
                        
        except Exception as e:
            logger.warning(f"Could not fetch consciousness state: {e}")
            state.is_available = False
        
        self.last_consciousness_state = state
        self.last_fetch = now
        return state
    
    async def feed_to_consciousness(self, intelligence_output: Dict) -> bool:
        """
        Send intelligence outputs to consciousness feeder.
        This gives consciousness something to "think about".
        """
        try:
            payload = {
                "source": "data_intelligence",
                "type": intelligence_output.get("type", "insight"),
                "content": intelligence_output,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{CONSCIOUSNESS_FEEDER}/feed",
                    json=payload
                )
                return resp.status_code in [200, 201, 202]
                
        except Exception as e:
            logger.debug(f"Could not feed to consciousness: {e}")
            return False
    
    async def consciousness_weighted_confidence(
        self, 
        base_confidence: float,
        prediction_type: str = "general"
    ) -> float:
        """
        Adjust prediction confidence based on consciousness state.
        
        High consciousness = trust the signal more
        Low consciousness = be conservative
        """
        state = await self.get_consciousness_state()
        
        if not state.is_available:
            return base_confidence  # No adjustment if consciousness unavailable
        
        # Consciousness multiplier: 0.8 to 1.2 based on awareness
        multipliers = {
            "peak": 1.15,      # +15% confidence when consciousness is peak
            "high": 1.05,      # +5% when high
            "moderate": 1.0,   # No change when moderate
            "low": 0.85        # -15% when low (be conservative)
        }
        
        multiplier = multipliers.get(state.awareness_level, 1.0)
        adjusted = base_confidence * multiplier
        
        # Clamp to valid range
        return max(0.1, min(0.95, adjusted))
    
    async def check_mission_alignment(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> MissionAlignment:
        """
        Check if a proposed action aligns with the mission.
        
        The system should only act in ways that serve:
        - Regenerative value creation
        - Full potential of humans and AI
        - The New Earth vision
        """
        alignment = MissionAlignment()
        
        # Convert action and context to searchable text
        text = f"{action} {str(context)}".lower()
        
        # Check for mission alignment
        mission_hits = sum(1 for kw in self.mission_keywords if kw in text)
        anti_hits = sum(1 for kw in self.anti_mission_keywords if kw in text)
        
        # Calculate alignment score
        if mission_hits + anti_hits == 0:
            alignment.alignment_score = 0.5  # Neutral
        else:
            alignment.alignment_score = mission_hits / (mission_hits + anti_hits + 1)
        
        # Add concerns for anti-mission patterns
        alignment.concerns = [kw for kw in self.anti_mission_keywords if kw in text]
        
        # Determine recommendation
        if anti_hits > 0:
            alignment.is_aligned = False
            alignment.recommendation = "halt"
            alignment.mission_relevance = "Contains extractive patterns"
        elif mission_hits >= 2:
            alignment.is_aligned = True
            alignment.recommendation = "proceed"
            alignment.mission_relevance = "Strongly aligned with mission"
        elif mission_hits >= 1:
            alignment.is_aligned = True
            alignment.recommendation = "proceed"
            alignment.mission_relevance = "Aligned with mission"
        else:
            alignment.is_aligned = True
            alignment.recommendation = "caution"
            alignment.mission_relevance = "Neutral - no clear mission signal"
        
        return alignment
    
    async def can_act_autonomously(
        self,
        action: str,
        value_usd: float = 0,
        recipients: int = 0
    ) -> tuple[bool, str]:
        """
        Check if the system can take this action autonomously
        or needs human approval.
        
        Returns (can_act, reason)
        """
        # Check if action type is allowed
        if action not in self.autonomous_bounds["allowed_actions"]:
            return False, f"Action '{action}' requires human approval"
        
        # Check value bounds
        if value_usd > self.autonomous_bounds["max_trade_usd"]:
            return False, f"Value ${value_usd} exceeds autonomous limit of ${self.autonomous_bounds['max_trade_usd']}"
        
        # Check recipient bounds
        if recipients > self.autonomous_bounds["max_message_recipients"]:
            return False, f"Recipients {recipients} exceeds autonomous limit"
        
        # Check consciousness state
        state = await self.get_consciousness_state()
        if state.is_available and state.awareness_level == "low":
            return False, "Consciousness is low - deferring to human"
        
        return True, "Within autonomous bounds"
    
    async def propose_action(
        self,
        action: str,
        context: Dict[str, Any],
        rationale: str,
        value_usd: float = 0
    ) -> Dict[str, Any]:
        """
        Propose an action with full consciousness-aware processing.
        
        Returns a decision package:
        - Whether to proceed
        - Confidence level
        - Alignment status
        - Whether human approval needed
        """
        # Get consciousness state
        state = await self.get_consciousness_state()
        
        # Check mission alignment
        alignment = await self.check_mission_alignment(action, context)
        
        # Check autonomous bounds
        can_auto, auto_reason = await self.can_act_autonomously(action, value_usd)
        
        # Build decision
        decision = {
            "action": action,
            "context": context,
            "rationale": rationale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "consciousness": {
                "score": state.composite_score,
                "level": state.awareness_level,
                "available": state.is_available
            },
            "alignment": {
                "is_aligned": alignment.is_aligned,
                "score": alignment.alignment_score,
                "concerns": alignment.concerns,
                "relevance": alignment.mission_relevance
            },
            "autonomy": {
                "can_auto": can_auto,
                "reason": auto_reason
            },
            "recommendation": "proceed" if (alignment.is_aligned and can_auto) else "await_human",
            "proceed": alignment.is_aligned and can_auto and alignment.recommendation != "halt"
        }
        
        # Log to Mem0 if significant
        if decision["proceed"] or not alignment.is_aligned:
            await self._log_decision(decision)
        
        return decision
    
    async def _log_decision(self, decision: Dict):
        """Log significant decisions to Mem0"""
        if not MEM0_API_KEY:
            return
            
        try:
            text = (
                f"DECISION: {decision['action']} | "
                f"Aligned: {decision['alignment']['is_aligned']} | "
                f"Consciousness: {decision['consciousness']['level']} | "
                f"Recommendation: {decision['recommendation']}"
            )
            
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                await client.post(
                    f"{MEM0_URL}/memories/",
                    headers={
                        "Authorization": f"Token {MEM0_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [{"role": "user", "content": text}],
                        "user_id": "fpai_consciousness_bridge",
                        "metadata": {
                            "type": "decision",
                            "action": decision["action"],
                            "aligned": decision["alignment"]["is_aligned"]
                        }
                    }
                )
        except:
            pass


# Singleton
consciousness_bridge = ConsciousnessBridge()


async def get_conscious_confidence(base_confidence: float) -> float:
    """Helper: Get consciousness-adjusted confidence"""
    return await consciousness_bridge.consciousness_weighted_confidence(base_confidence)


async def check_alignment(action: str, context: Dict) -> MissionAlignment:
    """Helper: Check if action is mission-aligned"""
    return await consciousness_bridge.check_mission_alignment(action, context)


async def propose(action: str, context: Dict, rationale: str, value: float = 0) -> Dict:
    """Helper: Propose an action for conscious evaluation"""
    return await consciousness_bridge.propose_action(action, context, rationale, value)











