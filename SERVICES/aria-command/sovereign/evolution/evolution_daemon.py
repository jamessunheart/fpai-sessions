#!/usr/bin/env python3
"""
ARIA EVOLUTION DAEMON v2.0
===========================

UPGRADED: Three-Tier Dynamic Learning Architecture

TIER 1: IMMEDIATE (< 100ms per interaction)
- RealtimeLearner: Corrections, success reinforcement
- ResponseCache: Instant cached responses
- MetricsWindow: Rolling metrics

TIER 2: TRIGGERED (1-5 min)
- TriggerEngine: Event-driven evolution
- ErrorSpikeHandler: Auto-fix spikes

TIER 3: SCHEDULED (Adaptive)
- AdaptiveScheduler: Learns user patterns
- PatternSynthesizer: Deep analysis
- PromptEvolver: System prompt optimization

The daemon orchestrates ALL tiers for optimal learning.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# Tier 1: Immediate Learning
from .realtime_learner import get_realtime_learner, process_interaction as realtime_learn
from .correction_handler import get_correction_handler, detect_and_learn, enhance_query
from .response_cache import get_response_cache, check_cache, cache_response, invalidate_cache
from .metrics_window import get_metrics_window, record_interaction as record_metrics, get_metrics_summary

# Tier 2: Triggered Evolution
from .trigger_engine import get_trigger_engine, report_interaction as report_to_triggers
from .error_spike_handler import get_error_spike_handler, record_error, check_and_fix_spike

# Tier 3: Scheduled Analysis
from .adaptive_scheduler import get_adaptive_scheduler, record_user_activity, TaskType

# Legacy components (still used)
from .interaction_logger import get_interaction_logger, log_interaction, get_evolution_data
from .success_detector import get_success_detector, analyze_successes
from .synthesizer import get_synthesizer, analyze_and_propose, ImprovementProposal
from .prompt_evolver import get_prompt_evolver, evolve_from_patterns
from .capability_evolver import get_capability_evolver, record_capability_request
from .proactive_evolver import get_proactive_evolver, learn_proactive_pattern
from .efficiency_evolver import get_efficiency_evolver, record_efficiency_metrics
from .safe_applicator import get_safe_applicator, apply_proposal

# Pattern detection and notifications
from .pattern_detectors import (
    get_pattern_manager, 
    detect_patterns, 
    detect_patterns_single,
    save_patterns,
    DetectedPattern
)
from .notifications import (
    notifier,
    notify_patterns_detected,
    notify_proposal_created,
    notify_change_applied
)

logger = logging.getLogger("aria.evolution.daemon")

# ============================================================================
# CONFIGURATION
# ============================================================================

EVOLUTION_ENABLED = os.getenv("ARIA_EVOLUTION_ENABLED", "true").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")

# Schedule (24h format)
ANALYSIS_HOUR = 6
DESIGN_HOUR = 6
APPLY_HOUR = 7
DIGEST_HOUR = 8


@dataclass
class EvolutionCycleResult:
    """Result of an evolution cycle."""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Analysis
    interactions_analyzed: int = 0
    patterns_detected: int = 0
    
    # Proposals
    proposals_generated: int = 0
    proposals_auto_approved: int = 0
    proposals_pending: int = 0
    
    # Changes
    changes_applied: int = 0
    changes_failed: int = 0
    changes_rolled_back: int = 0
    
    # Costs
    analysis_cost_usd: float = 0.0


# ============================================================================
# EVOLUTION DAEMON
# ============================================================================

class EvolutionDaemon:
    """
    Main evolution orchestrator v2.0.
    
    Coordinates THREE TIERS of learning:
    - Tier 1: Immediate (per-interaction)
    - Tier 2: Triggered (event-driven)
    - Tier 3: Scheduled (daily analysis)
    """
    
    def __init__(self):
        # Tier 1: Immediate Learning
        self.realtime_learner = get_realtime_learner()
        self.correction_handler = get_correction_handler()
        self.response_cache = get_response_cache()
        self.metrics_window = get_metrics_window()
        
        # Tier 2: Triggered Evolution
        self.trigger_engine = get_trigger_engine()
        self.error_spike_handler = get_error_spike_handler()
        
        # Tier 3: Scheduled Analysis
        self.adaptive_scheduler = get_adaptive_scheduler()
        
        # Legacy components
        self.interaction_logger = get_interaction_logger()
        self.success_detector = get_success_detector()
        self.synthesizer = get_synthesizer()
        self.prompt_evolver = get_prompt_evolver()
        self.capability_evolver = get_capability_evolver()
        self.proactive_evolver = get_proactive_evolver()
        self.efficiency_evolver = get_efficiency_evolver()
        self.safe_applicator = get_safe_applicator()
        
        # Register scheduler task handlers
        self._register_scheduler_handlers()
        
        self._running = False
        self._last_cycle: Optional[EvolutionCycleResult] = None
        
        # Interaction-triggered analysis
        self._interaction_count_since_analysis = 0
        self._analysis_trigger_threshold = 10  # Trigger analysis every N interactions
        self._last_triggered_analysis: Optional[datetime] = None
        self._triggered_analysis_cooldown = timedelta(minutes=30)  # Min time between triggered analyses
    
    def _register_scheduler_handlers(self):
        """Register handlers for scheduled tasks."""
        self.adaptive_scheduler.register_handler(
            TaskType.ANALYSIS,
            self._run_analysis
        )
        self.adaptive_scheduler.register_handler(
            TaskType.DIGEST,
            self._send_digest
        )
        self.adaptive_scheduler.register_handler(
            TaskType.CLEANUP,
            self._run_cleanup
        )
        self.adaptive_scheduler.register_handler(
            TaskType.METRICS_AGGREGATE,
            self._aggregate_metrics
        )
        self.adaptive_scheduler.register_handler(
            TaskType.CACHE_WARMUP,
            self._warmup_cache
        )
        self.adaptive_scheduler.register_handler(
            TaskType.HEALTH_CHECK,
            self._health_check
        )
    
    async def run(self):
        """
        Main daemon loop v2.0.
        
        Now orchestrates three tiers:
        - Tier 2 trigger engine runs in parallel
        - Tier 3 adaptive scheduler handles timing
        """
        if not EVOLUTION_ENABLED:
            logger.info("Evolution daemon disabled")
            return
        
        logger.info("Evolution daemon v2.0 starting (three-tier architecture)...")
        self._running = True
        
        # Start background tasks
        trigger_task = asyncio.create_task(self._run_trigger_engine())
        scheduler_task = asyncio.create_task(self._run_scheduler())
        
        try:
            while self._running:
                try:
                    # Check for error spikes (Tier 2)
                    spike = await check_and_fix_spike()
                    if spike:
                        logger.warning(f"Error spike handled: {spike.fix_result}")
                    
                    # Clean up expired caches periodically
                    if datetime.now().minute == 0:
                        self.response_cache.cleanup_expired()
                        self.metrics_window.aggregate_hourly()
                    
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Evolution daemon error: {e}")
                    await asyncio.sleep(60)
                    
        finally:
            # Cancel background tasks
            trigger_task.cancel()
            scheduler_task.cancel()
            try:
                await trigger_task
            except asyncio.CancelledError:
                pass
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
    
    async def _run_trigger_engine(self):
        """Run Tier 2 trigger engine."""
        try:
            await self.trigger_engine.run()
        except asyncio.CancelledError:
            self.trigger_engine.stop()
    
    async def _run_scheduler(self):
        """Run Tier 3 adaptive scheduler."""
        try:
            await self.adaptive_scheduler.run()
        except asyncio.CancelledError:
            self.adaptive_scheduler.stop()
    
    def stop(self):
        """Stop the daemon."""
        self._running = False
        logger.info("Evolution daemon stopping...")
    
    async def _run_analysis(self):
        """Run the analysis phase."""
        logger.info("Starting evolution analysis phase...")
        
        result = EvolutionCycleResult()
        
        try:
            # Get interaction data
            data = get_evolution_data(24)
            result.interactions_analyzed = data["summary"].get("total_interactions", 0)
            
            # Analyze success patterns
            patterns = self.success_detector.analyze_successes(24)
            result.patterns_detected = len(patterns)
            
            logger.info(f"Analysis: {result.interactions_analyzed} interactions, {result.patterns_detected} patterns")
            
        except Exception as e:
            logger.error(f"Analysis phase error: {e}")
        
        self._last_cycle = result
    
    async def _run_design(self):
        """Run the design phase - generate improvement proposals."""
        logger.info("Starting evolution design phase...")
        
        if not self._last_cycle:
            self._last_cycle = EvolutionCycleResult()
        
        try:
            # Generate AI-powered proposals
            proposals = await analyze_and_propose(24)
            self._last_cycle.proposals_generated = len(proposals)
            
            # Count auto-approved (high confidence, low risk)
            auto_approved = [p for p in proposals if p.confidence >= 0.9 and p.risk_level == "low"]
            self._last_cycle.proposals_auto_approved = len(auto_approved)
            self._last_cycle.proposals_pending = len(proposals) - len(auto_approved)
            
            # Also try pattern-based prompt evolution
            prompt_version = await evolve_from_patterns()
            if prompt_version:
                logger.info(f"Evolved prompt to version {prompt_version.version}")
            
            logger.info(f"Design: {len(proposals)} proposals ({len(auto_approved)} auto-approved)")
            
        except Exception as e:
            logger.error(f"Design phase error: {e}")
    
    async def _run_apply(self):
        """Run the apply phase - apply safe changes."""
        logger.info("Starting evolution apply phase...")
        
        if not self._last_cycle:
            self._last_cycle = EvolutionCycleResult()
        
        try:
            # Get high-confidence proposals
            proposals = self.synthesizer.get_high_confidence_proposals(0.9)
            
            for proposal in proposals[:5]:  # Limit to 5 per cycle
                success, msg = await apply_proposal(proposal)
                
                if success:
                    self._last_cycle.changes_applied += 1
                    self.synthesizer.mark_proposal(proposal.id, "applied", "success")
                else:
                    if "rolled back" in msg.lower():
                        self._last_cycle.changes_rolled_back += 1
                    else:
                        self._last_cycle.changes_failed += 1
                    self.synthesizer.mark_proposal(proposal.id, "failed", msg)
            
            logger.info(f"Apply: {self._last_cycle.changes_applied} applied, {self._last_cycle.changes_failed} failed")
            
        except Exception as e:
            logger.error(f"Apply phase error: {e}")
    
    async def _send_digest(self):
        """Send evolution digest to James."""
        if not TELEGRAM_BOT_TOKEN or not SUNHEART_CHAT_ID:
            logger.warning("Cannot send digest: missing Telegram config")
            return
        
        try:
            digest = await self._generate_digest()
            await self._send_telegram(digest)
            logger.info("Evolution digest sent")
            
        except Exception as e:
            logger.error(f"Send digest error: {e}")
    
    async def _generate_digest(self) -> str:
        """Generate the daily evolution digest."""
        if not self._last_cycle:
            return "📊 **Aria Evolution Digest**\n\nNo evolution cycle ran today."
        
        cycle = self._last_cycle
        
        # Get stats
        efficiency = self.efficiency_evolver.get_efficiency_stats(1)
        proactive = self.proactive_evolver.get_patterns_summary()
        changes = self.safe_applicator.get_change_stats()
        
        digest = f"""📊 **Aria Evolution Digest**
