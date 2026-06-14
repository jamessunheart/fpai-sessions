"""
Knowledge Base - Persistent storage for healing outcomes and learning
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
from contextlib import contextmanager

from .config import DB_PATH
from .failure_analyzer import FailureType, FailureDiagnosis
from .healing_executor import HealingOutcome, HealingResult

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Persistent storage for healing outcomes and patterns.
    Provides learning capabilities to improve healing over time.
    """
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_conn() as conn:
            conn.executescript("""
                -- Healing outcomes table
                CREATE TABLE IF NOT EXISTS healing_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    result TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    error TEXT,
                    notes TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Failure diagnoses table
                CREATE TABLE IF NOT EXISTS diagnoses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    confidence REAL,
                    evidence TEXT,
                    suggested_fix TEXT,
                    requires_human BOOLEAN,
                    missing_module TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Service health history
                CREATE TABLE IF NOT EXISTS health_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time_ms INTEGER,
                    error TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Recurring patterns
                CREATE TABLE IF NOT EXISTS recurring_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    flagged_for_review BOOLEAN DEFAULT FALSE,
                    UNIQUE(service_name, failure_type)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_outcomes_service ON healing_outcomes(service_name);
                CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp ON healing_outcomes(timestamp);
                CREATE INDEX IF NOT EXISTS idx_diagnoses_service ON diagnoses(service_name);
                CREATE INDEX IF NOT EXISTS idx_health_service ON health_history(service_name);
                CREATE INDEX IF NOT EXISTS idx_patterns_service ON recurring_patterns(service_name);
            """)
            conn.commit()
            logger.info(f"Knowledge base initialized at {self.db_path}")
    
    @contextmanager
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def record_outcome(self, outcome: HealingOutcome):
        """Record a healing outcome."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO healing_outcomes 
                (service_name, failure_type, action_name, result, execution_time_ms, error, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outcome.service_name,
                outcome.failure_type.value,
                outcome.action_name,
                outcome.result.value,
                outcome.execution_time_ms,
                outcome.error,
                outcome.notes,
                outcome.timestamp.isoformat() if outcome.timestamp else datetime.now().isoformat(),
            ))
            conn.commit()
            
            # Update recurring patterns
            self._update_pattern(conn, outcome.service_name, outcome.failure_type.value)
    
    def record_diagnosis(self, diagnosis: FailureDiagnosis):
        """Record a failure diagnosis."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO diagnoses 
                (service_name, failure_type, confidence, evidence, suggested_fix, requires_human, missing_module, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                diagnosis.service_name,
                diagnosis.failure_type.value,
                diagnosis.confidence,
                diagnosis.evidence[:1000] if diagnosis.evidence else None,
                diagnosis.suggested_fix,
                diagnosis.requires_human,
                diagnosis.missing_module,
                diagnosis.timestamp.isoformat() if diagnosis.timestamp else datetime.now().isoformat(),
            ))
            conn.commit()
    
    def record_health_check(self, service_name: str, status: str, response_time_ms: Optional[int] = None, error: Optional[str] = None):
        """Record a health check result."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO health_history (service_name, status, response_time_ms, error)
                VALUES (?, ?, ?, ?)
            """, (service_name, status, response_time_ms, error))
            conn.commit()
    
    def _update_pattern(self, conn, service_name: str, failure_type: str):
        """Update recurring pattern tracking."""
        conn.execute("""
            INSERT INTO recurring_patterns (service_name, failure_type, occurrence_count, last_seen)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(service_name, failure_type) DO UPDATE SET
                occurrence_count = occurrence_count + 1,
                last_seen = CURRENT_TIMESTAMP
        """, (service_name, failure_type))
        
        # Check if pattern should be flagged
        cursor = conn.execute("""
            SELECT occurrence_count FROM recurring_patterns
            WHERE service_name = ? AND failure_type = ?
            AND datetime(first_seen) > datetime('now', '-24 hours')
        """, (service_name, failure_type))
        
        row = cursor.fetchone()
        if row and row['occurrence_count'] >= 5:
            conn.execute("""
                UPDATE recurring_patterns SET flagged_for_review = TRUE
                WHERE service_name = ? AND failure_type = ?
            """, (service_name, failure_type))
    
    def get_success_rate(self, failure_type: str, action_name: str) -> float:
        """Get historical success rate for a failure type and action combination."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes
                FROM healing_outcomes
                WHERE failure_type = ? AND action_name = ?
            """, (failure_type, action_name))
            
            row = cursor.fetchone()
            if row and row['total'] > 0:
                return row['successes'] / row['total']
            return 0.5  # Default to 50% for unknown combinations
    
    def get_best_action_for_failure(self, service_name: str, failure_type: str) -> Optional[str]:
        """Get the historically most successful action for a failure type."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT 
                    action_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes
                FROM healing_outcomes
                WHERE failure_type = ?
                GROUP BY action_name
                HAVING total >= 3
                ORDER BY (successes * 1.0 / total) DESC
                LIMIT 1
            """, (failure_type,))
            
            row = cursor.fetchone()
            if row:
                return row['action_name']
            return None
    
    def get_recent_outcomes(self, limit: int = 50, service_name: Optional[str] = None) -> List[dict]:
        """Get recent healing outcomes."""
        with self._get_conn() as conn:
            if service_name:
                cursor = conn.execute("""
                    SELECT * FROM healing_outcomes
                    WHERE service_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (service_name, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM healing_outcomes
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recurring_patterns(self, flagged_only: bool = False) -> List[dict]:
        """Get recurring failure patterns."""
        with self._get_conn() as conn:
            if flagged_only:
                cursor = conn.execute("""
                    SELECT * FROM recurring_patterns
                    WHERE flagged_for_review = TRUE
                    ORDER BY occurrence_count DESC
                """)
            else:
                cursor = conn.execute("""
                    SELECT * FROM recurring_patterns
                    ORDER BY occurrence_count DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_service_mttr(self, service_name: str) -> Optional[float]:
        """Get Mean Time To Recovery for a service in minutes."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT AVG(execution_time_ms) / 1000.0 / 60.0 as mttr_minutes
                FROM healing_outcomes
                WHERE service_name = ? AND result = 'success'
            """, (service_name,))
            
            row = cursor.fetchone()
            return row['mttr_minutes'] if row else None
    
    def get_stats(self) -> dict:
        """Get overall knowledge base statistics."""
        with self._get_conn() as conn:
            # Total outcomes
            cursor = conn.execute("SELECT COUNT(*) as count FROM healing_outcomes")
            total_outcomes = cursor.fetchone()['count']
            
            # Success rate
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes
                FROM healing_outcomes
            """)
            row = cursor.fetchone()
            success_rate = (row['successes'] / row['total'] * 100) if row['total'] > 0 else 0
            
            # Flagged patterns
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM recurring_patterns
                WHERE flagged_for_review = TRUE
            """)
            flagged_patterns = cursor.fetchone()['count']
            
            # By failure type
            cursor = conn.execute("""
                SELECT 
                    failure_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'success' THEN 1 ELSE 0 END) as successes
                FROM healing_outcomes
                GROUP BY failure_type
            """)
            by_failure_type = {
                row['failure_type']: {
                    "total": row['total'],
                    "successes": row['successes'],
                    "rate": round(row['successes'] / row['total'] * 100, 1) if row['total'] > 0 else 0
                }
                for row in cursor.fetchall()
            }
            
            return {
                "total_healing_attempts": total_outcomes,
                "overall_success_rate": round(success_rate, 1),
                "flagged_patterns": flagged_patterns,
                "by_failure_type": by_failure_type,
            }
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up records older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_conn() as conn:
            conn.execute("""
                DELETE FROM healing_outcomes
                WHERE datetime(timestamp) < datetime(?)
            """, (cutoff.isoformat(),))
            
            conn.execute("""
                DELETE FROM diagnoses
                WHERE datetime(timestamp) < datetime(?)
            """, (cutoff.isoformat(),))
            
            conn.execute("""
                DELETE FROM health_history
                WHERE datetime(timestamp) < datetime(?)
            """, (cutoff.isoformat(),))
            
            conn.commit()
            logger.info(f"Cleaned up records older than {days} days")


# Global knowledge base instance
knowledge_base = KnowledgeBase()











