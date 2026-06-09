#!/usr/bin/env python3
"""
ARIA REFLECTION DAEMON
======================

Main orchestration loop for the AI-to-AI reflection system:
1. Monitors triggers (scheduled, threshold, patterns, manual)
2. Runs summarization → dialogue → spec → build pipeline
3. Reports results
4. Manages costs

Run as: python -m sovereign.reflection.daemon
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional
import uuid

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sovereign.reflection.trigger import (
    ReflectionTrigger, TriggerEvent, TriggerType,
    get_trigger, increment_interactions
)
from sovereign.reflection.summarizer import (
    InteractionSummarizer, InteractionSummary, get_summarizer
)
from sovereign.reflection.dialogue import (
    DialogueEngine, DialogueResult, get_dialogue_engine
)
from sovereign.reflection.spec_generator import (
    SpecGenerator, GeneratedSpec, get_spec_generator
)
from sovereign.reflection.builder_bridge import (
    BuilderBridge, BuildJob, get_builder_bridge
)
from sovereign.reflection.cost_tracker import (
    ReflectionCostTracker, CycleCost, get_cost_tracker
)
from sovereign.reflection.reporter import (
    ReflectionReporter, get_reporter, report_cycle
)

logger = logging.getLogger("aria.reflection.daemon")

# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_LEVEL = os.getenv("REFLECTION_LOG_LEVEL", "INFO")
CHECK_INTERVAL = int(os.getenv("REFLECTION_CHECK_INTERVAL", "60"))  # seconds


# ============================================================================
# REFLECTION DAEMON
# ============================================================================

class ReflectionDaemon:
    """
    Main daemon that orchestrates the reflection system.
    
    Flow:
    1. Trigger fires (scheduled, threshold, pattern, manual)
    2. Summarize recent interactions
    3. Run AI-to-AI dialogue
    4. Generate specs from proposals
    5. Queue specs to builder
    6. Report results
    """
    
    def __init__(self):
        self.trigger = get_trigger()
        self.summarizer = get_summarizer()
        self.dialogue_engine = get_dialogue_engine()
        self.spec_generator = get_spec_generator()
        self.builder_bridge = get_builder_bridge()
        self.cost_tracker = get_cost_tracker()
        self.reporter = get_reporter()
        
        self._running = False
        self._current_cycle_id: Optional[str] = None
    
    async def start(self):
        """Start the reflection daemon."""
        logger.info("🔄 Reflection daemon starting...")
        self._running = True
        
        # Register trigger callback
        self.trigger.register_callback(self._on_trigger)
        
        # Start trigger monitor
        asyncio.create_task(self.trigger.start())
        
        # Main loop
        while self._running:
            try:
                # Process any completed builds
                await self._check_builds()
                
                # Check for digest times
                await self._check_digests()
                
            except Exception as e:
                logger.error(f"Daemon loop error: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)
        
        logger.info("Reflection daemon stopped")
    
    def stop(self):
        """Stop the daemon."""
        logger.info("Stopping reflection daemon...")
        self._running = False
        self.trigger.stop()
    
    # ========================================================================
    # TRIGGER HANDLING
    # ========================================================================
    
    def _on_trigger(self, event: TriggerEvent):
        """Called when a trigger fires."""
        logger.info(f"Trigger fired: {event.trigger_type.value}")
        
        # Run cycle in background
        asyncio.create_task(self.run_cycle(event))
    
    async def run_cycle(self, event: TriggerEvent = None) -> Optional[str]:
        """
        Run a complete reflection cycle.
        
        Returns cycle_id if successful.
        """
        cycle_id = f"cycle-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self._current_cycle_id = cycle_id
        
        logger.info(f"=== Starting reflection cycle: {cycle_id} ===")
        
        # Start cost tracking
        cost = self.cost_tracker.start_cycle(cycle_id)
        
        try:
            # Determine hours to review based on trigger type
            hours = 24  # Default
            if event:
                if event.trigger_type == TriggerType.SCHEDULED_WEEKLY:
                    hours = 168  # 7 days
                elif event.trigger_type == TriggerType.THRESHOLD:
                    hours = 12
                elif event.trigger_type == TriggerType.PATTERN:
                    hours = 6
            
            # Step 1: Summarize
            logger.info(f"Step 1: Summarizing last {hours} hours...")
            summary = await self.summarizer.summarize(hours)
            self.cost_tracker.record_summarizer_cost(summary.summarization_cost)
            
            if summary.interaction_count == 0:
                logger.info("No interactions to analyze, skipping cycle")
                self.cost_tracker.end_cycle()
                return None
            
            # Step 2: Dialogue
            logger.info("Step 2: Running AI dialogue...")
            dialogue = await self.dialogue_engine.run_dialogue(summary)
            self.cost_tracker.record_dialogue_cost(dialogue.total_cost)
            self.cost_tracker.record_outcomes(proposals=len(dialogue.proposals))
            
            if not dialogue.proposals:
                logger.info("No proposals from dialogue, cycle complete")
                cost = self.cost_tracker.end_cycle()
                await report_cycle(cycle_id, summary, dialogue, [], [], cost)
                return cycle_id
            
            # Step 3: Generate specs
            logger.info(f"Step 3: Generating specs for {len(dialogue.proposals)} proposals...")
            specs = await self.spec_generator.generate_all_specs(dialogue, summary)
            
            total_spec_cost = sum(s.generation_cost for s in specs)
            self.cost_tracker.record_spec_cost(total_spec_cost)
            self.cost_tracker.record_outcomes(specs=len(specs))
            
            # Step 4: Queue to builder
            logger.info(f"Step 4: Queueing {len(specs)} specs to builder...")
            builds = self.builder_bridge.queue_specs(specs, cycle_id)
            
            # Count needing approval
            needs_approval = [b for b in builds if b.status == "needs_approval"]
            if needs_approval:
                logger.info(f"{len(needs_approval)} specs need approval")
                await self.reporter.report_approval_needed(needs_approval)
            
            # Step 5: Process auto-approved builds
            auto_approved = [b for b in builds if b.status == "queued"]
            if auto_approved:
                logger.info(f"Processing {len(auto_approved)} auto-approved builds...")
                completed = await self.builder_bridge.process_queue()
                
                ok = sum(1 for b in completed if b.status == "completed")
                fail = sum(1 for b in completed if b.status in ["failed", "rolled_back"])
                
                self.cost_tracker.record_outcomes(builds_completed=ok, builds_failed=fail)
            
            # Finalize
            cost = self.cost_tracker.end_cycle()
            
            # Step 6: Report
            logger.info("Step 6: Reporting results...")
            await report_cycle(cycle_id, summary, dialogue, specs, builds, cost)
            
            logger.info(f"=== Cycle {cycle_id} complete: ${cost.total_cost:.4f} ===")
            
            return cycle_id
            
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            import traceback
            traceback.print_exc()
            
            # End cost tracking
            cost = self.cost_tracker.end_cycle()
            
            # Send error notification
            await self.reporter.send_telegram(
                f"❌ *Reflection Cycle Failed*\n\nCycle: {cycle_id}\nError: {str(e)[:200]}"
            )
            
            return None
        
        finally:
            self._current_cycle_id = None
    
    async def run_manual_cycle(self, reason: str = "Manual trigger") -> Optional[str]:
        """Run a manual reflection cycle."""
        event = self.trigger.trigger_manual(reason)
        return await self.run_cycle(event)
    
    # ========================================================================
    # BUILD PROCESSING
    # ========================================================================
    
    async def _check_builds(self):
        """Check and process pending builds."""
        try:
            queue_status = self.builder_bridge.get_queue_status()
            status_counts = queue_status.get("status_counts", {})
            
            if status_counts.get("queued", 0) > 0:
                logger.debug("Processing queued builds...")
                completed = await self.builder_bridge.process_queue()
                
                for build in completed:
                    success = build.status == "completed"
                    await self.reporter.report_build_complete(build, success)
                    
        except Exception as e:
            logger.error(f"Build check error: {e}")
    
    # ========================================================================
    # DIGEST SCHEDULING
    # ========================================================================
    
    async def _check_digests(self):
        """Check if digest should be sent."""
        now = datetime.now()
        
        # Daily digest at 8 AM
        if now.hour == 8 and now.minute < 2:
            logger.info("Sending daily digest...")
            await self.reporter.send_daily_digest()
        
        # Weekly digest on Sundays at 8 AM
        if now.weekday() == 6 and now.hour == 8 and now.minute < 2:
            logger.info("Sending weekly digest...")
            await self.reporter.send_weekly_digest()
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    def get_status(self) -> dict:
        """Get daemon status."""
        trigger_status = self.trigger.get_status()
        queue_status = self.builder_bridge.get_queue_status()
        cost_summary = self.cost_tracker.get_cost_summary()
        
        return {
            "running": self._running,
            "current_cycle": self._current_cycle_id,
            "trigger": trigger_status,
            "queue": queue_status,
            "costs": cost_summary
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_daemon: Optional[ReflectionDaemon] = None


def get_daemon() -> ReflectionDaemon:
    """Get global daemon instance."""
    global _daemon
    if _daemon is None:
        _daemon = ReflectionDaemon()
    return _daemon


async def run_manual_cycle(reason: str = "Manual trigger") -> Optional[str]:
    """Run a manual reflection cycle."""
    return await get_daemon().run_manual_cycle(reason)


def get_daemon_status() -> dict:
    """Get daemon status."""
    return get_daemon().get_status()


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    daemon = get_daemon()
    
    # Handle shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown():
        daemon.stop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown)
    
    # Start daemon
    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())


