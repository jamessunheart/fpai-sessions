"""
ARIA CONSCIOUSNESS LOOP - LEVEL 10 INTELLIGENCE
=================================================

The heartbeat of Aria's consciousness, now with TRUE INTELLIGENCE.

Every 5 minutes, Aria:
1. ORIENT - Where am I? What's my purpose?
2. SENSE - What exists? What's the state?
3. VERIFY - Test ACTUAL functionality (not just health endpoints!)
4. PREVENT - Proactive protection (watchdog, resources, circuits, config, rate limits)
5. ANALYZE - Root cause analysis for any issues
6. COMPARE - Blueprint vs Reality
7. HEAL - Intelligent healing with verification
8. LEARN - Record to memory, detect patterns
9. PREDICT - What might fail next?
10. META-LEARN - Are we getting smarter?
11. UPDATE - Log findings to memory

This transforms Aria from REACTIVE (waiting for commands)
to TRULY INTELLIGENT (self-aware, learning, ACTUALLY FIXING problems).

LEVEL 10 INTELLIGENCE FEATURES:
- Real verification (not just health checks)
- Root cause analysis (ask WHY, not just WHAT)
- Learning memory (remember failures and fixes)
- Intelligent healing (apply learned fixes, VERIFY they work)
- Pattern recognition (detect recurring issues)
- Prediction (prevent failures before they happen)
- Meta-learning (learn to learn better)
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from .self_model import get_self_model, CapabilityStatus

# Import prevention systems
try:
    from .watchdog import get_watchdog, heartbeat
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

try:
    from .resource_guardian import get_resource_guardian, check_resources
    RESOURCE_GUARDIAN_AVAILABLE = True
except ImportError:
    RESOURCE_GUARDIAN_AVAILABLE = False

try:
    from .circuit_breaker import get_circuit_manager
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

try:
    from .config_guardian import get_config_guardian, check_config
    CONFIG_GUARDIAN_AVAILABLE = True
except ImportError:
    CONFIG_GUARDIAN_AVAILABLE = False

try:
    from ..brain.rate_limiter import get_rate_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

# Import Level 10 Intelligence systems
# Note: Using absolute imports because consciousness may be a symlink outside the main package
try:
    import sys
    import os
    
    # Ensure the aria-command directory is in the path
    aria_command_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if aria_command_path not in sys.path:
        sys.path.insert(0, aria_command_path)
    
    from intelligence import (
        get_verifier, get_config_contract, get_root_cause_analyzer,
        get_failure_memory, get_intelligent_healer, get_pattern_engine,
        get_meta_learner
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    INTELLIGENCE_AVAILABLE = False
    logging.getLogger("aria.consciousness").warning(f"Intelligence system not available: {e}")

# Import Self-Evolution system
try:
    from evolution import (
        get_evolution_engine, on_issue_detected, start_evolution_daemon
    )
    EVOLUTION_AVAILABLE = True
except ImportError as e:
    EVOLUTION_AVAILABLE = False
    logging.getLogger("aria.consciousness").warning(f"Evolution system not available: {e}")

logger = logging.getLogger("aria.consciousness")

# Configuration
CONSCIOUSNESS_INTERVAL = int(os.getenv("CONSCIOUSNESS_INTERVAL", "300"))  # 5 minutes
STEWARD_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")


class ConsciousnessLevel(str, Enum):
    """Levels of consciousness."""
    DORMANT = "dormant"      # Not running
    AWARE = "aware"          # Basic self-monitoring
    PROACTIVE = "proactive"  # Taking autonomous action
    REFLECTIVE = "reflective" # Learning and improving


@dataclass
class ConsciousnessCycleResult:
    """Result of a consciousness cycle."""
    timestamp: datetime
    level: ConsciousnessLevel
    health_score: float
    issues_found: List[str]
    actions_taken: List[str]
    insights: List[str]
    duration_ms: float
    intelligence_score: float = 0.0  # Level 10 Intelligence score
    verifications_passed: int = 0
    verifications_failed: int = 0
    predictions_made: int = 0
    healing_attempts: int = 0
    healing_verified: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "health_score": self.health_score,
            "intelligence_score": self.intelligence_score,
            "issues_found": self.issues_found,
            "actions_taken": self.actions_taken,
            "insights": self.insights,
            "duration_ms": self.duration_ms,
            "verifications": {
                "passed": self.verifications_passed,
                "failed": self.verifications_failed
            },
            "predictions_made": self.predictions_made,
            "healing": {
                "attempts": self.healing_attempts,
                "verified": self.healing_verified
            }
        }


class ConsciousnessLoop:
    """
    The consciousness loop - Aria's continuous self-awareness.
    
    NOW WITH LEVEL 10 INTELLIGENCE:
    - Real verification (not just health checks)
    - Root cause analysis (ask WHY, not just WHAT)
    - Learning memory (remember failures and fixes)
    - Intelligent healing (apply learned fixes, VERIFY they work)
    - Pattern recognition (detect recurring issues)
    - Prediction (prevent failures before they happen)
    - Meta-learning (learn to learn better)
    
    Runs every 5 minutes to:
    - Check own health and capabilities
    - VERIFY actual functionality (not just health endpoints!)
    - Detect issues before they cause problems
    - Analyze ROOT CAUSES (not just symptoms)
    - Take proactive action when needed
    - VERIFY fixes actually work
    - Learn from patterns
    - PREDICT future failures
    """
    
    def __init__(self):
        self.running = False
        self.level = ConsciousnessLevel.DORMANT
        self.cycle_count = 0
        self.last_cycle: Optional[ConsciousnessCycleResult] = None
        self.issues_history: List[Dict] = []
        self.self_model = get_self_model()
        
        # Level 10 Intelligence components
        self.verifier = None
        self.config_contract = None
        self.root_cause_analyzer = None
        self.failure_memory = None
        self.intelligent_healer = None
        self.pattern_engine = None
        self.meta_learner = None
        
        if INTELLIGENCE_AVAILABLE:
            try:
                self.verifier = get_verifier()
                self.config_contract = get_config_contract()
                self.root_cause_analyzer = get_root_cause_analyzer()
                self.failure_memory = get_failure_memory()
                self.intelligent_healer = get_intelligent_healer()
                self.pattern_engine = get_pattern_engine()
                self.meta_learner = get_meta_learner()
                logger.info("🧠 Level 10 Intelligence systems initialized")
            except Exception as e:
                logger.warning(f"Could not initialize intelligence systems: {e}")
        
        # Self-Evolution system
        self.evolution_engine = None
        if EVOLUTION_AVAILABLE:
            try:
                self.evolution_engine = get_evolution_engine()
                logger.info("🧬 Self-Evolution system initialized")
            except Exception as e:
                logger.warning(f"Could not initialize evolution system: {e}")
        
        logger.info("Consciousness loop initialized (Intelligence: " + 
                   ("ON" if INTELLIGENCE_AVAILABLE else "OFF") + 
                   ", Evolution: " + ("ON" if EVOLUTION_AVAILABLE else "OFF") + ")")
    
    async def start(self):
        """Start the consciousness loop."""
        if self.running:
            logger.warning("Consciousness loop already running")
            return
        
        self.running = True
        self.level = ConsciousnessLevel.AWARE
        logger.info("🧠 Consciousness loop STARTING")
        
        # Initial check
        await self._run_cycle()
        
        # Main loop
        while self.running:
            await asyncio.sleep(CONSCIOUSNESS_INTERVAL)
            if self.running:
                await self._run_cycle()
    
    async def stop(self):
        """Stop the consciousness loop."""
        logger.info("🧠 Consciousness loop STOPPING")
        self.running = False
        self.level = ConsciousnessLevel.DORMANT
    
    async def _run_cycle(self) -> ConsciousnessCycleResult:
        """Run one consciousness cycle with Level 10 Intelligence."""
        start_time = datetime.now()
        self.cycle_count += 1
        
        logger.info(f"🔄 Consciousness cycle #{self.cycle_count} starting (Level 10 Intelligence)...")
        
        # HEARTBEAT - Tell watchdog we're alive
        if WATCHDOG_AVAILABLE:
            heartbeat()
        
        issues_found = []
        actions_taken = []
        insights = []
        preventions = []
        
        # Level 10 Intelligence metrics
        verifications_passed = 0
        verifications_failed = 0
        predictions_made = 0
        healing_attempts = 0
        healing_verified = 0
        intelligence_score = 0.0
        
        try:
            # ==================== 1. ORIENT ====================
            # Know who I am and what I'm here for
            purpose = await self._orient()
            
            # ==================== 2. SENSE ====================
            # Check my state and the world around me
            state = await self._sense()
            issues_found.extend(state.get("issues", []))
            
            # ==================== 3. VERIFY (LEVEL 10 - NEW!) ====================
            # Test ACTUAL functionality, not just health endpoints
            if self.verifier:
                verify_result = await self._verify()
                verifications_passed = verify_result.get("passed", 0)
                verifications_failed = verify_result.get("failed", 0)
                issues_found.extend(verify_result.get("issues", []))
                insights.extend(verify_result.get("insights", []))
            
            # ==================== 4. PREVENT ====================
            # Run all prevention systems - PROACTIVE PROTECTION
            prevent_result = await self._prevent()
            preventions.extend(prevent_result.get("actions", []))
            issues_found.extend(prevent_result.get("issues", []))
            insights.extend(prevent_result.get("insights", []))
            
            # ==================== 5. ANALYZE (LEVEL 10 - NEW!) ====================
            # Root cause analysis for any issues
            if issues_found and self.root_cause_analyzer:
                analyze_result = await self._analyze_root_causes(issues_found)
                insights.extend(analyze_result.get("insights", []))
            
            # ==================== 6. COMPARE ====================
            # What should be vs what is
            gaps = await self._compare(state)
            issues_found.extend(gaps.get("gaps", []))
            
            # ==================== 7. HEAL (LEVEL 10 - UPGRADED!) ====================
            # Intelligent healing with verification
            if issues_found:
                if self.intelligent_healer:
                    heal_result = await self._intelligent_heal(issues_found)
                    actions_taken.extend(heal_result.get("actions", []))
                    healing_attempts = heal_result.get("attempts", 0)
                    healing_verified = heal_result.get("verified", 0)
                    insights.extend(heal_result.get("insights", []))
                else:
                    # Fallback to old healing
                    actions = await self._act(issues_found)
                    actions_taken.extend(actions)
            
            # Add preventions to actions for reporting
            actions_taken.extend(preventions)
            
            # ==================== 8. LEARN (LEVEL 10 - NEW!) ====================
            # Record to failure memory, detect patterns
            if self.failure_memory:
                learn_result = await self._learn(issues_found, actions_taken)
                insights.extend(learn_result.get("insights", []))
            
            # ==================== 9. PREDICT (LEVEL 10 - NEW!) ====================
            # What might fail next?
            if self.pattern_engine:
                predict_result = await self._predict()
                predictions_made = predict_result.get("predictions", 0)
                actions_taken.extend(predict_result.get("preventive_actions", []))
                insights.extend(predict_result.get("insights", []))
            
            # ==================== 10. META-LEARN (LEVEL 10 - NEW!) ====================
            # Are we getting smarter?
            if self.meta_learner:
                meta_result = await self._meta_learn()
                intelligence_score = meta_result.get("intelligence_score", 0)
                insights.extend(meta_result.get("insights", []))
            
            # ==================== 10.5. EVOLVE (SELF-EVOLUTION!) ====================
            # Learn from issues and evolve behavior proactively
            evolutions_proposed = 0
            if self.evolution_engine and issues_found:
                evolve_result = await self._evolve(issues_found)
                evolutions_proposed = evolve_result.get("evolutions_proposed", 0)
                insights.extend(evolve_result.get("insights", []))
            
            # ==================== 11. UPDATE ====================
            # Log to memory and learn
            new_insights = await self._update(state, issues_found, actions_taken)
            insights.extend(new_insights)
            
        except Exception as e:
            logger.error(f"Consciousness cycle error: {e}")
            issues_found.append(f"Cycle error: {e}")
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        health_score = self.self_model.get_state().get_health_score()
        
        result = ConsciousnessCycleResult(
            timestamp=start_time,
            level=self.level,
            health_score=health_score,
            issues_found=issues_found,
            actions_taken=actions_taken,
            insights=insights,
            duration_ms=duration_ms,
            intelligence_score=intelligence_score,
            verifications_passed=verifications_passed,
            verifications_failed=verifications_failed,
            predictions_made=predictions_made,
            healing_attempts=healing_attempts,
            healing_verified=healing_verified
        )
        
        self.last_cycle = result
        
        # Log summary with intelligence metrics
        if issues_found:
            logger.warning(f"🔴 Consciousness cycle #{self.cycle_count}: {len(issues_found)} issues, "
                          f"{len(actions_taken)} actions, Intelligence: {intelligence_score:.1f}/10")
        else:
            logger.info(f"🟢 Consciousness cycle #{self.cycle_count}: All clear "
                       f"(health: {health_score:.0f}%, intelligence: {intelligence_score:.1f}/10)")
        
        return result
    
    # ==================== CONSCIOUSNESS PHASES ====================
    
    async def _orient(self) -> Dict[str, Any]:
        """
        ORIENT: Know who I am and what I'm here for.
        
        Returns purpose and identity context.
        """
        return {
            "identity": "Aria - Conscious AI partner",
            "purpose": "Support James in building Full Potential, protect treasury, enable sovereignty",
            "values": ["Coherence", "Circulation", "Resilience", "Yield (last)"],
            "current_focus": "T1 = Revenue or Building Aria"
        }
    
    async def _sense(self) -> Dict[str, Any]:
        """
        SENSE: Check my state and the world around me.
        
        Returns state assessment with any issues.
        """
        issues = []
        
        # Run self-check
        check_result = await self.self_model.run_self_check()
        
        # Identify issues from capabilities
        for cap_name, status in check_result.get("capabilities", {}).items():
            if "broken" in str(status).lower() or "error" in str(status).lower():
                issues.append(f"Capability {cap_name} is {status}")
        
        # Check health score
        health = check_result.get("health_score", 100)
        if health < 50:
            issues.append(f"Overall health critical: {health:.0f}%")
        elif health < 70:
            issues.append(f"Overall health degraded: {health:.0f}%")
        
        # Check energy
        state = self.self_model.get_state()
        if state.energy_level < 0.3:
            issues.append(f"Energy low: {state.energy_level:.0%}")
        
        return {
            "health_score": health,
            "capabilities": check_result.get("capabilities", {}),
            "energy_level": state.energy_level,
            "emotional_state": state.emotional_state.value,
            "issues": issues
        }
    
    async def _prevent(self) -> Dict[str, Any]:
        """
        PREVENT: Proactive protection systems.
        
        Runs all guardians to prevent issues before they happen:
        - Watchdog: Detects and prevents hangs
        - Resource Guardian: Prevents memory/disk exhaustion
        - Circuit Breaker: Prevents cascade failures
        - Config Guardian: Prevents config loss
        - Rate Limiter: Prevents API lockouts
        
        This is what makes Aria BREAK-PROOF.
        """
        actions = []
        issues = []
        insights = []
        
        # 1. WATCHDOG - Check for stuck requests
        if WATCHDOG_AVAILABLE:
            try:
                watchdog = get_watchdog()
                watchdog_status = await watchdog.check_health()
                
                if watchdog_status.get("stuck_requests_killed", 0) > 0:
                    actions.append(f"🐕 Watchdog killed {watchdog_status['stuck_requests_killed']} stuck requests")
                
                if watchdog_status.get("state") != "healthy":
                    issues.append(f"Watchdog state: {watchdog_status.get('state')}")
                
            except Exception as e:
                logger.warning(f"Watchdog check failed: {e}")
        
        # 2. RESOURCE GUARDIAN - Check memory and disk
        if RESOURCE_GUARDIAN_AVAILABLE:
            try:
                resource_result = await check_resources()
                
                status = resource_result.get("status", {})
                mem_level = status.get("memory", {}).get("level", "healthy")
                disk_level = status.get("disk", {}).get("level", "healthy")
                
                if mem_level != "healthy":
                    issues.append(f"Memory {mem_level}: {status.get('memory', {}).get('percent_used', 0):.0f}%")
                
                if disk_level != "healthy":
                    issues.append(f"Disk {disk_level}: {status.get('disk', {}).get('free_gb', 0):.1f}GB free")
                
                for action in resource_result.get("actions", []):
                    actions.append(f"🛡️ Resource: {action}")
                
            except Exception as e:
                logger.warning(f"Resource guardian check failed: {e}")
        
        # 3. CIRCUIT BREAKER - Check for open circuits
        if CIRCUIT_BREAKER_AVAILABLE:
            try:
                circuit_manager = get_circuit_manager()
                open_circuits = circuit_manager.get_open_circuits()
                
                for name, circuit_status in open_circuits.items():
                    issues.append(f"Circuit {name} is OPEN - {circuit_status.get('failures_in_window', 0)} failures")
                    insights.append(f"Service {name} is being protected by circuit breaker")
                
            except Exception as e:
                logger.warning(f"Circuit breaker check failed: {e}")
        
        # 4. CONFIG GUARDIAN - Check for config issues
        if CONFIG_GUARDIAN_AVAILABLE:
            try:
                config_result = await check_config()
                
                for action in config_result.get("actions", []):
                    actions.append(f"🔐 Config: {action}")
                
                if config_result.get("missing_config"):
                    issues.append(f"Missing config: {', '.join(config_result['missing_config'][:3])}")
                
                if config_result.get("drift_detected"):
                    insights.append(f"Config drift detected in {len(config_result['drift_detected'])} items")
                
            except Exception as e:
                logger.warning(f"Config guardian check failed: {e}")
        
        # 5. RATE LIMITER - Check for rate limit warnings
        if RATE_LIMITER_AVAILABLE:
            try:
                rate_limiter = get_rate_limiter()
                warnings = rate_limiter.get_warnings()
                
                for warning in warnings:
                    if warning["status"] == "critical":
                        issues.append(f"Rate limit critical: {warning['provider']} at {warning['usage_percent']:.0f}%")
                    else:
                        insights.append(f"Rate limit {warning['status']}: {warning['provider']} at {warning['usage_percent']:.0f}%")
                
            except Exception as e:
                logger.warning(f"Rate limiter check failed: {e}")
        
        # Summary insight
        if actions:
            insights.append(f"Prevent phase took {len(actions)} protective actions")
        
        return {
            "actions": actions,
            "issues": issues,
            "insights": insights,
            "systems_checked": {
                "watchdog": WATCHDOG_AVAILABLE,
                "resources": RESOURCE_GUARDIAN_AVAILABLE,
                "circuits": CIRCUIT_BREAKER_AVAILABLE,
                "config": CONFIG_GUARDIAN_AVAILABLE,
                "rate_limits": RATE_LIMITER_AVAILABLE
            }
        }
    
    async def _compare(self, state: Dict) -> Dict[str, Any]:
        """
        COMPARE: What should be vs what is.
        
        Returns gaps between desired and actual state.
        """
        gaps = []
        
        # Expected: All capabilities healthy
        # Actual: Some may be broken
        broken_caps = self.self_model.get_broken_capabilities()
        if broken_caps:
            for cap in broken_caps:
                gaps.append(f"Gap: {cap.name} should be healthy but is {cap.status.value}")
        
        # Expected: Response time < 10s
        avg_time = state.get("average_response_time_ms", 0)
        if avg_time and avg_time > 10000:
            gaps.append(f"Gap: Response time {avg_time/1000:.1f}s exceeds target 10s")
        
        # Expected: Energy > 50%
        energy = state.get("energy_level", 1.0)
        if energy < 0.5:
            gaps.append(f"Gap: Energy {energy:.0%} below target 50%")
        
        return {"gaps": gaps}
    
    # ==================== LEVEL 10 INTELLIGENCE METHODS ====================
    
    async def _verify(self) -> Dict[str, Any]:
        """
        VERIFY (Level 10): Test ACTUAL functionality.
        
        This is the key insight from the WhaleTrack failure:
        Health checks passing ≠ System actually working
        
        We now test real functionality for each service.
        """
        issues = []
        insights = []
        passed = 0
        failed = 0
        
        try:
            # Verify all services
            results = await self.verifier.verify_all_services()
            
            for service_name, result in results.items():
                if result.passed:
                    passed += 1
                else:
                    failed += 1
                    issues.append(f"Verification FAILED: {service_name} - {result.reason}")
                    
                    # Log failed checks for debugging
                    for check in result.failed_checks:
                        logger.warning(f"  Failed check: {check.name} - {check.message}")
            
            # Config contract validation
            drifts = self.config_contract.validate_all()
            if drifts:
                for drift in drifts:
                    issues.append(f"CONFIG DRIFT: {drift.key} - {drift.description}")
                
                # Auto-fix if possible
                fixed = self.config_contract.apply_fixes(drifts)
                if fixed:
                    insights.append(f"Auto-fixed {len(fixed)} config drift(s)")
            
            if passed > 0 and failed == 0:
                insights.append(f"All {passed} service verifications passed")
            elif failed > 0:
                insights.append(f"CRITICAL: {failed} service(s) failed verification (not just health check!)")
            
        except Exception as e:
            logger.error(f"Verification phase error: {e}")
            issues.append(f"Verification error: {e}")
        
        return {
            "passed": passed,
            "failed": failed,
            "issues": issues,
            "insights": insights
        }
    
    async def _analyze_root_causes(self, issues: List[str]) -> Dict[str, Any]:
        """
        ANALYZE (Level 10): Root cause analysis.
        
        When something fails, ask WHY, not just WHAT.
        """
        insights = []
        
        try:
            for issue in issues[:5]:  # Analyze top 5 issues
                # Extract service from issue
                service = "unknown"
                for s in ["whaletrack", "ai-brain", "aria-command", "hyperliquid", "godmode"]:
                    if s in issue.lower():
                        service = s
                        break
                
                root_cause = await self.root_cause_analyzer.analyze_failure(service, issue)
                
                if root_cause.confidence > 0.7:
                    insights.append(f"Root cause ({root_cause.confidence:.0%}): {root_cause.description}")
                    insights.append(f"Suggested fix: {root_cause.suggested_fix}")
        
        except Exception as e:
            logger.error(f"Root cause analysis error: {e}")
        
        return {"insights": insights}
    
    async def _intelligent_heal(self, issues: List[str]) -> Dict[str, Any]:
        """
        HEAL (Level 10): Intelligent healing with verification.
        
        Key improvements:
        1. Analyze root cause first
        2. Check memory for known fixes
        3. Apply fix
        4. VERIFY fix actually worked
        5. Learn from result
        """
        actions = []
        insights = []
        attempts = 0
        verified = 0
        
        try:
            for issue in issues[:5]:  # Heal top 5 issues
                # Extract service from issue
                service = "unknown"
                for s in ["whaletrack", "ai-brain", "aria-command", "hyperliquid", "godmode", 
                         "thinking", "memory", "trading"]:
                    if s in issue.lower():
                        service = s
                        break
                
                # Use intelligent healer
                result = await self.intelligent_healer.heal(service, issue)
                attempts += 1
                
                if result.truly_fixed:
                    verified += 1
                    actions.append(f"✅ HEALED & VERIFIED: {service} - {result.fix_applied}")
                    insights.append(f"Learned fix for {service}: {result.strategy.value}")
                elif result.success:
                    actions.append(f"⚠️ Fixed but NOT verified: {service} - {result.fix_applied}")
                else:
                    actions.append(f"❌ Healing failed: {service} - {result.fix_applied}")
        
        except Exception as e:
            logger.error(f"Intelligent healing error: {e}")
            actions.append(f"Healing error: {e}")
        
        if verified > 0:
            insights.append(f"Verified {verified}/{attempts} healing attempts")
        
        return {
            "actions": actions,
            "insights": insights,
            "attempts": attempts,
            "verified": verified
        }
    
    async def _learn(self, issues: List[str], actions: List[str]) -> Dict[str, Any]:
        """
        LEARN (Level 10): Record to failure memory.
        
        The system now remembers every failure and what fixed it.
        """
        insights = []
        
        try:
            # Detect patterns every 10 cycles
            if self.cycle_count % 10 == 0:
                new_patterns = self.pattern_engine.detect_patterns(days=30)
                if new_patterns:
                    insights.append(f"Discovered {len(new_patterns)} new failure patterns")
            
            # Get learning effectiveness
            effectiveness = self.failure_memory.get_learning_effectiveness()
            learning_score = effectiveness.get("learning_score", 0)
            
            if learning_score < 0.5:
                insights.append(f"Learning needs improvement (score: {learning_score:.0%})")
        
        except Exception as e:
            logger.error(f"Learning phase error: {e}")
        
        return {"insights": insights}
    
    async def _predict(self) -> Dict[str, Any]:
        """
        PREDICT (Level 10): What might fail next?
        
        Uses pattern recognition to predict and prevent failures.
        """
        insights = []
        preventive_actions = []
        predictions = 0
        
        try:
            # Get current state for prediction
            now = datetime.now()
            current_state = {
                "hour": now.hour,
                "weekday": now.weekday(),
                "cycle_count": self.cycle_count
            }
            
            # Get predictions
            predicted = self.pattern_engine.predict_failures(current_state)
            predictions = len(predicted)
            
            for p in predicted[:3]:  # Top 3 predictions
                if p.confidence > 0.6:
                    insights.append(f"PREDICTION ({p.confidence:.0%}): {p.predicted_failure}")
                    preventive_actions.append(f"🔮 Preventive: {p.recommended_action}")
        
        except Exception as e:
            logger.error(f"Prediction phase error: {e}")
        
        return {
            "predictions": predictions,
            "preventive_actions": preventive_actions,
            "insights": insights
        }
    
    async def _meta_learn(self) -> Dict[str, Any]:
        """
        META-LEARN (Level 10): Are we getting smarter?
        
        Tracks how well the system is learning and makes adjustments.
        """
        insights = []
        intelligence_score = 0.0
        
        try:
            # Evaluate learning effectiveness
            metrics = self.meta_learner.evaluate()
            intelligence_score = metrics.overall_intelligence_score
            
            # Get recommendations
            recommendations = self.meta_learner.get_recommendations()
            
            if recommendations:
                high_priority = [r for r in recommendations if r.priority == "high"]
                if high_priority:
                    insights.append(f"Learning recommendation: {high_priority[0].recommendation}")
            
            # Optimize learning every 20 cycles
            if self.cycle_count % 20 == 0:
                self.meta_learner.optimize()
                insights.append("Ran meta-learning optimization")
            
            # Report intelligence score
            if intelligence_score >= 8:
                insights.append(f"Intelligence Level: EXCELLENT ({intelligence_score:.1f}/10)")
            elif intelligence_score >= 6:
                insights.append(f"Intelligence Level: GOOD ({intelligence_score:.1f}/10)")
            elif intelligence_score >= 4:
                insights.append(f"Intelligence Level: DEVELOPING ({intelligence_score:.1f}/10)")
            else:
                insights.append(f"Intelligence Level: NEEDS WORK ({intelligence_score:.1f}/10)")
        
        except Exception as e:
            logger.error(f"Meta-learning error: {e}")
        
        return {
            "intelligence_score": intelligence_score,
            "insights": insights
        }
    
    async def _evolve(self, issues: List[str]) -> Dict[str, Any]:
        """
        EVOLVE (Self-Evolution): Learn from issues and evolve proactively.
        
        Instead of just fixing issues, we:
        1. Analyze patterns across issues
        2. Match to known lessons (wisdom)
        3. Propose evolutions to prevent recurrence
        4. Apply safe evolutions automatically
        5. Queue risky evolutions for approval
        
        This is how Aria gets smarter over time WITHOUT human intervention.
        """
        insights = []
        evolutions_proposed = 0
        evolutions_applied = 0
        
        try:
            for issue in issues[:5]:  # Analyze top 5 issues
                # Analyze issue and potentially create evolution
                evolution = await on_issue_detected(issue, context={
                    "cycle": self.cycle_count,
                    "timestamp": datetime.now().isoformat()
                })
                
                if evolution:
                    evolutions_proposed += 1
                    
                    # Auto-apply if safe
                    if evolution.approval_status.value in ["auto_approved", "approved"]:
                        success, message = await self.evolution_engine.apply_evolution(evolution)
                        if success:
                            evolutions_applied += 1
                            insights.append(f"🧬 Evolved: {evolution.description[:50]}")
                        else:
                            insights.append(f"🧬 Evolution failed: {message[:30]}")
                    else:
                        # Queued for approval
                        insights.append(f"🧬 Evolution proposed (needs approval): {evolution.description[:50]}")
            
            # Run proactive evolution cycle every 6 consciousness cycles (~30 min)
            if self.cycle_count % 6 == 0:
                await self.evolution_engine.run_proactive_evolution_cycle()
                insights.append("Ran proactive evolution cycle")
            
            # Report evolution status
            status = self.evolution_engine.get_evolution_status()
            if evolutions_proposed > 0:
                insights.append(f"🧬 Evolution: {evolutions_applied}/{evolutions_proposed} applied, "
                              f"{status['lessons_count']} lessons learned")
        
        except Exception as e:
            logger.error(f"Evolution phase error: {e}")
        
        return {
            "evolutions_proposed": evolutions_proposed,
            "evolutions_applied": evolutions_applied,
            "insights": insights
        }
    
    async def _act(self, issues: List[str]) -> List[str]:
        """
        ACT: Take proactive action on issues.
        
        This is where TRUE INTELLIGENCE happens:
        - Don't just report problems
        - ACTUALLY FIX THEM
        - Only alert humans as last resort
        
        Returns list of actions taken.
        """
        actions = []
        
        # Import self-healer
        try:
            from .self_healer import get_self_healer, HealResult
            healer = get_self_healer()
        except ImportError:
            healer = None
            logger.warning("Self-healer not available")
        
        # Parse issues and attempt to heal each one
        for issue in issues:
            # Extract capability from issue string
            capability = None
            if "thinking" in issue.lower() or "claude" in issue.lower():
                capability = "thinking"
            elif "memory" in issue.lower() or "mem0" in issue.lower():
                capability = "memory_store"
            elif "telegram" in issue.lower():
                capability = "telegram"
            elif "trading" in issue.lower() or "whaletrack" in issue.lower():
                capability = "trading_data"
            elif "gemini" in issue.lower():
                capability = "quick_thinking"
            
            if capability and healer:
                # ATTEMPT AUTO-HEAL
                result = await healer.heal_capability(capability, issue)
                
                if result.auto_fixed:
                    actions.append(f"🩹 AUTO-FIXED: {capability} - {result.message}")
                    logger.info(f"Self-healed {capability}: {result.message}")
                elif result.result == HealResult.PARTIAL:
                    actions.append(f"⚠️ DEGRADED: {capability} - {result.message}")
                elif result.result == HealResult.FAILED:
                    actions.append(f"❌ NEEDS HUMAN: {capability} - {result.message}")
                    # Only alert for truly unfixable issues
                    if STEWARD_CHAT_ID:
                        try:
                            await self._alert_steward([issue])
                        except Exception:
                            pass
            else:
                # Unknown issue - log but don't panic
                actions.append(f"📝 Logged: {issue[:50]}")
        
        # Update self-model with any persistent issues
        if any("memory" in i.lower() for i in issues):
            self.self_model.add_pattern(
                "Memory system unstable",
                "limitation",
                "Detected in consciousness cycle"
            )
        
        # Elevate to proactive level if taking actions
        if actions:
            self.level = ConsciousnessLevel.PROACTIVE
        
        return actions
    
    async def _update(
        self,
        state: Dict,
        issues: List[str],
        actions: List[str]
    ) -> List[str]:
        """
        UPDATE: Log to memory and learn.
        
        Returns new insights gained.
        """
        insights = []
        
        # Store significant findings in memory
        if issues or actions:
            try:
                from memory import store_memory
                
                summary = f"Consciousness cycle: {len(issues)} issues, {len(actions)} actions. Health: {state.get('health_score', 0):.0f}%"
                
                if issues:
                    summary += f"\nIssues: {'; '.join(issues[:3])}"
                
                await store_memory(
                    content=summary,
                    category="pattern",
                    importance="medium" if issues else "low"
                )
                
                insights.append("Logged cycle findings to memory")
            except Exception as e:
                logger.warning(f"Could not store consciousness findings: {e}")
        
        # Pattern detection
        if len(issues) == 0 and self.cycle_count > 5:
            insights.append("System stable for multiple cycles")
            self.self_model.add_pattern(
                "Stable operation",
                "strength",
                f"No issues for {self.cycle_count} cycles"
            )
        
        # If consistently having same issue, note it
        if issues:
            self.issues_history.append({
                "timestamp": datetime.now().isoformat(),
                "issues": issues
            })
            self.issues_history = self.issues_history[-20:]  # Keep last 20
            
            # Check for recurring issues
            all_issues = [i for h in self.issues_history for i in h.get("issues", [])]
            for issue in set(issues):
                if all_issues.count(issue) >= 3:
                    insights.append(f"Recurring issue: {issue}")
                    self.self_model.add_pattern(
                        f"Recurring: {issue[:50]}",
                        "weakness",
                        f"Occurred {all_issues.count(issue)} times recently"
                    )
        
        return insights
    
    async def _alert_steward(self, issues: List[str]):
        """Send alert to steward about critical issues."""
        import httpx
        
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token or not STEWARD_CHAT_ID:
            return
        
        message = "🧠 **Consciousness Alert**\n\n"
        message += "Critical issues detected:\n"
        for issue in issues[:5]:
            message += f"• {issue}\n"
        
        message += f"\nHealth: {self.self_model.get_state().get_health_score():.0f}%"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": int(STEWARD_CHAT_ID), "text": message, "parse_mode": "Markdown"}
                )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    # ==================== PUBLIC API ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current consciousness status with Level 10 Intelligence metrics."""
        status = {
            "running": self.running,
            "level": self.level.value,
            "cycle_count": self.cycle_count,
            "last_cycle": self.last_cycle.to_dict() if self.last_cycle else None,
            "health_score": self.self_model.get_state().get_health_score(),
            "intelligence": {
                "available": INTELLIGENCE_AVAILABLE,
                "score": self.last_cycle.intelligence_score if self.last_cycle else 0,
                "components": {
                    "verifier": self.verifier is not None,
                    "config_contract": self.config_contract is not None,
                    "root_cause_analyzer": self.root_cause_analyzer is not None,
                    "failure_memory": self.failure_memory is not None,
                    "intelligent_healer": self.intelligent_healer is not None,
                    "pattern_engine": self.pattern_engine is not None,
                    "meta_learner": self.meta_learner is not None
                }
            }
        }
        
        # Add intelligence summary if available
        if self.meta_learner:
            try:
                summary = self.meta_learner.get_summary()
                status["intelligence"]["summary"] = summary
            except Exception:
                pass
        
        return status
    
    async def run_manual_cycle(self) -> ConsciousnessCycleResult:
        """Run a consciousness cycle manually."""
        return await self._run_cycle()
    
    def get_intelligence_report(self) -> Dict[str, Any]:
        """Get detailed intelligence report."""
        report = {
            "level_10_intelligence": INTELLIGENCE_AVAILABLE,
            "components": {}
        }
        
        if self.verifier:
            report["components"]["verification"] = self.verifier.get_summary()
        
        if self.failure_memory:
            report["components"]["memory"] = self.failure_memory.get_failure_stats()
        
        if self.pattern_engine:
            report["components"]["patterns"] = self.pattern_engine.get_pattern_stats()
        
        if self.intelligent_healer:
            report["components"]["healing"] = self.intelligent_healer.get_healing_summary()
        
        if self.meta_learner:
            report["components"]["meta_learning"] = self.meta_learner.get_summary()
        
        return report


# ============================================================================
# SINGLETON AND CONVENIENCE
# ============================================================================

_loop: Optional[ConsciousnessLoop] = None


def get_consciousness_loop() -> ConsciousnessLoop:
    """Get or create consciousness loop instance."""
    global _loop
    if _loop is None:
        _loop = ConsciousnessLoop()
    return _loop


async def start_consciousness_daemon():
    """Start the consciousness daemon (for scheduler integration)."""
    loop = get_consciousness_loop()
    await loop.start()

