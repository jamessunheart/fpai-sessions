#!/usr/bin/env python3
"""
ARIA TRIGGER ENGINE (TIER 2)
=============================

Event-driven evolution triggers that respond within 1-5 minutes.

Triggers:
- Error Spike: 3+ errors in 10 interactions OR error rate > 30%
- Correction Pattern: Same type of correction 2+ times
- Capability Request: Similar unfulfilled request 3+ times
- Performance Degradation: Response time > 2x average OR API errors
- User Rhythm: Consistent usage pattern detected

This layer sits between real-time (Tier 1) and scheduled (Tier 3) analysis.
"""

import os
import json
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("aria.evolution.triggers")

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")


class TriggerType(str, Enum):
    """Types of evolution triggers."""
    ERROR_SPIKE = "error_spike"
    CORRECTION_PATTERN = "correction_pattern"
    CAPABILITY_REQUEST = "capability_request"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    USER_RHYTHM = "user_rhythm"
    API_ERROR = "api_error"
    CUSTOM = "custom"


class TriggerStatus(str, Enum):
    """Status of a trigger event."""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    FIXED = "fixed"
    ESCALATED = "escalated"
    IGNORED = "ignored"


@dataclass
class TriggerEvent:
    """A detected trigger event."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    trigger_type: TriggerType = TriggerType.ERROR_SPIKE
    severity: str = "medium"  # low, medium, high, critical
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    related_interactions: List[int] = field(default_factory=list)
    
    # Analysis
    root_cause: str = ""
    proposed_fix: str = ""
    confidence: float = 0.0
    
    # Status
    status: TriggerStatus = TriggerStatus.DETECTED
    auto_fixed: bool = False
    fix_result: str = ""


@dataclass 
class TriggerRule:
    """A rule for detecting triggers."""
    trigger_type: TriggerType
    condition: Callable[[Dict], bool]
    action: Callable[[TriggerEvent], None]
    cooldown_minutes: int = 5
    min_confidence: float = 0.6
    auto_fix: bool = False


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

TRIGGER_SCHEMA = """
-- Trigger events
CREATE TABLE IF NOT EXISTS trigger_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    context TEXT,
    related_interactions TEXT,
    root_cause TEXT,
    proposed_fix TEXT,
    confidence REAL DEFAULT 0.0,
    status TEXT DEFAULT 'detected',
    auto_fixed INTEGER DEFAULT 0,
    fix_result TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trigger_time ON trigger_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trigger_type ON trigger_events(trigger_type);
CREATE INDEX IF NOT EXISTS idx_trigger_status ON trigger_events(status);

-- Trigger cooldowns (prevent spam)
CREATE TABLE IF NOT EXISTS trigger_cooldowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT UNIQUE NOT NULL,
    last_fired TEXT NOT NULL,
    fire_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_cooldown_type ON trigger_cooldowns(trigger_type);

-- Pattern accumulator (for detecting repeated patterns)
CREATE TABLE IF NOT EXISTS pattern_accumulator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    pattern_key TEXT NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    context TEXT,
    UNIQUE(pattern_type, pattern_key)
);

CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_accumulator(pattern_type);
CREATE INDEX IF NOT EXISTS idx_pattern_count ON pattern_accumulator(occurrence_count DESC);
"""


# ============================================================================
# TRIGGER DETECTORS
# ============================================================================

class ErrorSpikeDetector:
    """Detects error spikes in recent interactions."""
    
    def __init__(self, threshold: int = 3, window_size: int = 10):
        self.threshold = threshold
        self.window_size = window_size
        self._recent_errors: List[datetime] = []
        self._lock = threading.Lock()
    
    def add_result(self, success: bool, error_type: str = None):
        """Add an interaction result."""
        with self._lock:
            if not success:
                self._recent_errors.append(datetime.now())
            
            # Keep only recent
            cutoff = datetime.now() - timedelta(minutes=10)
            self._recent_errors = [e for e in self._recent_errors if e > cutoff]
    
    def check_spike(self) -> Tuple[bool, Dict]:
        """Check if there's an error spike."""
        with self._lock:
            recent_count = len(self._recent_errors)
            
            if recent_count >= self.threshold:
                return True, {
                    "error_count": recent_count,
                    "threshold": self.threshold,
                    "window_minutes": 10,
                    "timestamps": [e.isoformat() for e in self._recent_errors[-5:]]
                }
            
            return False, {}


