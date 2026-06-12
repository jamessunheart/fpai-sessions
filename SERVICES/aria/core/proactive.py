"""
ARIA PROACTIVE DAEMON
=====================

The proactive intelligence system that makes Aria curious and helpful.

Features:
- Continuous monitoring of all systems
- Pattern detection and opportunity finding
- Auto-execution of safe actions
- Tiered notifications (urgent/routine)
- Daily digest generation
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger("aria.proactive")

# Configuration
POLL_INTERVAL = int(os.getenv("PROACTIVE_POLL_INTERVAL", "60"))  # seconds
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "8"))  # 8am local time
STATE_FILE = Path("/opt/fpai/aria/proactive_state.json")


class Priority(str, Enum):
    """Signal priority levels."""
    URGENT = "urgent"      # Telegram immediately
    HIGH = "high"          # Telegram soon
    MEDIUM = "medium"      # Dashboard digest
    LOW = "low"            # Dashboard digest


class ActionType(str, Enum):
    """Types of actions Aria can take."""
    AUTO_EXECUTE = "auto_execute"  # Do it now, no approval
    PROPOSE = "propose"            # Ask for approval
    NOTIFY = "notify"              # Just inform


@dataclass
class Signal:
    """A signal detected by a sensor."""
    source: str           # trading, infra, builder, revenue
    signal_type: str      # e.g., "strong_signal", "service_down", "queue_full"
    priority: Priority
    title: str
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    action_type: ActionType = ActionType.NOTIFY
    suggested_action: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ProactiveAction:
    """An action taken by the proactive system."""
    id: str
    signal: Signal
    action_taken: str
    result: str
    timestamp: str = ""
    approved_by: Optional[str] = None  # "auto", "user", None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class ProactiveDaemon:
    """
    The main proactive intelligence daemon.
    
    Continuously monitors all systems, detects opportunities,
    and takes appropriate actions.
    """
    
    def __init__(self):
        # Lazy imports to avoid circular dependencies
        self.sensors = {}
        self.notifications = None
        self.approvals = None
        self.curiosity = None
        
        # State tracking
        self.running = False
        self.last_poll = None
        self.last_digest = None
        self.actions_today: List[ProactiveAction] = []
        self.signals_seen: Dict[str, datetime] = {}  # Dedup signals
        
        # Stats
        self.stats = {
            "polls": 0,
            "signals_detected": 0,
            "auto_actions": 0,
            "proposals_sent": 0,
            "notifications_sent": 0,
            "cost_savings": 0.0,
            "started_at": None
        }
        
        self._load_state()
        logger.info("ProactiveDaemon initialized")
    
    async def initialize(self):
        """Initialize all components."""
        # Import sensors
        from .sensors.trading import TradingSensor
        from .sensors.infrastructure import InfrastructureSensor
        from .sensors.builder import BuilderSensor
        from .sensors.revenue import RevenueSensor
        from .notifications import NotificationSystem
        from .approvals import get_approval_system
        from .curiosity import CuriosityEngine
        
        self.sensors = {
            "trading": TradingSensor(),
            "infrastructure": InfrastructureSensor(),
            "builder": BuilderSensor(),
            "revenue": RevenueSensor()
        }
        
        self.notifications = NotificationSystem()
        self.approvals = get_approval_system()
        self.curiosity = CuriosityEngine()
        
        logger.info("All sensors and systems initialized")
    
    def _load_state(self):
        """Load persisted state."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self.last_digest = data.get("last_digest")
                self.stats = {**self.stats, **data.get("stats", {})}
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Persist state to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "last_digest": self.last_digest,
                "stats": self.stats,
                "saved_at": datetime.utcnow().isoformat()
            }
            STATE_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")
    
    async def start(self):
        """Start the proactive daemon."""
        if self.running:
            logger.warning("Daemon already running")
            return
        
        await self.initialize()
        self.running = True
        self.stats["started_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"🚀 ProactiveDaemon starting (poll interval: {POLL_INTERVAL}s)")
        
        while self.running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            
            await asyncio.sleep(POLL_INTERVAL)
    
    async def stop(self):
        """Stop the daemon."""
        self.running = False
        self._save_state()
        logger.info("ProactiveDaemon stopped")
    
    async def _run_cycle(self):
        """Run a single proactive cycle."""
        self.stats["polls"] += 1
        self.last_poll = datetime.utcnow()
        
        # 1. Collect signals from all sensors
        signals = await self._collect_signals()
        
        # 2. Filter and deduplicate
        new_signals = self._filter_signals(signals)
        
        if new_signals:
            logger.info(f"🔍 Detected {len(new_signals)} new signals")
        
        # 3. Process each signal
        for signal in new_signals:
            await self._process_signal(signal)
        
        # 4. Run curiosity engine periodically (every 10 cycles)
        if self.stats["polls"] % 10 == 0 and self.curiosity:
            await self._run_curiosity()
        
        # 5. Check if it's time for daily digest
        await self._check_digest_time()
        
        # 6. Save state periodically
        if self.stats["polls"] % 5 == 0:
            self._save_state()
    
    async def _collect_signals(self) -> List[Signal]:
        """Collect signals from all sensors."""
        all_signals = []
        
        for name, sensor in self.sensors.items():
            try:
                signals = await sensor.sense()
                all_signals.extend(signals)
            except Exception as e:
                logger.error(f"Sensor {name} error: {e}")
        
        return all_signals
    
    def _filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """Filter out duplicate or stale signals."""
        new_signals = []
        now = datetime.utcnow()
        
        for signal in signals:
            # Create a unique key for this signal
            key = f"{signal.source}:{signal.signal_type}:{signal.title}"
            
            # Check if we've seen this recently (within 5 minutes)
            if key in self.signals_seen:
                last_seen = self.signals_seen[key]
                if now - last_seen < timedelta(minutes=5):
                    continue  # Skip duplicate
            
            self.signals_seen[key] = now
            new_signals.append(signal)
            self.stats["signals_detected"] += 1
        
        # Clean up old signals
        cutoff = now - timedelta(hours=1)
        self.signals_seen = {
            k: v for k, v in self.signals_seen.items()
            if v > cutoff
        }
        
        return new_signals
    
    async def _process_signal(self, signal: Signal):
        """Process a single signal."""
        logger.info(f"Processing: [{signal.priority.value}] {signal.title}")
        
        if signal.action_type == ActionType.AUTO_EXECUTE:
            await self._auto_execute(signal)
        elif signal.action_type == ActionType.PROPOSE:
            await self._propose_action(signal)
        else:
            await self._notify(signal)
    
    async def _auto_execute(self, signal: Signal):
        """Auto-execute a safe action."""
        logger.info(f"⚡ Auto-executing: {signal.suggested_action}")
        
        action = ProactiveAction(
            id=f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            signal=signal,
            action_taken=signal.suggested_action or "Unknown action",
            result="pending",
            approved_by="auto"
        )
        
        try:
            # Execute based on signal type
            if signal.source == "infrastructure" and "scale_down" in signal.signal_type:
                result = await self._execute_scale_down(signal.data)
                action.result = result
                
                # Track cost savings
                if "savings" in signal.data:
                    self.stats["cost_savings"] += signal.data["savings"]
            
            elif signal.source == "infrastructure" and "stop_service" in signal.signal_type:
                result = await self._execute_stop_service(signal.data)
                action.result = result
            
            else:
                action.result = "No executor for this action type"
            
            self.stats["auto_actions"] += 1
            
        except Exception as e:
            action.result = f"Error: {str(e)}"
            logger.error(f"Auto-execute failed: {e}")
        
        self.actions_today.append(action)
        
        # Notify if significant
        if signal.priority in [Priority.URGENT, Priority.HIGH]:
            await self.notifications.send_urgent(
                f"✅ Auto-action: {action.action_taken}\nResult: {action.result}"
            )
    
    async def _propose_action(self, signal: Signal):
        """Propose an action for approval."""
        logger.info(f"📋 Proposing: {signal.suggested_action}")
        
        # Create approval request
        from .approvals import DecisionCategory
        
        category_map = {
            "trading": DecisionCategory.TRADING,
            "infrastructure": DecisionCategory.SPENDING,
            "builder": DecisionCategory.CHANGES,
        }
        
        category = category_map.get(signal.source, DecisionCategory.CHANGES)
        
        decision = await self.approvals.decide(
            category=category,
            action=signal.suggested_action or signal.title,
            reason=signal.description,
            context=signal.data,
            estimated_cost=signal.data.get("estimated_cost", 0),
            risk_level=signal.data.get("risk_level", "medium")
        )
        
        self.stats["proposals_sent"] += 1
        
        # Send notification
        await self.notifications.send_urgent(
            f"🤔 **Action Proposed**\n\n"
            f"**{signal.title}**\n"
            f"{signal.description}\n\n"
            f"Reply `/approve {decision.id}` or `/deny {decision.id}`"
        )
    
    async def _notify(self, signal: Signal):
        """Send a notification without action."""
        if signal.priority == Priority.URGENT:
            await self.notifications.send_urgent(
                f"🔔 **{signal.title}**\n\n{signal.description}"
            )
            self.stats["notifications_sent"] += 1
        elif signal.priority == Priority.HIGH:
            await self.notifications.send_urgent(
                f"📢 {signal.title}\n{signal.description}"
            )
            self.stats["notifications_sent"] += 1
        else:
            # Add to digest instead
            await self.notifications.add_to_digest(signal)
    
    async def _run_curiosity(self):
        """Run the curiosity engine to discover patterns."""
        if not self.curiosity:
            return
        
        try:
            insights = await self.curiosity.explore()
            for insight in insights:
                if insight.get("worth_sharing"):
                    await self.notifications.send_curiosity(
                        insight.get("message", "")
                    )
        except Exception as e:
            logger.error(f"Curiosity error: {e}")
    
    async def _check_digest_time(self):
        """Check if it's time to send daily digest."""
        now = datetime.now()
        
        # Check if it's digest hour and we haven't sent today
        if now.hour == DIGEST_HOUR:
            today = now.strftime("%Y-%m-%d")
            if self.last_digest != today:
                await self._send_daily_digest()
                self.last_digest = today
                self._save_state()
    
    async def _send_daily_digest(self):
        """Send the daily morning briefing."""
        from .digest import generate_digest
        
        try:
            digest = await generate_digest(
                actions=self.actions_today,
                stats=self.stats,
                sensors=self.sensors
            )
            
            await self.notifications.send_digest(digest)
            
            # Clear today's actions
            self.actions_today = []
            
            logger.info("📬 Daily digest sent")
            
        except Exception as e:
            logger.error(f"Digest error: {e}")
    
    # ==================== EXECUTORS ====================
    
    async def _execute_scale_down(self, data: Dict) -> str:
        """Execute GPU scale down."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Call GPU Smart Scaler
                r = await client.post(
                    "http://162.0.208.88:8450/force-check"
                )
                if r.status_code == 200:
                    return f"Scaled down GPUs. Estimated savings: ${data.get('savings', 0):.2f}/hr"
                return f"Scale down returned {r.status_code}"
        except Exception as e:
            return f"Scale down failed: {e}"
    
    async def _execute_stop_service(self, data: Dict) -> str:
        """Stop an unused service."""
        service = data.get("service")
        if not service:
            return "No service specified"
        
        # Log the intention - actual execution would require SSH
        logger.info(f"Would stop service: {service}")
        return f"Service {service} marked for stopping (requires manual action)"
    
    # ==================== STATUS ====================
    
    def get_status(self) -> Dict:
        """Get daemon status."""
        return {
            "running": self.running,
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
            "last_digest": self.last_digest,
            "stats": self.stats,
            "sensors": list(self.sensors.keys()),
            "actions_today": len(self.actions_today),
            "poll_interval": POLL_INTERVAL
        }
    
    async def force_cycle(self):
        """Force a proactive cycle now."""
        await self._run_cycle()
        return {"status": "cycle_complete", "signals": self.stats["signals_detected"]}


# Singleton instance
_daemon: Optional[ProactiveDaemon] = None


def get_daemon() -> ProactiveDaemon:
    """Get or create the proactive daemon."""
    global _daemon
    if _daemon is None:
        _daemon = ProactiveDaemon()
    return _daemon


async def start_daemon():
    """Start the proactive daemon."""
    daemon = get_daemon()
    await daemon.start()