_{datetime.now().strftime("%B %d, %Y")}_

**📈 Analysis**
• Interactions analyzed: {cycle.interactions_analyzed}
• Patterns detected: {cycle.patterns_detected}

**💡 Improvements**
• Proposals generated: {cycle.proposals_generated}
• Auto-approved: {cycle.proposals_auto_approved}
• Pending review: {cycle.proposals_pending}

**🔧 Changes Applied**
• Successfully applied: {cycle.changes_applied}
• Failed: {cycle.changes_failed}
• Rolled back: {cycle.changes_rolled_back}

**⚡ Efficiency**
• Cache hits: {efficiency.get('cache_hits', 0)}
• Cost saved: ${efficiency.get('cost_saved_by_cache', 0):.4f}
• Total cost (24h): ${efficiency.get('total_cost', 0):.4f}

**🎯 Proactivity**
• Active patterns: {sum(p['count'] for p in proactive.get('by_trigger_type', {}).values())}
• Success rate: {proactive.get('total_success_rate', 0)*100:.0f}%

**📝 Next Steps**
"""
        # Add pending proposals
        pending = self.synthesizer.get_pending_proposals()[:3]
        if pending:
            for p in pending:
                digest += f"• [{p.category}] {p.problem[:50]}... (conf: {p.confidence:.0%})\n"
        else:
            digest += "• No pending proposals - system is optimized! ✨\n"
        
        digest += "\n_Use /evolution status for details_"
        
        return digest
    
    async def _send_telegram(self, message: str):
        """Send message to Telegram."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": SUNHEART_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
    
    # ========================================================================
    # PUBLIC METHODS FOR INTEGRATION
    # ========================================================================
    
    async def on_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        model: str,
        tools: List[str],
        time_ms: float,
        tokens: int,
        cost: float,
        success: bool,
        was_cached: bool = False,
        was_correction: bool = False
    ):
        """
        Called for every interaction - triggers THREE TIERS of learning.
        
        This is the main integration point with the Aria brain.
        
        TIER 1: Immediate (< 100ms)
        - Realtime learner processes corrections
        - Response cache updated
        - Rolling metrics updated
        
        TIER 2: Triggered (feeds detectors)
        - Error spike detection
        - Correction pattern detection
        - Performance monitoring
        
        TIER 3: Scheduled (logs for later)
        - Full interaction logged
        - User activity recorded
        """
        
        # ====================================================================
        # TIER 1: IMMEDIATE LEARNING (< 100ms)
        # ====================================================================
        
        # Process through realtime learner
        insights = self.realtime_learner.process_interaction(
            user_id=user_id,
            user_message=message,
            aria_response=response,
            response_time_ms=time_ms,
            tools_used=tools,
            success=success
        )
        
        # If correction detected, learn immediately
        if insights.get("correction_detected"):
            # Invalidate any cached response for the original query
            invalidate_cache(message, reason="correction")
            logger.info(f"Tier 1: Learned from correction: {insights.get('correction_applied')}")
        
        # If successful, cache the response
        if success and not was_cached and len(response) < 5000:
            cache_response(
                query=message,
                response=response,
                tools_used=tools,
                response_time_ms=time_ms,
                cost_usd=cost,
                user_id=user_id
            )
        
        # Update rolling metrics
        record_metrics(
            success=success,
            response_time_ms=time_ms,
            was_correction=was_correction,
            was_cached=was_cached,
            cost_usd=cost,
            tokens=tokens,
            tools_used=len(tools)
        )
        
        # ====================================================================
        # TIER 2: TRIGGER ENGINE (feeds detectors)
        # ====================================================================
        
        # Report to trigger engine
        report_to_triggers(
            user_id=user_id,
            success=success,
            response_time_ms=time_ms,
            was_correction=was_correction,
            correction_type=insights.get("correction_applied", {}).get("learned") if insights.get("correction_detected") else None,
            tools_used=tools
        )
        
        # If error, report for spike detection
        if not success:
            record_error(
                error_message=f"Interaction failed for user {user_id}",
                user_id=user_id,
                context={"message": message[:100], "model": model}
            )
        
        # ====================================================================
        # TIER 3: SCHEDULED ANALYSIS (log for later)
        # ====================================================================
        
        # Log full interaction for daily analysis
        log_interaction(
            user_id=user_id,
            user_message=message,
            response=response,
            model_used=model,
            tools_called=tools,
            total_time_ms=time_ms,
            tokens_used=tokens,
            cost_usd=cost,
            success=success
        )
        
        # Record user activity for adaptive scheduling
        record_user_activity(user_id, "chat")
        
        # Record efficiency metrics
        record_efficiency_metrics(
            model=model,
            intent="general",
            time_ms=time_ms,
            tokens=tokens,
            cost=cost
        )
        
        # Learn proactive patterns
        learn_proactive_pattern(
            user_id=user_id,
            intent="general",
            message=message,
            tools=tools
        )
        
        # Record capability requests
        record_capability_request(user_id, message)
        
        # ====================================================================
        # PATTERN DETECTION & TRIGGERED ANALYSIS
        # ====================================================================
        
        # Increment interaction counter
        self._interaction_count_since_analysis += 1
        
        # Run single-interaction pattern detection
        interaction_data = {
            "user_message": message,
            "response": response,
            "tool_count": len(tools),
            "total_time_ms": time_ms,
            "id": 0  # Will be set by logger
        }
        
        single_patterns = detect_patterns_single(interaction_data)
        high_severity_single = [p for p in single_patterns if p.severity == "high"]
        
        # Check if we should trigger full analysis
        should_trigger = False
        trigger_reason = ""
        
        # Trigger 1: Interaction count threshold
        if self._interaction_count_since_analysis >= self._analysis_trigger_threshold:
            should_trigger = True
            trigger_reason = f"Reached {self._analysis_trigger_threshold} interactions"
        
        # Trigger 2: High severity pattern detected in this interaction
        if high_severity_single:
            should_trigger = True
            trigger_reason = f"High severity pattern: {high_severity_single[0].detector}"
        
        # Check cooldown
        if should_trigger:
            now = datetime.now()
            if self._last_triggered_analysis:
                time_since_last = now - self._last_triggered_analysis
                if time_since_last < self._triggered_analysis_cooldown:
                    logger.debug(f"Analysis trigger skipped - cooldown ({time_since_last.seconds}s since last)")
                    should_trigger = False
        
        # Run triggered analysis in background
        if should_trigger:
            self._interaction_count_since_analysis = 0
            self._last_triggered_analysis = datetime.now()
            asyncio.create_task(self._run_triggered_analysis(trigger_reason))
        
        return insights
    
    async def _run_triggered_analysis(self, reason: str):
        """Run triggered analysis (non-blocking, in background)."""
        try:
            logger.info(f"Triggered analysis starting: {reason}")
            
            # Detect patterns from last 6 hours
            patterns = detect_patterns(6)
            save_patterns(patterns)
            
            high_severity = [p for p in patterns if p.severity == "high"]
            
            if high_severity:
                # Notify about high severity patterns
                await notify_patterns_detected([p.to_dict() for p in high_severity])
                logger.info(f"Notified about {len(high_severity)} high severity patterns")
                
                # Run synthesis to generate proposals
                try:
                    proposals = await analyze_and_propose(6)
                    
                    if proposals:
                        # Notify about proposals (medium+ impact)
                        for proposal in proposals:
                            if proposal.expected_impact in ['medium', 'high']:
                                await notify_proposal_created({
                                    'id': proposal.id,
                                    'category': proposal.category,
                                    'problem': proposal.problem,
                                    'solution': proposal.solution,
                                    'confidence': proposal.confidence,
                                    'expected_impact': proposal.expected_impact,
                                    'risk_level': proposal.risk_level
                                })
                        
                        logger.info(f"Generated {len(proposals)} improvement proposals")
                        
                except Exception as e:
                    logger.error(f"Synthesis failed in triggered analysis: {e}")
            
            logger.info(f"Triggered analysis complete: {len(patterns)} patterns, {len(high_severity)} high severity")
            
        except Exception as e:
            logger.error(f"Triggered analysis failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get evolution daemon status v2.0."""
        # Get tier-specific stats
        metrics_summary = get_metrics_summary()
        cache_stats = self.response_cache.get_stats(1)
        trigger_status = self.trigger_engine.get_status()
        scheduler_status = self.adaptive_scheduler.get_status()
        
        return {
            "enabled": EVOLUTION_ENABLED,
            "running": self._running,
            "version": "2.0 (three-tier)",
            "last_cycle": {
                "timestamp": self._last_cycle.timestamp.isoformat() if self._last_cycle else None,
                "interactions": self._last_cycle.interactions_analyzed if self._last_cycle else 0,
                "changes_applied": self._last_cycle.changes_applied if self._last_cycle else 0
            },
            "tier_1_immediate": {
                "realtime_learner": self.realtime_learner.get_learning_summary(),
                "response_cache": {
                    "hit_rate": cache_stats.get("hit_rate", 0),
                    "entries": cache_stats.get("valid_entries", 0),
                    "cost_saved": cache_stats.get("total_cost_saved_usd", 0)
                },
                "metrics": {
                    "health_score": metrics_summary.get("overall_health", {}).get("score", 0),
                    "error_rate": metrics_summary.get("metrics", {}).get("error_rate", {}).get("value", 0),
                    "success_rate": metrics_summary.get("metrics", {}).get("success_rate", {}).get("value", 0)
                }
            },
            "tier_2_triggered": {
                "trigger_engine": trigger_status,
                "error_spikes": self.error_spike_handler.get_error_stats(24)
            },
            "tier_3_scheduled": {
                "scheduler": scheduler_status,
                "user_active": scheduler_status.get("user_active", False),
                "quiet_period_min": scheduler_status.get("quiet_period_minutes", 0)
            },
            "legacy_components": {
                "interaction_logger": "active",
                "success_detector": "active",
                "synthesizer": "active",
                "prompt_evolver": "active",
                "capability_evolver": "active",
                "proactive_evolver": "active",
                "efficiency_evolver": "active",
                "safe_applicator": "active"
            }
        }
    
    # ========================================================================
    # SCHEDULER TASK HANDLERS
    # ========================================================================
    
    async def _run_cleanup(self) -> Dict[str, Any]:
        """Clean up old data and caches."""
        results = {
            "cache_expired": self.response_cache.cleanup_expired(),
            "metrics_cleaned": 0
        }
        
        # Clean old metric points
        self.metrics_window.cleanup_old_points(7)
        
        logger.info(f"Cleanup completed: {results}")
        return results
    
    async def _aggregate_metrics(self) -> Dict[str, Any]:
        """Aggregate hourly metrics."""
        self.metrics_window.aggregate_hourly()
        return {"status": "aggregated"}
    
    async def _warmup_cache(self) -> Dict[str, Any]:
        """Pre-warm caches based on user patterns."""
        # Get user patterns to identify likely queries
        pattern = self.adaptive_scheduler.get_pattern()
        
        if not pattern:
            return {"status": "no_pattern"}
        
        # Would load common queries based on pattern
        # For now, just ensure cache is loaded
        return {
            "status": "warmed",
            "cache_size": len(self.response_cache._memory_cache)
        }
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        summary = get_metrics_summary()
        health = summary.get("overall_health", {})
        
        if health.get("score", 1) < 0.5:
            logger.warning(f"Health check: DEGRADED ({health.get('score', 0):.2f})")
        
        return {
            "score": health.get("score", 0),
            "status": health.get("status", "unknown"),
            "alerts": summary.get("active_alerts", [])
        }
    
    async def run_manual_cycle(self) -> EvolutionCycleResult:
        """Run a manual evolution cycle (for testing)."""
        logger.info("Running manual evolution cycle...")
        
        await self._run_analysis()
        await self._run_design()
        await self._run_apply()
        
        return self._last_cycle


# ============================================================================
# SINGLETON
# ============================================================================

_daemon: Optional[EvolutionDaemon] = None


def get_evolution_daemon() -> EvolutionDaemon:
    """Get or create global evolution daemon."""
    global _daemon
    if _daemon is None:
        _daemon = EvolutionDaemon()
    return _daemon


async def start_evolution_daemon():
    """Start the evolution daemon."""
    daemon = get_evolution_daemon()
    await daemon.run()


def stop_evolution_daemon():
    """Stop the evolution daemon."""
    if _daemon:
        _daemon.stop()


async def on_aria_interaction(
    user_id: str,
    message: str,
    response: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Hook for Aria to report interactions.
    
    Returns insights from immediate learning.
    """
    daemon = get_evolution_daemon()
    return await daemon.on_interaction(
        user_id=user_id,
        message=message,
        response=response,
        model=kwargs.get("model", "unknown"),
        tools=kwargs.get("tools", []),
        time_ms=kwargs.get("time_ms", 0),
        tokens=kwargs.get("tokens", 0),
        cost=kwargs.get("cost", 0),
        success=kwargs.get("success", True),
        was_cached=kwargs.get("was_cached", False),
        was_correction=kwargs.get("was_correction", False)
    )


# ============================================================================
# CONVENIENCE FUNCTIONS FOR TIER 1 (PRE-PROCESSING)
# ============================================================================

def check_query_cache(query: str) -> Optional[Dict[str, Any]]:
    """
    Check if we have a cached response for this query.
    
    Call BEFORE processing a query for instant response.
    """
    cached = check_cache(query)
    if cached:
        return {
            "cached": True,
            "response": cached.response,
            "tools_used": cached.tools_used,
            "hit_count": cached.total_uses
        }
    return None


def get_query_enhancements(query: str) -> Dict[str, Any]:
    """
    Get any learned enhancements for a query.
    
    Call BEFORE processing to:
    - Check for learned corrections
    - Get interpretation hints
    """
    handler = get_correction_handler()
    return handler.enhance_query(query)

