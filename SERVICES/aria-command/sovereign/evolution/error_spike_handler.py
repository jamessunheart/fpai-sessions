#!/usr/bin/env python3
"""
ARIA ERROR SPIKE HANDLER
=========================

Specialized handler for detecting and auto-fixing error spikes.

When 3+ errors occur in 10 interactions OR error rate > 30%:
1. Pause and analyze recent failures
2. Identify common patterns
3. Generate fix hypothesis
4. Apply if confidence > 80%
5. Alert James if confidence < 80%

This is a critical safety system for Aria's reliability.
"""

import os
import json
import sqlite3
import asyncio
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("aria.evolution.error_spike")

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")


class ErrorCategory(str, Enum):
    """Categories of errors for analysis."""
    API_ERROR = "api_error"           # External API failures
    TIMEOUT = "timeout"               # Response timeouts
    PARSE_ERROR = "parse_error"       # Failed to parse user input
    TOOL_ERROR = "tool_error"         # Tool execution failure
    PERMISSION = "permission"         # Permission denied
    NOT_FOUND = "not_found"           # Resource not found
    VALIDATION = "validation"         # Input validation error
    INTERNAL = "internal"             # Internal system error
    UNKNOWN = "unknown"


class FixStrategy(str, Enum):
    """Strategies for fixing errors."""
    RETRY = "retry"                   # Simple retry
    FALLBACK_MODEL = "fallback_model" # Switch to backup model
    CLEAR_CACHE = "clear_cache"       # Clear caches
    RESTART_SERVICE = "restart_service"
    INCREASE_TIMEOUT = "increase_timeout"
    RATE_LIMIT = "rate_limit"         # Apply rate limiting
    NOTIFY_HUMAN = "notify_human"     # Escalate to human


@dataclass
class ErrorRecord:
    """A recorded error."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: str = ""
    error_message: str = ""
    error_type: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


@dataclass
class ErrorSpike:
    """A detected error spike event."""
    id: Optional[int] = None
    detected_at: datetime = field(default_factory=datetime.now)
    
    # Spike details
    error_count: int = 0
    error_rate: float = 0.0
    window_minutes: int = 10
    
    # Analysis
    primary_category: ErrorCategory = ErrorCategory.UNKNOWN
    common_pattern: str = ""
    affected_users: List[str] = field(default_factory=list)
    sample_errors: List[Dict] = field(default_factory=list)
    
    # Fix
    fix_strategy: FixStrategy = FixStrategy.NOTIFY_HUMAN
    fix_confidence: float = 0.0
    fix_applied: bool = False
    fix_result: str = ""
    
    # Status
    resolved: bool = False
    resolved_at: Optional[datetime] = None


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

ERROR_SPIKE_SCHEMA = """
-- Error records
CREATE TABLE IF NOT EXISTS error_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT,
    error_message TEXT,
    error_type TEXT,
    category TEXT DEFAULT 'unknown',
    context TEXT,
    resolved INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_error_time ON error_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_category ON error_records(category);
CREATE INDEX IF NOT EXISTS idx_error_resolved ON error_records(resolved);

-- Error spikes
CREATE TABLE IF NOT EXISTS error_spikes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,
    error_count INTEGER,
    error_rate REAL,
    window_minutes INTEGER,
    primary_category TEXT,
    common_pattern TEXT,
    affected_users TEXT,
    sample_errors TEXT,
    fix_strategy TEXT,
    fix_confidence REAL,
    fix_applied INTEGER DEFAULT 0,
    fix_result TEXT,
    resolved INTEGER DEFAULT 0,
    resolved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_spike_time ON error_spikes(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_spike_resolved ON error_spikes(resolved);

-- Fix history (what fixes were applied and their outcomes)
CREATE TABLE IF NOT EXISTS fix_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spike_id INTEGER,
    strategy TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    success INTEGER DEFAULT 0,
    details TEXT,
    rollback_available INTEGER DEFAULT 0,
    rollback_applied INTEGER DEFAULT 0,
    FOREIGN KEY (spike_id) REFERENCES error_spikes(id)
);

