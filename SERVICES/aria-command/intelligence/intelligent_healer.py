"""
INTELLIGENT HEALER
===================

Self-healing with verification and learning.

The WhaleTrack failure taught us:
1. Don't just retry the same thing
2. Understand WHY it failed
3. Apply the right fix
4. VERIFY the fix actually worked
5. Learn from the experience

This is the upgraded self-healer that actually works.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import httpx

from .root_cause import RootCauseAnalyzer, RootCause, CauseCategory, get_root_cause_analyzer
from .failure_memory import FailureMemory, Fix, get_failure_memory
from .real_verification import RealVerifier, VerificationResult, get_verifier
from .config_contracts import ConfigContract, ConfigDrift, DriftAction, get_config_contract

logger = logging.getLogger("aria.intelligence.healer")


class HealStrategy(str, Enum):
    """Healing strategies."""
    CONFIG_FIX = "config_fix"
    RESTART = "restart"
    RECONNECT = "reconnect"
    GRACEFUL_DEGRADE = "graceful_degrade"
    FIX_DEPENDENCY = "fix_dependency"
    APPLY_KNOWN_FIX = "apply_known_fix"
    MANUAL = "manual"


@dataclass
class HealResult:
    """Result of a healing attempt."""
    service: str
    issue: str
    strategy: HealStrategy
    fix_applied: str
    success: bool
    verified: bool  # Did we actually verify the fix worked?
    root_cause: Optional[RootCause] = None
    verification_result: Optional[VerificationResult] = None
    learned_from: Optional[int] = None  # ID of similar failure we learned from
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def truly_fixed(self) -> bool:
        """A fix is truly successful only if verified."""
        return self.success and self.verified


class IntelligentHealer:
    """
    Intelligent self-healing system.
    
    Key improvements over the old self-healer:
    1. Root cause analysis before fixing
    2. Memory of past fixes
    3. Verification after fixing
    4. Learning from results
    5. Smart alert suppression (no spam!)
    """
    
    # Services that are informational-only (don't alert if they fail)
    INFORMATIONAL_SERVICES = {"hyperliquid", "unknown"}
    
    # Minimum uptime before alerts fire (let system stabilize after restart)
    STARTUP_GRACE_PERIOD = timedelta(minutes=10)
    
    # How long between alerts for same service
    ALERT_COOLDOWN = timedelta(hours=12)
    
    # How many consecutive failures before alerting
    ALERT_THRESHOLD = 5
    
    def __init__(self):
        self.analyzer = get_root_cause_analyzer()
        self.memory = get_failure_memory()
        self.verifier = get_verifier()
        self.config = get_config_contract()
        self.http = httpx.AsyncClient(timeout=30.0)
        
        self.healing_history: List[HealResult] = []
        self.consecutive_failures: Dict[str, int] = {}
        self.last_alert_time: Dict[str, datetime] = {}
        self.startup_time = datetime.now()
        
        logger.info("IntelligentHealer initialized with smart alerting")
    
    async def close(self):
        """Close resources."""
        await self.http.aclose()
        await self.analyzer.close()
        await self.verifier.close()
    
    async def heal(
        self,
        service: str,
        issue: str,
        context: Dict[str, Any] = None
    ) -> HealResult:
        """
        Attempt to heal a service issue intelligently.
        
        Process:
        1. Analyze root cause
        2. Check memory for known fix
        3. Apply fix
        4. VERIFY fix worked
        5. Learn from result
        """
        start_time = datetime.now()
        context = context or {}
        
        logger.info(f"🩹 Healing {service}: {issue}")
        
        # 1. Analyze root cause
        root_cause = await self.analyzer.analyze_failure(service, issue, context)
        logger.info(f"Root cause: {root_cause}")
        
        # 2. Check memory for known fix
        known_fix = self.memory.get_best_fix(f"{service}:{root_cause.description}")
        if not known_fix:
            # Try symptom-based matching
            known_fix = self.memory.get_best_fix_for_symptom(service, issue)
        
        learned_from = None
        
        # 3. Determine and apply fix
        if known_fix and known_fix.is_reliable:
            logger.info(f"Applying known fix (success rate: {known_fix.success_rate:.0%})")
            result = await self._apply_known_fix(service, issue, known_fix, root_cause)
            learned_from = True  # TODO: track actual failure ID
        else:
            # Apply fix based on root cause
            result = await self._apply_intelligent_fix(service, issue, root_cause)
        
        # 4. VERIFY the fix actually worked
        duration = (datetime.now() - start_time).total_seconds() * 1000
        verification = await self.verifier.verify_service(service)
        
        result.verified = verification.passed
        result.success = result.success and verification.passed
        result.verification_result = verification
        result.duration_ms = duration
        result.root_cause = root_cause
        
        # 5. Learn from result
        self._learn_from_result(result)
        
        # Update consecutive failures
        if result.truly_fixed:
            self.consecutive_failures[service] = 0
            logger.info(f"✅ Healed {service} (verified)")
        else:
            self.consecutive_failures[service] = self.consecutive_failures.get(service, 0) + 1
            logger.warning(f"⚠️ Healing {service} failed or unverified")
            
            # Smart alerting with multiple guards
            should_alert = await self._should_alert(service, result)
            if should_alert:
                await self._alert_steward(service, issue, result)
        
        self.healing_history.append(result)
        return result
    
    async def _apply_known_fix(
        self,
        service: str,
        issue: str,
        fix: Fix,
        root_cause: RootCause
    ) -> HealResult:
        """Apply a fix we've learned works."""
        logger.info(f"Applying learned fix: {fix.fix_details}")
        
        try:
            # Parse fix type and apply
            if fix.fix_type == "config_change":
                success = await self._apply_config_fix(fix.fix_details)
            elif fix.fix_type == "restart":
                success = await self._apply_restart(service)
            elif fix.fix_type == "reconnect":
                success = await self._apply_reconnect(service)
            else:
                # Generic application
                success = await self._apply_generic_fix(service, fix.fix_details)
            
            return HealResult(
                service=service,
                issue=issue,
                strategy=HealStrategy.APPLY_KNOWN_FIX,
                fix_applied=fix.fix_details,
                success=success,
                verified=False  # Will be set after verification
            )
            
        except Exception as e:
            logger.error(f"Error applying known fix: {e}")
            return HealResult(
                service=service,
                issue=issue,
                strategy=HealStrategy.APPLY_KNOWN_FIX,
                fix_applied=f"Failed: {e}",
                success=False,
                verified=False
            )
    
    async def _apply_intelligent_fix(
        self,
        service: str,
        issue: str,
        root_cause: RootCause
    ) -> HealResult:
        """Apply a fix based on root cause analysis."""
        logger.info(f"Applying intelligent fix based on: {root_cause.category.value}")
        
        strategy = HealStrategy.MANUAL
        fix_applied = ""
        success = False
        
        try:
            if root_cause.category == CauseCategory.CONFIG:
                strategy = HealStrategy.CONFIG_FIX
                # Check for auto-fixable config drifts
                drifts = self.config.validate_all()
                service_drifts = [d for d in drifts if service in d.description.lower() or 
                                 service in d.key.lower()]
                
                if service_drifts:
                    fixed = self.config.apply_fixes(service_drifts)
                    if fixed:
                        fix_applied = f"Fixed config: {', '.join(d.key for d in fixed)}"
                        success = True
                    else:
                        fix_applied = f"Config drift detected but cannot auto-fix"
                else:
                    fix_applied = root_cause.suggested_fix
            
            elif root_cause.category == CauseCategory.DEPENDENCY:
                strategy = HealStrategy.FIX_DEPENDENCY
                # Try to heal the dependency first
                if root_cause.dependencies_affected:
                    dep = root_cause.dependencies_affected[0]
                    dep_result = await self.heal(dep, f"Dependency of {service}")
                    success = dep_result.truly_fixed
                    fix_applied = f"Fixed dependency {dep}: {dep_result.fix_applied}"
                else:
                    fix_applied = "Dependency issue but cannot identify which"
            
            elif root_cause.category == CauseCategory.SERVICE:
                strategy = HealStrategy.RESTART
                success = await self._apply_restart(service)
                fix_applied = f"Restarted {service}"
            
            elif root_cause.category == CauseCategory.NETWORK:
                strategy = HealStrategy.RECONNECT
                success = await self._apply_reconnect(service)
                fix_applied = f"Reconnected to {service}"
            
            elif root_cause.category == CauseCategory.RESOURCE:
                strategy = HealStrategy.GRACEFUL_DEGRADE
                fix_applied = "Resource issue - operating in degraded mode"
                success = True  # Degraded mode is still operational
            
            else:
                strategy = HealStrategy.MANUAL
                fix_applied = root_cause.suggested_fix
                success = False
            
        except Exception as e:
            logger.error(f"Error in intelligent fix: {e}")
            fix_applied = f"Fix error: {e}"
            success = False
        
        return HealResult(
            service=service,
            issue=issue,
            strategy=strategy,
            fix_applied=fix_applied,
            success=success,
            verified=False
        )
    
    async def _apply_config_fix(self, fix_details: str) -> bool:
        """Apply a configuration fix."""
        # Parse fix details for key=value
        if "=" in fix_details:
            parts = fix_details.split("=", 1)
            key = parts[0].strip()
            value = parts[1].strip()
            os.environ[key] = value
            logger.info(f"Set {key}={value[:20]}...")
            return True
        return False
    
    async def _apply_restart(self, service: str) -> bool:
        """Attempt to restart a service."""
        # This would integrate with systemctl or Docker
        # For now, we just note that a restart is needed
        logger.warning(f"Restart needed for {service} - manual intervention required")
        return False
    
    async def _apply_reconnect(self, service: str) -> bool:
        """Attempt to reconnect to a service."""
        # Force a fresh connection check
        try:
            result = await self.verifier.verify_service(service)
            return result.passed
        except Exception:
            return False
    
    async def _apply_generic_fix(self, service: str, fix_details: str) -> bool:
        """Apply a generic fix."""
        logger.info(f"Applying generic fix for {service}: {fix_details}")
        # For now, just try reconnection
        return await self._apply_reconnect(service)
    
    def _learn_from_result(self, result: HealResult):
        """Learn from a healing attempt."""
        self.memory.record_failure(
            service=result.service,
            symptom=result.issue,
            root_cause=result.root_cause.description if result.root_cause else "unknown",
            root_cause_confidence=result.root_cause.confidence if result.root_cause else 0,
            fix_applied=result.fix_applied,
            fix_worked=result.truly_fixed,
            time_to_fix=int(result.duration_ms / 1000),
            category=result.root_cause.category.value if result.root_cause else "unknown",
            fix_type=result.strategy.value
        )
        
        logger.info(f"Learned from healing attempt: {result.service} - "
                   f"{'SUCCESS' if result.truly_fixed else 'FAILED'}")
    
    async def _should_alert(self, service: str, result: HealResult) -> bool:
        """
        Determine if we should alert the steward.
        
        Guards:
        1. Startup grace period (let system stabilize)
        2. Informational-only services (never alert)
        3. Cooldown period between alerts
        4. Minimum consecutive failures threshold
        5. Manual intervention issues only
        """
        # Guard 1: Startup grace period
        if datetime.now() - self.startup_time < self.STARTUP_GRACE_PERIOD:
            logger.debug(f"Suppressing alert for {service} - still in startup grace period")
            return False
        
        # Guard 2: Informational-only services
        if service.lower() in self.INFORMATIONAL_SERVICES:
            logger.debug(f"Suppressing alert for {service} - informational service")
            return False
        
        # Guard 3: Cooldown period
        last_alert = self.last_alert_time.get(service)
        if last_alert and (datetime.now() - last_alert) < self.ALERT_COOLDOWN:
            logger.debug(f"Suppressing alert for {service} - in cooldown period")
            return False
        
        # Guard 4: Minimum failures threshold
        failures = self.consecutive_failures.get(service, 0)
        if failures < self.ALERT_THRESHOLD:
            logger.debug(f"Suppressing alert for {service} - only {failures} failures (need {self.ALERT_THRESHOLD})")
            return False
        
        # Guard 5: Only alert for manual intervention issues
        if result.strategy != HealStrategy.MANUAL and result.strategy != HealStrategy.RESTART:
            # If we applied a fix that might work next time, don't alert yet
            if result.success:  # Fix seemed to work, just not verified
                logger.debug(f"Suppressing alert for {service} - fix applied, awaiting verification")
                return False
        
        return True
    
    async def _alert_steward(self, service: str, issue: str, result: HealResult):
        """Alert James when auto-fix fails repeatedly."""
        # Final cooldown check (redundant but safe)
        last_alert = self.last_alert_time.get(service)
        if last_alert and (datetime.now() - last_alert) < self.ALERT_COOLDOWN:
            return
        
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("SUNHEART_CHAT_ID")
        
        if not telegram_token or not chat_id:
            logger.warning("Cannot alert - Telegram not configured")
            return
        
        try:
            root_cause_desc = result.root_cause.description if result.root_cause else "Unknown"
            
            failures = self.consecutive_failures.get(service, 0)
            message = f"""🚨 **Intelligent Healer Alert**

**Service:** {service}
**Issue:** {issue}
**Root Cause:** {root_cause_desc}
**Fix Attempted:** {result.fix_applied}
**Consecutive Failures:** {failures}

*After {failures} attempts, this needs human review.*

_Next alert in 12 hours if still failing._"""
            
            await self.http.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={
                    "chat_id": int(chat_id),
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            self.last_alert_time[service] = datetime.now()
            logger.info(f"Alerted steward about {service}")
            
        except Exception as e:
            logger.error(f"Failed to alert steward: {e}")
    
    def get_healing_summary(self) -> Dict[str, Any]:
        """Get summary of healing activity."""
        recent = [h for h in self.healing_history 
                 if datetime.fromisoformat(h.timestamp) > datetime.now() - timedelta(hours=24)]
        
        truly_fixed = sum(1 for h in recent if h.truly_fixed)
        verified = sum(1 for h in recent if h.verified)
        
        by_strategy = {}
        for h in recent:
            strategy = h.strategy.value
            if strategy not in by_strategy:
                by_strategy[strategy] = {"count": 0, "success": 0}
            by_strategy[strategy]["count"] += 1
            if h.truly_fixed:
                by_strategy[strategy]["success"] += 1
        
        return {
            "period": "24h",
            "total_attempts": len(recent),
            "truly_fixed": truly_fixed,
            "verified_rate": verified / len(recent) if recent else 0,
            "success_rate": truly_fixed / len(recent) if recent else 0,
            "by_strategy": by_strategy,
            "consecutive_failures": dict(self.consecutive_failures),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_healer: Optional[IntelligentHealer] = None


def get_intelligent_healer() -> IntelligentHealer:
    """Get or create the intelligent healer instance."""
    global _healer
    if _healer is None:
        _healer = IntelligentHealer()
    return _healer


async def heal_service(
    service: str,
    issue: str,
    context: Dict[str, Any] = None
) -> HealResult:
    """Convenience function to heal a service."""
    return await get_intelligent_healer().heal(service, issue, context)