class CorrectionPatternDetector:
    """Detects repeated correction patterns."""
    
    def __init__(self, threshold: int = 2):
        self.threshold = threshold
        self._patterns: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def add_correction(self, pattern_key: str, context: Dict = None):
        """Add a correction occurrence."""
        with self._lock:
            self._patterns[pattern_key].append(datetime.now())
            
            # Keep only last 24h
            cutoff = datetime.now() - timedelta(hours=24)
            self._patterns[pattern_key] = [
                t for t in self._patterns[pattern_key] if t > cutoff
            ]
    
    def check_patterns(self) -> List[Tuple[str, Dict]]:
        """Check for repeated correction patterns."""
        with self._lock:
            patterns = []
            
            for key, timestamps in self._patterns.items():
                if len(timestamps) >= self.threshold:
                    patterns.append((key, {
                        "pattern_key": key,
                        "occurrence_count": len(timestamps),
                        "threshold": self.threshold,
                        "first_seen": timestamps[0].isoformat(),
                        "last_seen": timestamps[-1].isoformat()
                    }))
            
            return patterns


class CapabilityRequestDetector:
    """Detects repeated capability requests (things Aria can't do)."""
    
    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._requests: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def add_request(self, capability: str, context: Dict = None):
        """Add an unfulfilled capability request."""
        with self._lock:
            self._requests[capability].append({
                "timestamp": datetime.now(),
                "context": context or {}
            })
            
            # Keep only last 7 days
            cutoff = datetime.now() - timedelta(days=7)
            self._requests[capability] = [
                r for r in self._requests[capability]
                if r["timestamp"] > cutoff
            ]
    
    def check_requests(self) -> List[Tuple[str, Dict]]:
        """Check for repeated capability requests."""
        with self._lock:
            requests = []
            
            for capability, occurrences in self._requests.items():
                if len(occurrences) >= self.threshold:
                    requests.append((capability, {
                        "capability": capability,
                        "request_count": len(occurrences),
                        "threshold": self.threshold,
                        "contexts": [o["context"] for o in occurrences[-3:]]
                    }))
            
            return requests


class PerformanceDegradationDetector:
    """Detects performance degradation."""
    
    def __init__(self, baseline_ms: float = 3000, multiplier: float = 2.0):
        self.baseline_ms = baseline_ms
        self.multiplier = multiplier
        self._recent_times: List[float] = []
        self._lock = threading.Lock()
    
    def add_response_time(self, time_ms: float):
        """Add a response time measurement."""
        with self._lock:
            self._recent_times.append(time_ms)
            
            # Keep last 20
            self._recent_times = self._recent_times[-20:]
    
    def check_degradation(self) -> Tuple[bool, Dict]:
        """Check for performance degradation."""
        with self._lock:
            if len(self._recent_times) < 5:
                return False, {}
            
            avg_time = sum(self._recent_times[-5:]) / 5
            threshold = self.baseline_ms * self.multiplier
            
            if avg_time > threshold:
                return True, {
                    "current_avg_ms": avg_time,
                    "baseline_ms": self.baseline_ms,
                    "threshold_ms": threshold,
                    "multiplier": self.multiplier,
                    "recent_times": self._recent_times[-5:]
                }
            
            return False, {}
    
    def update_baseline(self, new_baseline: float):
        """Update the baseline from successful operations."""
        if new_baseline > 0:
            # Weighted average with existing baseline
            self.baseline_ms = self.baseline_ms * 0.9 + new_baseline * 0.1