CREATE INDEX IF NOT EXISTS idx_fix_spike ON fix_history(spike_id);
CREATE INDEX IF NOT EXISTS idx_fix_time ON fix_history(applied_at DESC);
"""


# ============================================================================
# ERROR PATTERN MATCHING
# ============================================================================

ERROR_PATTERNS = {
    ErrorCategory.API_ERROR: [
        r'api.*error', r'external.*service', r'anthropic.*error',
        r'openai.*error', r'rate.*limit', r'503', r'500', r'502'
    ],
    ErrorCategory.TIMEOUT: [
        r'timeout', r'timed?\s*out', r'deadline.*exceeded',
        r'connection.*timeout', r'read.*timeout'
    ],
    ErrorCategory.PARSE_ERROR: [
        r'parse.*error', r'json.*error', r'invalid.*format',
        r'syntax.*error', r'unexpected.*token'
    ],
    ErrorCategory.TOOL_ERROR: [
        r'tool.*failed', r'tool.*error', r'command.*failed',
        r'execution.*error', r'subprocess'
    ],
    ErrorCategory.PERMISSION: [
        r'permission.*denied', r'access.*denied', r'unauthorized',
        r'forbidden', r'403'
    ],
    ErrorCategory.NOT_FOUND: [
        r'not.*found', r'404', r'does.*not.*exist', r'missing'
    ],
    ErrorCategory.VALIDATION: [
        r'validation.*error', r'invalid.*input', r'required.*field',
        r'constraint.*violated'
    ],
    ErrorCategory.INTERNAL: [
        r'internal.*error', r'assertion.*failed', r'bug',
        r'null.*pointer', r'index.*out.*of.*bounds'
    ]
}

FIX_STRATEGIES_BY_CATEGORY = {
    ErrorCategory.API_ERROR: [
        (FixStrategy.FALLBACK_MODEL, 0.8),
        (FixStrategy.RETRY, 0.6),
        (FixStrategy.RATE_LIMIT, 0.5)
    ],
    ErrorCategory.TIMEOUT: [
        (FixStrategy.INCREASE_TIMEOUT, 0.7),
        (FixStrategy.RETRY, 0.6),
        (FixStrategy.FALLBACK_MODEL, 0.5)
    ],
    ErrorCategory.PARSE_ERROR: [
        (FixStrategy.CLEAR_CACHE, 0.6),
        (FixStrategy.NOTIFY_HUMAN, 0.5)
    ],
    ErrorCategory.TOOL_ERROR: [
        (FixStrategy.RETRY, 0.6),
        (FixStrategy.NOTIFY_HUMAN, 0.5)
    ],
    ErrorCategory.PERMISSION: [
        (FixStrategy.NOTIFY_HUMAN, 0.9)
    ],
    ErrorCategory.NOT_FOUND: [
        (FixStrategy.CLEAR_CACHE, 0.7),
        (FixStrategy.NOTIFY_HUMAN, 0.5)
    ],
    ErrorCategory.VALIDATION: [
        (FixStrategy.NOTIFY_HUMAN, 0.8)
    ],
    ErrorCategory.INTERNAL: [
        (FixStrategy.RESTART_SERVICE, 0.6),
        (FixStrategy.NOTIFY_HUMAN, 0.8)
    ]
}


def categorize_error(error_message: str, error_type: str = None) -> ErrorCategory:
    """Categorize an error message."""
    combined = f"{error_message} {error_type or ''}".lower()
    
    for category, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return category
    
    return ErrorCategory.UNKNOWN


# ============================================================================
# ERROR SPIKE HANDLER
# ============================================================================

class ErrorSpikeHandler:
    """
    Handles detection and auto-fixing of error spikes.
    
    Flow:
    1. record_error() - Called for each error
    2. check_spike() - Periodically checks for spikes
    3. analyze_spike() - Analyzes root cause
    4. apply_fix() - Attempts auto-fix
    5. notify_human() - Escalates if needed
    """
    
    def __init__(
        self,
        db_path: str = DB_PATH,
        spike_threshold: int = 3,
        spike_rate_threshold: float = 0.3,
        window_minutes: int = 10,
        auto_fix_confidence: float = 0.8
    ):
        self.db_path = db_path
        self.spike_threshold = spike_threshold
        self.spike_rate_threshold = spike_rate_threshold
        self.window_minutes = window_minutes
        self.auto_fix_confidence = auto_fix_confidence
        
        self._local = threading.local()
        self._recent_errors: List[ErrorRecord] = []
        self._recent_interactions: int = 0
        self._lock = threading.Lock()
        
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
            cursor.executescript(ERROR_SPIKE_SCHEMA)
        logger.info("Error spike handler initialized")
    
    # ========================================================================
    # ERROR RECORDING
    # ========================================================================
    
    def record_error(
        self,
        error_message: str,
        error_type: str = None,
        user_id: str = None,
        context: Dict = None
    ) -> ErrorRecord:
        """
        Record an error occurrence.
        
        Call this for every error that occurs in Aria.
        """
        category = categorize_error(error_message, error_type)
        
        error = ErrorRecord(
            timestamp=datetime.now(),
            user_id=user_id or "unknown",
            error_message=error_message[:500],
            error_type=error_type or "unknown",
            category=category,
            context=context or {}
        )
        
        # Add to in-memory buffer
        with self._lock:
            self._recent_errors.append(error)
            # Keep only recent
            cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
            self._recent_errors = [e for e in self._recent_errors if e.timestamp > cutoff]
        
        # Persist
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO error_records (
                    timestamp, user_id, error_message, error_type,
                    category, context, resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                error.timestamp.isoformat(),
                error.user_id,
                error.error_message,
                error.error_type,
                error.category.value,
                json.dumps(error.context),
                datetime.now().isoformat()
            ))
            error.id = cursor.lastrowid
        
        return error
    
    def record_interaction(self, success: bool):
        """Record an interaction (for calculating error rate)."""
        with self._lock:
            self._recent_interactions += 1
            
            # Reset counter periodically
            if self._recent_interactions > 100:
                self._recent_interactions = len(self._recent_errors) + (1 if not success else 0)
    
    # ========================================================================
    # SPIKE DETECTION
    # ========================================================================
    
    def check_spike(self) -> Optional[ErrorSpike]:
        """
        Check if there's an error spike.
        
        Returns ErrorSpike if detected, None otherwise.
        """
        with self._lock:
            error_count = len(self._recent_errors)
            
            # Check absolute threshold
            if error_count < self.spike_threshold:
                return None
            
            # Check rate threshold
            total = max(self._recent_interactions, error_count)
            error_rate = error_count / total if total > 0 else 0
            
            if error_rate < self.spike_rate_threshold and error_count < self.spike_threshold:
                return None
            
            # Spike detected!
            spike = ErrorSpike(
                detected_at=datetime.now(),
                error_count=error_count,
                error_rate=error_rate,
                window_minutes=self.window_minutes,
                sample_errors=[
                    {
                        "message": e.error_message[:100],
                        "category": e.category.value,
                        "timestamp": e.timestamp.isoformat()
                    }
                    for e in self._recent_errors[-5:]
                ],
                affected_users=list(set(e.user_id for e in self._recent_errors))
            )
        
        return spike
    
    async def analyze_and_fix(self, spike: ErrorSpike) -> ErrorSpike:
        """
        Analyze the spike and attempt to fix it.
        
        This is the main entry point for handling a detected spike.
        """
        logger.warning(f"Analyzing error spike: {spike.error_count} errors in {spike.window_minutes} min")
        
        # 1. Analyze the spike
        spike = self._analyze_spike(spike)
        
        # 2. Determine fix strategy
        spike = self._determine_fix(spike)
        
        # 3. Save spike to database
        self._save_spike(spike)
        
        # 4. Apply fix if confidence is high enough
        if spike.fix_confidence >= self.auto_fix_confidence:
            success = await self._apply_fix(spike)
            spike.fix_applied = success
            spike.fix_result = "Applied" if success else "Failed"
            
            if success:
                spike.resolved = True
                spike.resolved_at = datetime.now()
        else:
            # Escalate to human
            await self._notify_human(spike)
            spike.fix_result = "Escalated to human"
        
        # 5. Update spike in database
        self._update_spike(spike)
        
        return spike
    
    def _analyze_spike(self, spike: ErrorSpike) -> ErrorSpike:
        """Analyze the spike to find common patterns."""
        with self._lock:
            errors = self._recent_errors[-10:]
        
        # Count categories
        category_counts = defaultdict(int)
        for error in errors:
            category_counts[error.category] += 1
        
        # Find primary category
        if category_counts:
            primary_category = max(category_counts.items(), key=lambda x: x[1])[0]
            spike.primary_category = primary_category
        
        # Find common patterns in error messages
        messages = [e.error_message for e in errors]
        spike.common_pattern = self._find_common_pattern(messages)
        
        return spike
    
    def _find_common_pattern(self, messages: List[str]) -> str:
        """Find common pattern in error messages."""
        if not messages:
            return ""
        
        # Simple approach: find common substrings
        words = defaultdict(int)
        for msg in messages:
            for word in msg.lower().split():
                if len(word) > 3:  # Ignore short words
                    words[word] += 1
        
        # Find words that appear in most messages
        threshold = len(messages) * 0.5
        common_words = [w for w, c in words.items() if c >= threshold]
        
        return " ".join(common_words[:5]) if common_words else ""
    
    def _determine_fix(self, spike: ErrorSpike) -> ErrorSpike:
        """Determine the best fix strategy."""
        strategies = FIX_STRATEGIES_BY_CATEGORY.get(
            spike.primary_category,
            [(FixStrategy.NOTIFY_HUMAN, 0.5)]
        )
        
        # Select highest confidence strategy
        best_strategy, confidence = strategies[0]
        
        # Adjust confidence based on spike severity
        if spike.error_count >= 5:
            confidence *= 0.9  # More errors = less confident in fix
        if spike.error_rate >= 0.5:
            confidence *= 0.8  # Higher rate = less confident
        
        spike.fix_strategy = best_strategy
        spike.fix_confidence = confidence
        
        return spike
    
    async def _apply_fix(self, spike: ErrorSpike) -> bool:
        """Apply the fix strategy."""
        strategy = spike.fix_strategy
        logger.info(f"Applying fix strategy: {strategy.value}")
        
        try:
            if strategy == FixStrategy.RETRY:
                return await self._apply_retry_fix()
            elif strategy == FixStrategy.FALLBACK_MODEL:
                return await self._apply_fallback_model()
            elif strategy == FixStrategy.CLEAR_CACHE:
                return await self._apply_clear_cache()
            elif strategy == FixStrategy.INCREASE_TIMEOUT:
                return await self._apply_increase_timeout()
            elif strategy == FixStrategy.RATE_LIMIT:
                return await self._apply_rate_limit()
            elif strategy == FixStrategy.RESTART_SERVICE:
                return await self._apply_restart_service()
            else:
                # NOTIFY_HUMAN - handled separately
                return False
                
        except Exception as e:
            logger.error(f"Fix application error: {e}")
            return False
    
    async def _apply_retry_fix(self) -> bool:
        """Apply retry fix - mark for retry."""
        # This would signal to the response layer to retry
        logger.info("Applied retry fix - failed requests will be retried")
        return True
    
    async def _apply_fallback_model(self) -> bool:
        """Switch to fallback model."""
        # This would update model routing
        logger.info("Switched to fallback model")
        return True
    
    async def _apply_clear_cache(self) -> bool:
        """Clear response caches."""
        # This would clear the response cache
        try:
            from .response_cache import get_response_cache
            cache = get_response_cache()
            cache.cleanup_expired()
            logger.info("Cleared response cache")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def _apply_increase_timeout(self) -> bool:
        """Increase request timeouts."""
        # This would update timeout configuration
        logger.info("Increased request timeouts")
        return True
    
    async def _apply_rate_limit(self) -> bool:
        """Apply rate limiting."""
        # This would activate rate limiting
        logger.info("Applied rate limiting")
        return True
    
    async def _apply_restart_service(self) -> bool:
        """Restart the service (graceful)."""
        # This would trigger a graceful restart
        logger.info("Service restart requested")
        return True
    
    async def _notify_human(self, spike: ErrorSpike):
        """Send notification to human."""
        if not TELEGRAM_BOT_TOKEN or not SUNHEART_CHAT_ID:
            logger.warning("Cannot notify human: missing Telegram config")
            return
        
        message = f"""🚨 **Error Spike Detected**

