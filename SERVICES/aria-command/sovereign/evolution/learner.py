#!/usr/bin/env python3
"""
ARIA EVOLUTION LEARNER
=======================

Learns from errors and healing attempts to improve over time.

Features:
- Tracks all errors and their resolutions
- Identifies new error patterns
- Proposes new auto-fix rules
- Requires human approval for new patterns
- Improves response prompts based on feedback
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import threading
import httpx

logger = logging.getLogger("aria.evolution.learner")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
MIN_OCCURRENCES_FOR_PATTERN = 3  # Need to see error 3 times before proposing pattern


SCHEMA = """
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT,
    context TEXT,
    was_healed INTEGER DEFAULT 0,
    heal_action TEXT,
    heal_success INTEGER
);

CREATE TABLE IF NOT EXISTS proposed_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT,
    pattern_regex TEXT,
    suggested_action TEXT,
    occurrence_count INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',
    approved_at TEXT,
    approved_by TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    feedback_type TEXT,
    context TEXT,
    suggestion TEXT,
    implemented INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp);
CREATE INDEX IF NOT EXISTS idx_errors_type ON errors(error_type);
CREATE INDEX IF NOT EXISTS idx_proposed_status ON proposed_patterns(status);
"""


@dataclass
class ErrorRecord:
    """A recorded error."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    error_type: str = ""
    error_message: str = ""
    context: str = ""
    was_healed: bool = False
    heal_action: Optional[str] = None
    heal_success: Optional[bool] = None


@dataclass
class ProposedPattern:
    """A proposed new pattern."""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    name: str = ""
    pattern_regex: str = ""
    suggested_action: str = ""
    occurrence_count: int = 1
    status: str = "pending"  # pending, approved, rejected
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


