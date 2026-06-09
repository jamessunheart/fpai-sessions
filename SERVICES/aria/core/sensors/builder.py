"""
BUILDER SENSOR
==============

Monitors the autonomous builder system for status and opportunities.

Watches:
- Pending/running/failed tasks
- Recent escalations
- Queue depth
- Self-improvement opportunities
"""

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

from ..proactive import Signal, Priority, ActionType

logger = logging.getLogger("aria.sensors.builder")

# Builder paths
BUILDER_QUEUE_DB = os.getenv("BUILDER_QUEUE_DB", "/opt/fpai/ai-brain/v2/thinking_v2.db")
BUILDER_ESCALATIONS_DIR = Path("/opt/fpai/ai-brain/v2/builder/escalations")
BUILDER_SPECS_DIR = Path("/opt/fpai/ai-brain/v2/builder/specs")

# Thresholds
QUEUE_BACKUP_THRESHOLD = 5  # Tasks before alerting
ESCALATION_PRIORITY_THRESHOLD = 1  # Any escalation is important


class BuilderSensor:
    """
    Sensor for builder queue and task status.
    
    Monitors:
    - Task queue depth
    - Failed/escalated tasks
    - Improvement opportunities
    """
    
    def __init__(self):
        self.last_queue_depth = 0
        self.seen_escalations = set()
        logger.info("BuilderSensor initialized")
    
    async def sense(self) -> List[Signal]:
        """
        Sense builder state and generate signals.
        
        Returns list of signals detected.
        """
        signals = []
        
        # 1. Check queue status
        queue_signals = self._check_queue()
        signals.extend(queue_signals)
        
        # 2. Check for escalations
        escalation_signals = self._check_escalations()
        signals.extend(escalation_signals)
        
        # 3. Check pending specs
        spec_signals = self._check_pending_specs()
        signals.extend(spec_signals)
        
        return signals
    
    def _check_queue(self) -> List[Signal]:
        """Check builder queue status."""
        signals = []
        
        try:
            if not Path(BUILDER_QUEUE_DB).exists():
                return signals
            
            conn = sqlite3.connect(BUILDER_QUEUE_DB)
            c = conn.cursor()
            
            # Get queue stats
            c.execute("""
                SELECT status, COUNT(*) as count 
                FROM build_queue 
                GROUP BY status
            """)
            stats = {row[0]: row[1] for row in c.fetchall()}
            
            pending = stats.get("pending", 0)
            running = stats.get("running", 0)
            failed = stats.get("failed", 0)
            completed = stats.get("completed", 0)
            
            conn.close()
            
            # Alert if queue is backing up
            if pending >= QUEUE_BACKUP_THRESHOLD:
                signals.append(Signal(
                    source="builder",
                    signal_type="queue_backup",
                    priority=Priority.MEDIUM,
                    title=f"📋 Builder Queue Growing: {pending} tasks pending",
                    description=f"Queue: {pending} pending, {running} running, {failed} failed",
                    data={
                        "pending": pending,
                        "running": running,
                        "failed": failed,
                        "completed": completed
                    },
                    action_type=ActionType.PROPOSE,
                    suggested_action="Scale up GPU fleet for faster builds"
                ))
            
            # Alert on failures
            if failed > 0 and failed > self.last_queue_depth:
                signals.append(Signal(
                    source="builder",
                    signal_type="build_failures",
                    priority=Priority.MEDIUM,
                    title=f"⚠️ Builder: {failed} Failed Tasks",
                    description="Some builds have failed and may need attention.",
                    data={"failed_count": failed},
                    action_type=ActionType.NOTIFY
                ))
            
            self.last_queue_depth = pending
            
        except Exception as e:
            logger.warning(f"Queue check error: {e}")
        
        return signals
    
    def _check_escalations(self) -> List[Signal]:
        """Check for new escalations."""
        signals = []
        
        try:
            if not BUILDER_ESCALATIONS_DIR.exists():
                return signals
            
            # Find recent escalation files
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            for esc_file in BUILDER_ESCALATIONS_DIR.glob("escalate_*.json"):
                # Skip if we've seen this
                if esc_file.name in self.seen_escalations:
                    continue
                
                # Check if recent
                try:
                    mtime = datetime.fromtimestamp(esc_file.stat().st_mtime)
                    if mtime < cutoff:
                        continue
                except:
                    continue
                
                # Read escalation
                try:
                    import json
                    data = json.loads(esc_file.read_text())
                    
                    self.seen_escalations.add(esc_file.name)
                    
                    signals.append(Signal(
                        source="builder",
                        signal_type="escalation",
                        priority=Priority.MEDIUM,
                        title=f"🚨 Build Escalation: {data.get('task_id', 'Unknown')}",
                        description=data.get("reason", "Build required manual intervention"),
                        data={
                            "task_id": data.get("task_id"),
                            "reason": data.get("reason"),
                            "file": esc_file.name
                        },
                        action_type=ActionType.NOTIFY
                    ))
                except:
                    continue
            
        except Exception as e:
            logger.warning(f"Escalation check error: {e}")
        
        return signals
    
    def _check_pending_specs(self) -> List[Signal]:
        """Check for pending specs waiting to be built."""
        signals = []
        
        try:
            pending_dir = BUILDER_SPECS_DIR / "pending"
            if not pending_dir.exists():
                return signals
            
            pending_specs = list(pending_dir.glob("*.md"))
            
            if len(pending_specs) > 0:
                spec_names = [s.stem for s in pending_specs[:5]]
                
                signals.append(Signal(
                    source="builder",
                    signal_type="pending_specs",
                    priority=Priority.LOW,
                    title=f"📝 {len(pending_specs)} Spec(s) Awaiting Build",
                    description=f"Pending: {', '.join(spec_names)}",
                    data={
                        "count": len(pending_specs),
                        "specs": spec_names
                    },
                    action_type=ActionType.NOTIFY
                ))
        
        except Exception as e:
            logger.warning(f"Pending specs check error: {e}")
        
        return signals
    
    async def get_status(self) -> Dict:
        """Get sensor status."""
        return {
            "name": "builder",
            "last_queue_depth": self.last_queue_depth,
            "seen_escalations": len(self.seen_escalations),
            "db_path": BUILDER_QUEUE_DB
        }


