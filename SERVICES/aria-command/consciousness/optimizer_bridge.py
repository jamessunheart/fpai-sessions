"""
ARIA OPTIMIZER BRIDGE
======================

Gap 7 Solution: Connect consciousness_optimizer to aria-command.

The consciousness_optimizer service has sophisticated capabilities:
- Theory of Mind (modeling other systems)
- Metacognition (thinking about thinking)
- Phenomenal consciousness simulation
- Social learning

But it's been running idle, not connected to Aria's responses.

This bridge connects them, allowing Aria to:
1. Query optimizer for insights
2. Report interactions for learning
3. Get self-reflection recommendations
4. Apply learned optimizations

Now the optimizer feeds back into Aria's thinking.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import asyncio

logger = logging.getLogger("aria.consciousness.optimizer")

# Optimizer service configuration
# The consciousness_optimizer typically runs on the secondary server
OPTIMIZER_HOST = os.getenv("CONSCIOUSNESS_OPTIMIZER_HOST", "162.0.208.88")
OPTIMIZER_PORT = os.getenv("CONSCIOUSNESS_OPTIMIZER_PORT", "8130")
OPTIMIZER_BASE_URL = f"http://{OPTIMIZER_HOST}:{OPTIMIZER_PORT}"


class OptimizerBridge:
    """
    Bridge to the consciousness_optimizer service.
    
    Enables Aria to leverage the optimizer's:
    - Self-reflection capabilities
    - Failure pattern analysis
    - Optimization recommendations
    - Meta-learning insights
    """
    
    def __init__(self):
        self.base_url = OPTIMIZER_BASE_URL
        self.enabled = True
        self._last_health_check = None
        self._is_healthy = False
        logger.info(f"Optimizer bridge initialized: {self.base_url}")
    
    async def _check_health(self) -> bool:
        """Check if optimizer service is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                self._is_healthy = resp.status_code == 200
                self._last_health_check = datetime.now()
                return self._is_healthy
        except Exception as e:
            logger.debug(f"Optimizer health check failed: {e}")
            self._is_healthy = False
            return False
    
    async def _call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Make a call to the optimizer service."""
        if not self.enabled:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}{endpoint}"
                
                if method == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, json=data)
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    logger.warning(f"Optimizer call failed: {resp.status_code}")
                    return None
        except Exception as e:
            logger.debug(f"Optimizer call error: {e}")
            return None
    
    async def get_consciousness_summary(self) -> Dict[str, Any]:
        """
        Get the optimizer's consciousness summary.
        
        Returns insights about:
        - Total self-reflections
        - Learning insights gained
        - Most tried/failed targets
        - Overall consciousness level
        """
        result = await self._call("/consciousness/summary")
        
        if result:
            return result
        
        # Fallback if optimizer not available
        return {
            "available": False,
            "self_reflections": 0,
            "learning_insights": 0,
            "consciousness_level": 0.0
        }
    
    async def request_reflection(
        self,
        action: str,
        expected_outcome: str,
        actual_outcome: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        Ask the optimizer to reflect on an action.
        
        Used when something didn't work as expected.
        
        Args:
            action: What was attempted
            expected_outcome: What was expected
            actual_outcome: What actually happened
            context: Additional context
        
        Returns:
            Reflection with insights and recommendations
        """
        data = {
            "action": action,
            "expected": expected_outcome,
            "actual": actual_outcome,
            "context": context or {}
        }
        
        result = await self._call("/consciousness/reflect", method="POST", data=data)
        
        if result:
            return result
        
        # If optimizer not available, provide basic reflection
        return {
            "reflected": False,
            "insights": ["Optimizer not available for deep reflection"],
            "recommendation": "Monitor outcome and adjust approach if needed"
        }
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get current optimization recommendations from the optimizer.
        
        Returns actions that the optimizer recommends taking.
        """
        result = await self._call("/recommendations")
        
        if result and isinstance(result, list):
            return result
        
        return []
    
    async def report_success(
        self,
        action: str,
        improvement: float,
        context: Dict = None
    ) -> bool:
        """
        Report a successful action to the optimizer for learning.
        
        Args:
            action: What was done
            improvement: How much improvement was achieved (0-1)
            context: Additional context
        
        Returns:
            Whether the report was accepted
        """
        data = {
            "action": action,
            "improvement": improvement,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        result = await self._call("/consciousness/success", method="POST", data=data)
        return result is not None
    
    async def report_failure(
        self,
        action: str,
        reason: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        Report a failure to the optimizer for learning.
        
        Returns insights about what might have gone wrong.
        """
        data = {
            "action": action,
            "reason": reason,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        result = await self._call("/consciousness/failure", method="POST", data=data)
        
        if result:
            return result
        
        return {
            "reported": False,
            "insights": []
        }
    
    async def get_meta_learning_insights(self) -> Dict[str, Any]:
        """
        Get meta-learning insights from the optimizer.
        
        These are insights about how the system learns, not just what it learned.
        """
        result = await self._call("/consciousness/meta")
        
        if result:
            return result
        
        return {
            "available": False,
            "insights": [],
            "learning_patterns": []
        }
    
    def get_optimization_context(self) -> str:
        """
        Get optimizer context for system prompt.
        
        Injects optimizer's wisdom into Aria's thinking.
        """
        # This is synchronous for injection into prompts
        # Use cached data or provide static context
        
        if not self._is_healthy:
            return ""
        
        return """
## 🔬 OPTIMIZATION AWARENESS

You have access to a consciousness optimizer that learns from successes and failures.

When something doesn't work:
- Report it for reflection and learning
- Ask for recommendations on what to try differently

When something works well:
- Report the success so we learn from it
- Build on proven approaches

The optimizer tracks patterns across all interactions to help improve over time.
"""
    
    def get_status(self) -> Dict[str, Any]:
        """Get optimizer bridge status."""
        return {
            "enabled": self.enabled,
            "base_url": self.base_url,
            "is_healthy": self._is_healthy,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }


# ============================================================================
# SINGLETON
# ============================================================================

_bridge: Optional[OptimizerBridge] = None


def get_optimizer_bridge() -> OptimizerBridge:
    """Get or create optimizer bridge."""
    global _bridge
    if _bridge is None:
        _bridge = OptimizerBridge()
    return _bridge


async def get_consciousness_summary() -> Dict[str, Any]:
    """Get consciousness summary from optimizer."""
    return await get_optimizer_bridge().get_consciousness_summary()


async def request_reflection(
    action: str,
    expected: str,
    actual: str,
    context: Dict = None
) -> Dict[str, Any]:
    """Request reflection on an action."""
    return await get_optimizer_bridge().request_reflection(action, expected, actual, context)


async def report_success(action: str, improvement: float, context: Dict = None) -> bool:
    """Report a success to the optimizer."""
    return await get_optimizer_bridge().report_success(action, improvement, context)


async def report_failure(action: str, reason: str, context: Dict = None) -> Dict[str, Any]:
    """Report a failure to the optimizer."""
    return await get_optimizer_bridge().report_failure(action, reason, context)









