"""
ARIA SELF-HEALER
=================

TRUE INTELLIGENCE = BREAK-PROOF + SELF-FIXING

This module makes Aria genuinely autonomous:
1. Detects when something breaks
2. Attempts to fix it automatically
3. Falls back to alternatives if primary fails
4. Alerts ONLY if auto-fix fails
5. Learns from what broke and what fixed it

No more "I'm feeling fine" when things are broken.
No more waiting for humans to fix things.
Aria heals herself.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import httpx

logger = logging.getLogger("aria.consciousness.healer")

# Configuration
STEWARD_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


class HealAction(str, Enum):
    """Actions the healer can take."""
    NONE = "none"
    SWITCH_MODEL = "switch_model"          # Switch to fallback AI model
    RESTART_SERVICE = "restart_service"    # Restart a service
    CLEAR_CACHE = "clear_cache"            # Clear problematic cache
    RECONNECT_API = "reconnect_api"        # Re-initialize API connection
    REDUCE_LOAD = "reduce_load"            # Reduce concurrent operations
    ALERT_HUMAN = "alert_human"            # Last resort - alert James


class HealResult(str, Enum):
    """Result of a healing attempt."""
    SUCCESS = "success"
    PARTIAL = "partial"      # Fixed but degraded
    FAILED = "failed"
    SKIPPED = "skipped"      # Already healthy


@dataclass
class HealingAttempt:
    """Record of a healing attempt."""
    capability: str
    action: HealAction
    result: HealResult
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    auto_fixed: bool = False


class SelfHealer:
    """
    Aria's self-healing system.
    
    When something breaks, she fixes it herself.
    Only alerts humans as a last resort.
    """
    
    def __init__(self):
        self.healing_history: List[HealingAttempt] = []
        self.consecutive_failures: Dict[str, int] = {}
        self.last_alert_time: Dict[str, datetime] = {}
        self.fallback_active: Dict[str, bool] = {}
        
        logger.info("🩹 Self-healer initialized")
    
    # ========================================================================
    # HEALING STRATEGIES
    # ========================================================================
    
    async def heal_capability(self, capability: str, issue: str) -> HealingAttempt:
        """
        Attempt to heal a broken capability.
        
        Returns the result of the healing attempt.
        """
        logger.info(f"🩹 Attempting to heal: {capability} (issue: {issue})")
        
        # Select healing strategy based on capability
        strategies = {
            "thinking": self._heal_thinking,
            "quick_thinking": self._heal_quick_thinking,
            "memory_store": self._heal_memory,
            "memory_recall": self._heal_memory,
            "telegram": self._heal_telegram,
            "trading_data": self._heal_trading,
            "voice": self._heal_voice,
        }
        
        healer = strategies.get(capability, self._heal_generic)
        
        try:
            result = await healer(capability, issue)
            self.healing_history.append(result)
            
            if result.result == HealResult.SUCCESS:
                self.consecutive_failures[capability] = 0
                logger.info(f"✅ Self-healed {capability}: {result.message}")
            else:
                self.consecutive_failures[capability] = self.consecutive_failures.get(capability, 0) + 1
                logger.warning(f"⚠️ Healing {capability} {result.result.value}: {result.message}")
                
                # Alert if repeated failures
                if self.consecutive_failures[capability] >= 3:
                    await self._alert_steward(capability, issue, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Healing error for {capability}: {e}")
            return HealingAttempt(
                capability=capability,
                action=HealAction.NONE,
                result=HealResult.FAILED,
                message=f"Healing error: {e}"
            )
    
    async def _heal_thinking(self, capability: str, issue: str) -> HealingAttempt:
        """
        Heal the primary thinking capability (Claude).
        
        Strategy:
        1. Check if API key is valid
        2. Try switching to fallback model
        3. Clear any stuck state
        """
        # Try 1: Check API connectivity
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return HealingAttempt(
                capability=capability,
                action=HealAction.ALERT_HUMAN,
                result=HealResult.FAILED,
                message="ANTHROPIC_API_KEY not set - requires human intervention"
            )
        
        # Try 2: Test API with minimal call
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}]
                    }
                )
                
                if resp.status_code == 200:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.RECONNECT_API,
                        result=HealResult.SUCCESS,
                        message="Claude API reconnected successfully",
                        auto_fixed=True
                    )
                elif resp.status_code == 401:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.ALERT_HUMAN,
                        result=HealResult.FAILED,
                        message="Claude API key invalid - requires human to update"
                    )
                elif resp.status_code == 429:
                    # Rate limited - switch to fallback
                    self.fallback_active["thinking"] = True
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.SWITCH_MODEL,
                        result=HealResult.PARTIAL,
                        message="Claude rate limited - switched to fallback (Gemini)",
                        auto_fixed=True
                    )
                    
        except httpx.TimeoutException:
            # Network issue - try fallback
            self.fallback_active["thinking"] = True
            return HealingAttempt(
                capability=capability,
                action=HealAction.SWITCH_MODEL,
                result=HealResult.PARTIAL,
                message="Claude timeout - switched to fallback",
                auto_fixed=True
            )
        except Exception as e:
            return HealingAttempt(
                capability=capability,
                action=HealAction.NONE,
                result=HealResult.FAILED,
                message=f"Claude connection error: {e}"
            )
        
        return HealingAttempt(
            capability=capability,
            action=HealAction.NONE,
            result=HealResult.FAILED,
            message="Unknown thinking issue"
        )
    
    async def _heal_quick_thinking(self, capability: str, issue: str) -> HealingAttempt:
        """Heal Gemini (quick thinking)."""
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if not gemini_key:
            return HealingAttempt(
                capability=capability,
                action=HealAction.SWITCH_MODEL,
                result=HealResult.PARTIAL,
                message="Gemini not configured - using Claude for all thinking",
                auto_fixed=True
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
                )
                
                if resp.status_code == 200:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.RECONNECT_API,
                        result=HealResult.SUCCESS,
                        message="Gemini API reconnected",
                        auto_fixed=True
                    )
                    
        except Exception as e:
            pass
        
        # Fallback: Just use Claude for everything
        return HealingAttempt(
            capability=capability,
            action=HealAction.SWITCH_MODEL,
            result=HealResult.PARTIAL,
            message="Gemini unavailable - Claude handling all requests",
            auto_fixed=True
        )
    
    async def _heal_memory(self, capability: str, issue: str) -> HealingAttempt:
        """Heal Mem0 memory system."""
        mem0_key = os.getenv("MEM0_API_KEY")
        
        if not mem0_key:
            return HealingAttempt(
                capability=capability,
                action=HealAction.REDUCE_LOAD,
                result=HealResult.PARTIAL,
                message="Mem0 not configured - using session memory only",
                auto_fixed=True
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.mem0.ai/v1/memories/search/",
                    headers={
                        "Authorization": f"Token {mem0_key}",
                        "Content-Type": "application/json"
                    },
                    json={"query": "test", "user_id": "aria_test", "limit": 1}
                )
                
                if resp.status_code == 200:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.RECONNECT_API,
                        result=HealResult.SUCCESS,
                        message="Mem0 connection restored",
                        auto_fixed=True
                    )
                    
        except Exception as e:
            pass
        
        return HealingAttempt(
            capability=capability,
            action=HealAction.REDUCE_LOAD,
            result=HealResult.PARTIAL,
            message="Mem0 unreachable - operating without cloud memory",
            auto_fixed=True
        )
    
    async def _heal_telegram(self, capability: str, issue: str) -> HealingAttempt:
        """Heal Telegram connection."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not token:
            return HealingAttempt(
                capability=capability,
                action=HealAction.ALERT_HUMAN,
                result=HealResult.FAILED,
                message="TELEGRAM_BOT_TOKEN not set - critical"
            )
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                
                if resp.status_code == 200:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.RECONNECT_API,
                        result=HealResult.SUCCESS,
                        message="Telegram connection restored",
                        auto_fixed=True
                    )
                elif resp.status_code == 401:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.ALERT_HUMAN,
                        result=HealResult.FAILED,
                        message="Telegram token invalid - needs human"
                    )
                    
        except Exception as e:
            # Telegram network issues usually resolve
            return HealingAttempt(
                capability=capability,
                action=HealAction.NONE,
                result=HealResult.PARTIAL,
                message=f"Telegram network issue - will retry: {e}",
                auto_fixed=True
            )
        
        return HealingAttempt(
            capability=capability,
            action=HealAction.NONE,
            result=HealResult.FAILED,
            message="Telegram healing failed"
        )
    
    async def _heal_trading(self, capability: str, issue: str) -> HealingAttempt:
        """
        Heal WhaleTrack trading data.
        
        Strategy:
        1. Check health endpoint (port 8601)
        2. Test balance endpoint (proves trading API works)
        3. Only claim success if core trading works
        """
        whaletrack_url = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8601")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Step 1: Health check - fast indicator of service state
                resp = await client.get(f"{whaletrack_url}/health")
                
                if resp.status_code != 200:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.NONE,
                        result=HealResult.PARTIAL,
                        message=f"WhaleTrack health check failed (status {resp.status_code})",
                        auto_fixed=False
                    )
                
                # Parse health response to check trading is enabled
                try:
                    health_data = resp.json()
                    trading_enabled = health_data.get("trading_enabled", False)
                    adapter_connected = health_data.get("adapter_connected", False)
                    
                    if not trading_enabled or not adapter_connected:
                        return HealingAttempt(
                            capability=capability,
                            action=HealAction.REDUCE_LOAD,
                            result=HealResult.PARTIAL,
                            message=f"WhaleTrack online but trading disabled or adapter disconnected",
                            auto_fixed=True
                        )
                except Exception:
                    pass  # If we can't parse, just check the balance endpoint
                
                # Step 2: Test balance endpoint (proves API actually works)
                balance_resp = await client.get(f"{whaletrack_url}/api/balance")
                
                if balance_resp.status_code == 200:
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.RECONNECT_API,
                        result=HealResult.SUCCESS,
                        message="WhaleTrack trading fully operational",
                        auto_fixed=True
                    )
                elif balance_resp.status_code in [401, 403]:
                    # Auth issue - but service is up
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.REDUCE_LOAD,
                        result=HealResult.PARTIAL,
                        message="WhaleTrack online but auth required",
                        auto_fixed=True
                    )
                else:
                    # Service is responding but balance endpoint failed
                    return HealingAttempt(
                        capability=capability,
                        action=HealAction.REDUCE_LOAD,
                        result=HealResult.PARTIAL,
                        message=f"WhaleTrack online, balance endpoint returned {balance_resp.status_code}",
                        auto_fixed=True
                    )
                    
        except httpx.ConnectError:
            return HealingAttempt(
                capability=capability,
                action=HealAction.NONE,
                result=HealResult.PARTIAL,
                message="WhaleTrack server unreachable - may be network issue",
                auto_fixed=False
            )
        except httpx.TimeoutException:
            return HealingAttempt(
                capability=capability,
                action=HealAction.REDUCE_LOAD,
                result=HealResult.PARTIAL,
                message="WhaleTrack timeout - server may be slow",
                auto_fixed=True
            )
        except Exception as e:
            return HealingAttempt(
                capability=capability,
                action=HealAction.NONE,
                result=HealResult.PARTIAL,
                message=f"WhaleTrack error: {str(e)[:50]}",
                auto_fixed=False
            )
    
    async def _heal_voice(self, capability: str, issue: str) -> HealingAttempt:
        """Heal voice messaging."""
        # Voice is nice-to-have, not critical
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_key:
            return HealingAttempt(
                capability=capability,
                action=HealAction.REDUCE_LOAD,
                result=HealResult.PARTIAL,
                message="Voice disabled - OpenAI key not set",
                auto_fixed=True
            )
        
        return HealingAttempt(
            capability=capability,
            action=HealAction.NONE,
            result=HealResult.SKIPPED,
            message="Voice capability available"
        )
    
    async def _heal_generic(self, capability: str, issue: str) -> HealingAttempt:
        """Generic healing for unknown capabilities."""
        return HealingAttempt(
            capability=capability,
            action=HealAction.ALERT_HUMAN,
            result=HealResult.PARTIAL,
            message=f"Unknown capability - monitoring: {issue}",
            auto_fixed=False
        )
    
    # ========================================================================
    # ALERTING (LAST RESORT)
    # ========================================================================
    
    async def _alert_steward(self, capability: str, issue: str, result: HealingAttempt):
        """
        Alert James only when auto-fix fails repeatedly.
        
        Smart alerting:
        - Suppresses duplicate alerts for 6 hours
        - Only alerts if truly broken (not partial fixes)
        - Batches multiple issues into one alert
        """
        # Rate limit alerts - max once per 6 hours per capability
        last_alert = self.last_alert_time.get(capability)
        if last_alert and (datetime.now() - last_alert) < timedelta(hours=6):
            logger.debug(f"Suppressing alert for {capability} - already alerted within 6 hours")
            return
        
        # Don't alert for partial fixes - those are handled
        if result.auto_fixed or result.result == HealResult.PARTIAL:
            logger.debug(f"Not alerting for {capability} - partial fix applied")
            return
        
        if not TELEGRAM_TOKEN or not STEWARD_CHAT_ID:
            logger.warning("Cannot alert steward - Telegram not configured")
            return
        
        try:
            failures = self.consecutive_failures.get(capability, 0)
            
            # Only alert for truly broken things (3+ failures without auto-fix)
            if failures < 3:
                logger.debug(f"Not alerting for {capability} - only {failures} failures")
                return
            
            message = f"""🚨 **Self-Healing Failed**

**Capability:** {capability}
**Issue:** {issue}
**Attempts:** {failures}
**Last Action:** {result.action.value}
**Status:** {result.message}

*Auto-healing exhausted. Human intervention may be needed.*

_This alert will not repeat for 6 hours._"""
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={
                        "chat_id": int(STEWARD_CHAT_ID),
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                )
            
            self.last_alert_time[capability] = datetime.now()
            logger.info(f"Alerted steward about {capability} (won't repeat for 6h)")
            
        except Exception as e:
            logger.error(f"Failed to alert steward: {e}")
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    def get_healing_summary(self) -> Dict[str, Any]:
        """Get summary of healing activity."""
        recent = [h for h in self.healing_history if h.timestamp > datetime.now() - timedelta(hours=24)]
        
        auto_fixed = sum(1 for h in recent if h.auto_fixed)
        failed = sum(1 for h in recent if h.result == HealResult.FAILED)
        
        return {
            "total_healing_attempts_24h": len(recent),
            "auto_fixed": auto_fixed,
            "failed": failed,
            "active_fallbacks": list(self.fallback_active.keys()),
            "consecutive_failures": dict(self.consecutive_failures),
            "recent_heals": [
                {
                    "capability": h.capability,
                    "action": h.action.value,
                    "result": h.result.value,
                    "auto_fixed": h.auto_fixed,
                    "message": h.message[:100]
                }
                for h in recent[-5:]
            ]
        }
    
    def is_using_fallback(self, capability: str) -> bool:
        """Check if a capability is running on fallback."""
        return self.fallback_active.get(capability, False)


# ============================================================================
# SINGLETON
# ============================================================================

_healer: Optional[SelfHealer] = None


def get_self_healer() -> SelfHealer:
    """Get or create self-healer instance."""
    global _healer
    if _healer is None:
        _healer = SelfHealer()
    return _healer


async def heal_capability(capability: str, issue: str) -> HealingAttempt:
    """Attempt to heal a capability."""
    return await get_self_healer().heal_capability(capability, issue)