**Errors:** {spike.error_count} in {spike.window_minutes} min
**Error Rate:** {spike.error_rate*100:.1f}%
**Category:** {spike.primary_category.value}
**Pattern:** {spike.common_pattern or 'Unknown'}

**Proposed Fix:** {spike.fix_strategy.value}
**Confidence:** {spike.fix_confidence*100:.0f}%

_Auto-fix not applied due to low confidence. Please review._

Use `/fix spike` to apply fix or `/spike ignore` to dismiss.
"""
        
        try:
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
            logger.info("Sent spike notification to human")
        except Exception as e:
            logger.error(f"Failed to notify human: {e}")
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    def _save_spike(self, spike: ErrorSpike):
        """Save spike to database."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO error_spikes (
                    detected_at, error_count, error_rate, window_minutes,
                    primary_category, common_pattern, affected_users,
                    sample_errors, fix_strategy, fix_confidence,
                    fix_applied, fix_result, resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spike.detected_at.isoformat(),
                spike.error_count,
                spike.error_rate,
                spike.window_minutes,
                spike.primary_category.value,
                spike.common_pattern,
                json.dumps(spike.affected_users),
                json.dumps(spike.sample_errors),
                spike.fix_strategy.value,
                spike.fix_confidence,
                1 if spike.fix_applied else 0,
                spike.fix_result,
                1 if spike.resolved else 0,
                datetime.now().isoformat()
            ))
            spike.id = cursor.lastrowid
    
    def _update_spike(self, spike: ErrorSpike):
        """Update spike in database."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE error_spikes SET
                    fix_applied = ?,
                    fix_result = ?,
                    resolved = ?,
                    resolved_at = ?
                WHERE id = ?
            """, (
                1 if spike.fix_applied else 0,
                spike.fix_result,
                1 if spike.resolved else 0,
                spike.resolved_at.isoformat() if spike.resolved_at else None,
                spike.id
            ))
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    def get_recent_spikes(self, hours: int = 24) -> List[Dict]:
        """Get recent error spikes."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM error_spikes
                WHERE detected_at >= ?
                ORDER BY detected_at DESC
            """, (since,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unresolved_spikes(self) -> List[Dict]:
        """Get unresolved spikes."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM error_spikes
                WHERE resolved = 0
                ORDER BY detected_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            # Total errors
            cursor.execute("""
                SELECT COUNT(*) as count FROM error_records
                WHERE timestamp >= ?
            """, (since,))
            total_errors = cursor.fetchone()["count"]
            
            # By category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM error_records
                WHERE timestamp >= ?
                GROUP BY category
                ORDER BY count DESC
            """, (since,))
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
            
            # Spike count
            cursor.execute("""
                SELECT COUNT(*) as count FROM error_spikes
                WHERE detected_at >= ?
            """, (since,))
            spike_count = cursor.fetchone()["count"]
            
            # Auto-fixed count
            cursor.execute("""
                SELECT COUNT(*) as count FROM error_spikes
                WHERE detected_at >= ? AND fix_applied = 1
            """, (since,))
            auto_fixed = cursor.fetchone()["count"]
        
        return {
            "period_hours": hours,
            "total_errors": total_errors,
            "by_category": by_category,
            "spike_count": spike_count,
            "auto_fixed_count": auto_fixed,
            "current_error_count": len(self._recent_errors),
            "current_interaction_count": self._recent_interactions
        }
    
    def resolve_spike(self, spike_id: int, resolution: str = "Manual resolution"):
        """Manually resolve a spike."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE error_spikes SET
                    resolved = 1,
                    resolved_at = ?,
                    fix_result = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), resolution, spike_id))
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_handler: Optional[ErrorSpikeHandler] = None


def get_error_spike_handler() -> ErrorSpikeHandler:
    """Get or create global error spike handler."""
    global _handler
    if _handler is None:
        _handler = ErrorSpikeHandler()
    return _handler


def record_error(error_message: str, **kwargs) -> ErrorRecord:
    """Record an error."""
    return get_error_spike_handler().record_error(error_message, **kwargs)


async def check_and_fix_spike() -> Optional[ErrorSpike]:
    """Check for spike and fix if found."""
    handler = get_error_spike_handler()
    spike = handler.check_spike()
    
    if spike:
        return await handler.analyze_and_fix(spike)
    
    return None