class UserRhythmDetector:
    """Detects user usage patterns."""
    
    def __init__(self):
        self._activity: Dict[int, int] = defaultdict(int)  # hour -> count
        self._daily_activity: Dict[int, int] = defaultdict(int)  # day of week -> count
        self._lock = threading.Lock()
    
    def add_activity(self, user_id: str):
        """Record user activity."""
        now = datetime.now()
        with self._lock:
            self._activity[now.hour] += 1
            self._daily_activity[now.weekday()] += 1
    
    def get_patterns(self) -> Dict[str, Any]:
        """Get detected usage patterns."""
        with self._lock:
            # Find peak hours
            peak_hours = sorted(
                self._activity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            # Find peak days
            peak_days = sorted(
                self._daily_activity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            return {
                "peak_hours": [h for h, _ in peak_hours],
                "peak_days": [d for d, _ in peak_days],
                "hour_distribution": dict(self._activity),
                "day_distribution": dict(self._daily_activity)
            }


# ============================================================================
# TRIGGER ENGINE
# ============================================================================

class TriggerEngine:
    """
    Manages all Tier 2 evolution triggers.
    
    - Receives events from Tier 1 (realtime learning)
    - Detects patterns that need attention
    - Triggers fixes or escalates to Tier 3
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        
        # Detectors
        self.error_spike = ErrorSpikeDetector()
        self.correction_pattern = CorrectionPatternDetector()
        self.capability_request = CapabilityRequestDetector()
        self.performance = PerformanceDegradationDetector()
        self.user_rhythm = UserRhythmDetector()
        
        # Action handlers
        self._handlers: Dict[TriggerType, Callable] = {}
        
        # Running state
        self._running = False
        self._check_interval = 60  # seconds
        
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get cursor with auto-commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(TRIGGER_SCHEMA)
        logger.info("Trigger engine initialized")
    
    # ========================================================================
    # EVENT INGESTION
    # ========================================================================
    
    def on_interaction(
        self,
        user_id: str,
        success: bool,
        response_time_ms: float,
        was_correction: bool,
        correction_type: str = None,
        error_type: str = None,
        tools_used: List[str] = None
    ):
        """
        Called for every interaction to feed the detectors.
        
        This is the main entry point from Tier 1.
        """
        # Feed error spike detector
        self.error_spike.add_result(success, error_type)
        
        # Feed correction pattern detector
        if was_correction and correction_type:
            self.correction_pattern.add_correction(correction_type)
        
        # Feed performance detector
        self.performance.add_response_time(response_time_ms)
        
        # Feed user rhythm detector
        self.user_rhythm.add_activity(user_id)
        
        # Update baseline on success
        if success and response_time_ms < 5000:
            self.performance.update_baseline(response_time_ms)
    
    def on_capability_miss(self, capability: str, context: Dict = None):
        """Called when a capability request cannot be fulfilled."""
        self.capability_request.add_request(capability, context)
    
    # ========================================================================
    # TRIGGER CHECKING
    # ========================================================================
    
    async def check_triggers(self) -> List[TriggerEvent]:
        """
        Check all detectors for trigger conditions.
        
        Returns list of triggered events.
        """
        events = []
        
        # 1. Check error spike
        is_spike, spike_context = self.error_spike.check_spike()
        if is_spike and self._can_fire(TriggerType.ERROR_SPIKE):
            event = await self._handle_error_spike(spike_context)
            if event:
                events.append(event)
        
        # 2. Check correction patterns
        patterns = self.correction_pattern.check_patterns()
        for pattern_key, pattern_context in patterns:
            if self._can_fire(TriggerType.CORRECTION_PATTERN, pattern_key):
                event = await self._handle_correction_pattern(pattern_key, pattern_context)
                if event:
                    events.append(event)
        
        # 3. Check capability requests
        requests = self.capability_request.check_requests()
        for capability, request_context in requests:
            if self._can_fire(TriggerType.CAPABILITY_REQUEST, capability):
                event = await self._handle_capability_request(capability, request_context)
                if event:
                    events.append(event)
        
        # 4. Check performance degradation
        is_degraded, perf_context = self.performance.check_degradation()
        if is_degraded and self._can_fire(TriggerType.PERFORMANCE_DEGRADATION):
            event = await self._handle_performance_degradation(perf_context)
            if event:
                events.append(event)
        
        return events
    
    def _can_fire(self, trigger_type: TriggerType, key: str = None) -> bool:
        """Check if trigger can fire (cooldown check)."""
        cooldown_key = f"{trigger_type.value}:{key}" if key else trigger_type.value
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT last_fired FROM trigger_cooldowns
                WHERE trigger_type = ?
            """, (cooldown_key,))
            
            row = cursor.fetchone()
            if row:
                last_fired = datetime.fromisoformat(row["last_fired"])
                cooldown_minutes = 5  # Default cooldown
                if datetime.now() - last_fired < timedelta(minutes=cooldown_minutes):
                    return False
        
        # Record this firing
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO trigger_cooldowns (trigger_type, last_fired, fire_count)
                VALUES (?, ?, 1)
                ON CONFLICT(trigger_type) DO UPDATE SET
                    last_fired = excluded.last_fired,
                    fire_count = fire_count + 1
            """, (cooldown_key, datetime.now().isoformat()))
        
        return True
    
    # ========================================================================
    # TRIGGER HANDLERS
    # ========================================================================
    
    async def _handle_error_spike(self, context: Dict) -> TriggerEvent:
        """Handle an error spike trigger."""
        event = TriggerEvent(
            trigger_type=TriggerType.ERROR_SPIKE,
            severity="high",
            context=context,
            status=TriggerStatus.DETECTED
        )
        
        # Analyze root cause
        event.root_cause = self._analyze_error_cause(context)
        
        # Propose fix
        event.proposed_fix = self._propose_error_fix(event.root_cause)
        event.confidence = 0.7
        
        # Save to database
        self._save_event(event)
        
        # Try auto-fix if confidence is high
        if event.confidence >= 0.8:
            success = await self._apply_fix(event)
            event.auto_fixed = success
            event.status = TriggerStatus.FIXED if success else TriggerStatus.ESCALATED
        else:
            event.status = TriggerStatus.ESCALATED
        
        # Update in database
        self._update_event(event)
        
        logger.warning(f"Error spike detected: {event.root_cause}")
        
        return event
    
    async def _handle_correction_pattern(self, pattern_key: str, context: Dict) -> TriggerEvent:
        """Handle a correction pattern trigger."""
        event = TriggerEvent(
            trigger_type=TriggerType.CORRECTION_PATTERN,
            severity="medium",
            context=context,
            status=TriggerStatus.DETECTED
        )
        
        # Analyze the pattern
        event.root_cause = f"Repeated correction for: {pattern_key}"
        
        # Propose learning update
        event.proposed_fix = f"Update interpretation rules for '{pattern_key}'"
        event.confidence = 0.8  # Corrections are reliable signals
        
        # Save
        self._save_event(event)
        
        # Correction patterns are usually safe to auto-apply
        if event.confidence >= 0.7:
            success = await self._apply_learning(event)
            event.auto_fixed = success
            event.status = TriggerStatus.FIXED if success else TriggerStatus.ESCALATED
        
        self._update_event(event)
        
        logger.info(f"Correction pattern detected: {pattern_key}")
        
        return event
    
    async def _handle_capability_request(self, capability: str, context: Dict) -> TriggerEvent:
        """Handle a capability request trigger."""
        event = TriggerEvent(
            trigger_type=TriggerType.CAPABILITY_REQUEST,
            severity="low",
            context=context,
            status=TriggerStatus.DETECTED
        )
        
        event.root_cause = f"Missing capability: {capability}"
        event.proposed_fix = f"Consider adding capability for: {capability}"
        event.confidence = 0.6
        
        # Capability requests are always escalated (need human approval)
        event.status = TriggerStatus.ESCALATED
        
        self._save_event(event)
        
        logger.info(f"Capability request detected: {capability}")
        
        return event
    
    async def _handle_performance_degradation(self, context: Dict) -> TriggerEvent:
        """Handle performance degradation trigger."""
        event = TriggerEvent(
            trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
            severity="high",
            context=context,
            status=TriggerStatus.DETECTED
        )
        
        event.root_cause = "Response times significantly above baseline"
        event.proposed_fix = "Consider: increase caching, switch to faster model, check API status"
        event.confidence = 0.7
        
        self._save_event(event)
        
        # Try to auto-mitigate
        success = await self._mitigate_performance(event)
        event.auto_fixed = success
        event.status = TriggerStatus.FIXED if success else TriggerStatus.ESCALATED
        
        self._update_event(event)
        
        logger.warning(f"Performance degradation detected: avg {context.get('current_avg_ms', 0):.0f}ms")
        
        return event
    
    # ========================================================================
    # FIX METHODS
    # ========================================================================
    
    def _analyze_error_cause(self, context: Dict) -> str:
        """Analyze the root cause of errors."""
        # This would be more sophisticated in practice
        error_count = context.get("error_count", 0)
        
        if error_count >= 5:
            return "Multiple consecutive errors - possible API or service issue"
        elif error_count >= 3:
            return "Error spike - may be query type specific"
        
        return "Unknown error cause"
    
    def _propose_error_fix(self, root_cause: str) -> str:
        """Propose a fix for the error."""
        if "API" in root_cause:
            return "Switch to fallback model and retry failed requests"
        elif "service" in root_cause:
            return "Check service health and restart if needed"
        
        return "Increase logging and monitor"
    
    async def _apply_fix(self, event: TriggerEvent) -> bool:
        """Apply an auto-fix."""
        # Placeholder - would implement actual fixes
        event.fix_result = "Auto-fix attempted"
        return True
    
    async def _apply_learning(self, event: TriggerEvent) -> bool:
        """Apply a learning update."""
        # Placeholder - would update interpretation rules
        event.fix_result = "Learning applied"
        return True
    
    async def _mitigate_performance(self, event: TriggerEvent) -> bool:
        """Mitigate performance issues."""
        # Placeholder - would increase caching aggressiveness
        event.fix_result = "Increased caching"
        return True
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    def _save_event(self, event: TriggerEvent):
        """Save a trigger event to database."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO trigger_events (
                    timestamp, trigger_type, severity, context,
                    related_interactions, root_cause, proposed_fix,
                    confidence, status, auto_fixed, fix_result, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.timestamp.isoformat(),
                event.trigger_type.value,
                event.severity,
                json.dumps(event.context),
                json.dumps(event.related_interactions),
                event.root_cause,
                event.proposed_fix,
                event.confidence,
                event.status.value,
                1 if event.auto_fixed else 0,
                event.fix_result,
                datetime.now().isoformat()
            ))
            event.id = cursor.lastrowid
    
    def _update_event(self, event: TriggerEvent):
        """Update a trigger event in database."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE trigger_events SET
                    status = ?,
                    auto_fixed = ?,
                    fix_result = ?
                WHERE id = ?
            """, (
                event.status.value,
                1 if event.auto_fixed else 0,
                event.fix_result,
                event.id
            ))
    
    # ========================================================================
    # BACKGROUND LOOP
    # ========================================================================
    
    async def run(self):
        """Run the trigger engine background loop."""
        logger.info("Trigger engine starting...")
        self._running = True
        
        while self._running:
            try:
                events = await self.check_triggers()
                
                if events:
                    logger.info(f"Processed {len(events)} trigger events")
                
                await asyncio.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"Trigger engine error: {e}")
                await asyncio.sleep(self._check_interval * 2)
    
    def stop(self):
        """Stop the trigger engine."""
        self._running = False
        logger.info("Trigger engine stopping...")
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def get_recent_events(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent trigger events."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM trigger_events
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (since, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_escalated_events(self) -> List[Dict]:
        """Get events that need human attention."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM trigger_events
                WHERE status = 'escalated'
                ORDER BY timestamp DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_patterns(self) -> Dict[str, Any]:
        """Get detected user usage patterns."""
        return self.user_rhythm.get_patterns()
    
    def get_status(self) -> Dict[str, Any]:
        """Get trigger engine status."""
        with self._cursor() as cursor:
            # Count events by type
            cursor.execute("""
                SELECT trigger_type, COUNT(*) as count
                FROM trigger_events
                WHERE timestamp >= datetime('now', '-24 hours')
                GROUP BY trigger_type
            """)
            by_type = {row["trigger_type"]: row["count"] for row in cursor.fetchall()}
            
            # Count by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM trigger_events
                WHERE timestamp >= datetime('now', '-24 hours')
                GROUP BY status
            """)
            by_status = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        return {
            "running": self._running,
            "check_interval_seconds": self._check_interval,
            "events_24h": {
                "by_type": by_type,
                "by_status": by_status
            },
            "user_patterns": self.user_rhythm.get_patterns()
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[TriggerEngine] = None


def get_trigger_engine() -> TriggerEngine:
    """Get or create global trigger engine."""
    global _engine
    if _engine is None:
        _engine = TriggerEngine()
    return _engine


async def start_trigger_engine():
    """Start the trigger engine background loop."""
    engine = get_trigger_engine()
    await engine.run()


def stop_trigger_engine():
    """Stop the trigger engine."""
    if _engine:
        _engine.stop()


def report_interaction(**kwargs):
    """Report an interaction to the trigger engine."""
    get_trigger_engine().on_interaction(**kwargs)