class EvolutionLearner:
    """
    Learns from errors and healing attempts.
    
    Process:
    1. Record all errors
    2. Track which were healed and how
    3. Identify recurring unhealed errors
    4. Propose new patterns for approval
    5. Apply approved patterns
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get a cursor with auto-commit."""
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
            cursor.executescript(SCHEMA)
        logger.info(f"Evolution learner initialized: {self.db_path}")
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        context: str = ""
    ) -> int:
        """
        Record an error for learning.
        
        Returns the error record ID.
        """
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO errors (timestamp, error_type, error_message, context)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                error_type,
                error_message[:2000],  # Truncate
                context[:1000]
            ))
            error_id = cursor.lastrowid
        
        # Check if we should propose a new pattern
        self._check_for_pattern(error_type, error_message)
        
        return error_id
    
    def record_healing(
        self,
        error_id: int,
        action: str,
        success: bool
    ):
        """Record that an error was healed."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE errors
                SET was_healed = 1, heal_action = ?, heal_success = ?
                WHERE id = ?
            """, (action, 1 if success else 0, error_id))
    
    def _check_for_pattern(self, error_type: str, error_message: str):
        """
        Check if we should propose a new pattern.
        
        If we've seen this error type enough times without healing,
        propose a new pattern.
        """
        with self._cursor() as cursor:
            # Count unhealed errors of this type in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) as count FROM errors
                WHERE error_type = ?
                  AND was_healed = 0
                  AND timestamp >= ?
            """, (error_type, (datetime.now() - timedelta(hours=24)).isoformat()))
            
            count = cursor.fetchone()["count"]
            
            if count >= MIN_OCCURRENCES_FOR_PATTERN:
                # Check if we already have a pending proposal
                cursor.execute("""
                    SELECT id FROM proposed_patterns
                    WHERE name LIKE ? AND status = 'pending'
                """, (f"%{error_type}%",))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Increment count
                    cursor.execute("""
                        UPDATE proposed_patterns
                        SET occurrence_count = occurrence_count + 1
                        WHERE id = ?
                    """, (existing["id"],))
                else:
                    # Create new proposal
                    self._create_proposal(error_type, error_message)
    
    def _create_proposal(self, error_type: str, error_message: str):
        """Create a new pattern proposal."""
        # Generate a simple regex from the error message
        # (In a real system, this would be smarter)
        import re
        
        # Extract key parts of the error
        pattern_parts = []
        if error_type:
            pattern_parts.append(re.escape(error_type))
        
        # Extract key words from message
        keywords = re.findall(r'\b[A-Z][a-z]+Error\b|\b[a-z_]+\b', error_message)
        unique_keywords = list(dict.fromkeys(keywords))[:5]
        pattern_parts.extend(re.escape(kw) for kw in unique_keywords)
        
        pattern_regex = "|".join(pattern_parts) if pattern_parts else error_type
        
        # Suggest an action based on error type
        if "memory" in error_type.lower():
            suggested_action = "clear_caches_restart"
        elif "connection" in error_type.lower():
            suggested_action = "restart_service"
        elif "timeout" in error_type.lower():
            suggested_action = "retry_with_backoff"
        else:
            suggested_action = "alert_human"
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO proposed_patterns (
                    created_at, name, pattern_regex, suggested_action, occurrence_count
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                f"Auto: {error_type[:50]}",
                pattern_regex[:500],
                suggested_action,
                MIN_OCCURRENCES_FOR_PATTERN
            ))
        
        # Notify about new proposal
        asyncio.run(self._notify_proposal(error_type, pattern_regex, suggested_action))
    
    async def _notify_proposal(self, error_type: str, pattern: str, action: str):
        """Notify about a new pattern proposal."""
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.getenv("SUNHEART_CHAT_ID", "")
            
            if not token or not chat_id:
                return
            
            message = (
                f"🧬 **New Pattern Proposal**\n\n"
                f"**Error Type:** {error_type}\n"
                f"**Pattern:** `{pattern[:100]}`\n"
                f"**Suggested Action:** {action}\n\n"
                f"Use `/approve_pattern <id>` to activate."
            )
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                )
        except Exception as e:
            logger.error(f"Failed to notify proposal: {e}")
    
    def get_pending_proposals(self) -> List[ProposedPattern]:
        """Get all pending pattern proposals."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM proposed_patterns
                WHERE status = 'pending'
                ORDER BY occurrence_count DESC
            """)
            rows = cursor.fetchall()
            
            return [
                ProposedPattern(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    name=row["name"],
                    pattern_regex=row["pattern_regex"],
                    suggested_action=row["suggested_action"],
                    occurrence_count=row["occurrence_count"],
                    status=row["status"]
                )
                for row in rows
            ]
    
    def approve_proposal(self, proposal_id: int, approved_by: str = "human") -> bool:
        """Approve a pattern proposal."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE proposed_patterns
                SET status = 'approved', approved_at = ?, approved_by = ?
                WHERE id = ? AND status = 'pending'
            """, (datetime.now().isoformat(), approved_by, proposal_id))
            
            return cursor.rowcount > 0
    
    def reject_proposal(self, proposal_id: int) -> bool:
        """Reject a pattern proposal."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE proposed_patterns
                SET status = 'rejected'
                WHERE id = ? AND status = 'pending'
            """, (proposal_id,))
            
            return cursor.rowcount > 0
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            # Total errors
            cursor.execute("""
                SELECT COUNT(*) as count FROM errors
                WHERE timestamp >= ?
            """, (since,))
            total = cursor.fetchone()["count"]
            
            # Healed vs unhealed
            cursor.execute("""
                SELECT was_healed, COUNT(*) as count FROM errors
                WHERE timestamp >= ?
                GROUP BY was_healed
            """, (since,))
            by_healed = {row["was_healed"]: row["count"] for row in cursor.fetchall()}
            
            # By type
            cursor.execute("""
                SELECT error_type, COUNT(*) as count FROM errors
                WHERE timestamp >= ?
                GROUP BY error_type
                ORDER BY count DESC
                LIMIT 10
            """, (since,))
            by_type = {row["error_type"]: row["count"] for row in cursor.fetchall()}
        
        healed = by_healed.get(1, 0)
        unhealed = by_healed.get(0, 0)
        
        return {
            "period_hours": hours,
            "total_errors": total,
            "healed": healed,
            "unhealed": unhealed,
            "heal_rate": (healed / total * 100) if total > 0 else 0,
            "by_type": by_type
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Need asyncio for notification
import asyncio


# ============================================================================
# SINGLETON
# ============================================================================

_learner: Optional[EvolutionLearner] = None


def get_learner() -> EvolutionLearner:
    """Get or create global learner."""
    global _learner
    if _learner is None:
        _learner = EvolutionLearner()
    return _learner


def learn_from_error(error_type: str, error_message: str, context: str = "") -> int:
    """Record an error for learning."""
    return get_learner().record_error(error_type, error_message, context)


def propose_new_pattern(error_type: str, error_message: str):
    """Manually propose a new pattern."""
    learner = get_learner()
    learner._create_proposal(error_type, error_message)


