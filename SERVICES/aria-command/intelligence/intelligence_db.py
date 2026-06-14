"""
INTELLIGENCE DATABASE
======================

SQLite storage for the Level 10 Intelligence System.

Tables:
- failures: Records of all system failures
- fixes: Known fix patterns and their success rates
- patterns: Detected recurring patterns
- learning_metrics: Meta-learning tracking
- verification_history: Results of real verification checks
"""

import os
import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("aria.intelligence.db")

# Database location
DB_PATH = os.getenv("INTELLIGENCE_DB_PATH", "/opt/fpai/aria-command/data/intelligence.db")


@dataclass
class FailureRecord:
    """A recorded failure event."""
    id: Optional[int] = None
    timestamp: str = ""
    service: str = ""
    symptom: str = ""
    root_cause: str = ""
    root_cause_confidence: float = 0.0
    fix_applied: str = ""
    fix_worked: bool = False
    time_to_fix_seconds: int = 0
    similar_failure_id: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FixRecord:
    """A known fix pattern."""
    id: Optional[int] = None
    pattern: str = ""
    fix_type: str = ""  # config_change, restart, rollback, api_reconnect, etc.
    fix_details: str = ""
    success_count: int = 0
    failure_count: int = 0
    avg_time_seconds: float = 0.0
    last_used: str = ""
    created_at: str = ""
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class PatternRecord:
    """A detected recurring pattern."""
    id: Optional[int] = None
    pattern_type: str = ""  # temporal, sequence, config, correlation
    description: str = ""
    trigger_conditions: str = ""  # JSON
    predicted_outcome: str = ""
    confidence: float = 0.0
    occurrence_count: int = 0
    last_triggered: str = ""
    preventive_action: str = ""
    created_at: str = ""


@dataclass
class VerificationRecord:
    """A verification check result."""
    id: Optional[int] = None
    timestamp: str = ""
    service: str = ""
    check_type: str = ""  # health, functional, config
    passed: bool = False
    details: str = ""
    response_time_ms: float = 0.0


class IntelligenceDB:
    """
    SQLite database for intelligence system.
    
    Provides persistent storage for:
    - Failure history (for learning)
    - Fix patterns (for known solutions)
    - Detected patterns (for prediction)
    - Verification history (for trends)
    - Learning metrics (for meta-learning)
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db_directory()
        self._init_db()
        logger.info(f"IntelligenceDB initialized at {self.db_path}")
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Failures table: Records of all system failures
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    symptom TEXT NOT NULL,
                    root_cause TEXT,
                    root_cause_confidence REAL DEFAULT 0.0,
                    fix_applied TEXT,
                    fix_worked BOOLEAN DEFAULT FALSE,
                    time_to_fix_seconds INTEGER DEFAULT 0,
                    similar_failure_id INTEGER,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (similar_failure_id) REFERENCES failures(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_failures_service ON failures(service);
                CREATE INDEX IF NOT EXISTS idx_failures_timestamp ON failures(timestamp);
                CREATE INDEX IF NOT EXISTS idx_failures_symptom ON failures(symptom);
                
                -- Fixes table: Known fix patterns
                CREATE TABLE IF NOT EXISTS fixes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL UNIQUE,
                    fix_type TEXT NOT NULL,
                    fix_details TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    avg_time_seconds REAL DEFAULT 0.0,
                    last_used TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_fixes_pattern ON fixes(pattern);
                CREATE INDEX IF NOT EXISTS idx_fixes_success ON fixes(success_count);
                
                -- Patterns table: Detected recurring patterns
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    trigger_conditions TEXT NOT NULL,
                    predicted_outcome TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    occurrence_count INTEGER DEFAULT 0,
                    last_triggered TEXT,
                    preventive_action TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
                CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence);
                
                -- Verification history
                CREATE TABLE IF NOT EXISTS verification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    check_type TEXT NOT NULL,
                    passed BOOLEAN NOT NULL,
                    details TEXT,
                    response_time_ms REAL DEFAULT 0.0
                );
                
                CREATE INDEX IF NOT EXISTS idx_verification_service ON verification_history(service);
                CREATE INDEX IF NOT EXISTS idx_verification_timestamp ON verification_history(timestamp);
                
                -- Learning metrics (for meta-learning)
                CREATE TABLE IF NOT EXISTS learning_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    context TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_metrics_name ON learning_metrics(metric_name);
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON learning_metrics(timestamp);
                
                -- Config snapshots (for drift detection)
                CREATE TABLE IF NOT EXISTS config_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    config_key TEXT NOT NULL,
                    config_value TEXT,
                    is_valid BOOLEAN DEFAULT TRUE,
                    validation_error TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_config_key ON config_snapshots(config_key);
            """)
            logger.info("Intelligence database schema initialized")
    
    # ========================================================================
    # FAILURE OPERATIONS
    # ========================================================================
    
    def record_failure(self, failure: FailureRecord) -> int:
        """Record a failure event. Returns the failure ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO failures 
                (timestamp, service, symptom, root_cause, root_cause_confidence,
                 fix_applied, fix_worked, time_to_fix_seconds, similar_failure_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                failure.timestamp or datetime.now().isoformat(),
                failure.service,
                failure.symptom,
                failure.root_cause,
                failure.root_cause_confidence,
                failure.fix_applied,
                failure.fix_worked,
                failure.time_to_fix_seconds,
                failure.similar_failure_id,
                json.dumps(failure.metadata or {})
            ))
            return cursor.lastrowid
    
    def get_recent_failures(self, days: int = 30, service: str = None) -> List[FailureRecord]:
        """Get failures from the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            if service:
                rows = conn.execute("""
                    SELECT * FROM failures 
                    WHERE timestamp > ? AND service = ?
                    ORDER BY timestamp DESC
                """, (cutoff, service)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM failures 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (cutoff,)).fetchall()
            
            return [self._row_to_failure(row) for row in rows]
    
    def find_similar_failures(self, symptom: str, limit: int = 5) -> List[FailureRecord]:
        """Find failures with similar symptoms using keyword matching."""
        # Extract keywords from symptom
        keywords = [w.lower() for w in symptom.split() if len(w) > 3]
        
        with self._get_connection() as conn:
            # Simple keyword matching (could be upgraded to vector similarity)
            all_failures = conn.execute("""
                SELECT * FROM failures 
                WHERE fix_worked = TRUE
                ORDER BY timestamp DESC
                LIMIT 100
            """).fetchall()
            
            # Score by keyword overlap
            scored = []
            for row in all_failures:
                failure = self._row_to_failure(row)
                symptom_words = failure.symptom.lower().split()
                overlap = sum(1 for k in keywords if k in symptom_words)
                if overlap > 0:
                    scored.append((overlap, failure))
            
            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)
            return [f for _, f in scored[:limit]]
    
    def _row_to_failure(self, row: sqlite3.Row) -> FailureRecord:
        """Convert a database row to a FailureRecord."""
        return FailureRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            service=row["service"],
            symptom=row["symptom"],
            root_cause=row["root_cause"] or "",
            root_cause_confidence=row["root_cause_confidence"] or 0.0,
            fix_applied=row["fix_applied"] or "",
            fix_worked=bool(row["fix_worked"]),
            time_to_fix_seconds=row["time_to_fix_seconds"] or 0,
            similar_failure_id=row["similar_failure_id"],
            metadata=json.loads(row["metadata"] or "{}")
        )
    
    # ========================================================================
    # FIX OPERATIONS
    # ========================================================================
    
    def record_fix(self, fix: FixRecord) -> int:
        """Record or update a fix pattern."""
        with self._get_connection() as conn:
            # Check if pattern exists
            existing = conn.execute(
                "SELECT * FROM fixes WHERE pattern = ?",
                (fix.pattern,)
            ).fetchone()
            
            if existing:
                # Update existing
                conn.execute("""
                    UPDATE fixes SET
                        success_count = success_count + ?,
                        failure_count = failure_count + ?,
                        avg_time_seconds = (avg_time_seconds * (success_count + failure_count) + ?) / 
                                          (success_count + failure_count + 1),
                        last_used = ?
                    WHERE pattern = ?
                """, (
                    1 if fix.success_count > 0 else 0,
                    1 if fix.failure_count > 0 else 0,
                    fix.avg_time_seconds,
                    datetime.now().isoformat(),
                    fix.pattern
                ))
                return existing["id"]
            else:
                # Insert new
                cursor = conn.execute("""
                    INSERT INTO fixes 
                    (pattern, fix_type, fix_details, success_count, failure_count, 
                     avg_time_seconds, last_used, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fix.pattern,
                    fix.fix_type,
                    fix.fix_details,
                    fix.success_count,
                    fix.failure_count,
                    fix.avg_time_seconds,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                return cursor.lastrowid
    
    def get_best_fix(self, pattern: str) -> Optional[FixRecord]:
        """Get the best fix for a pattern based on success rate."""
        with self._get_connection() as conn:
            # Exact match first
            row = conn.execute(
                "SELECT * FROM fixes WHERE pattern = ?",
                (pattern,)
            ).fetchone()
            
            if row:
                return self._row_to_fix(row)
            
            # Keyword match fallback
            keywords = [w.lower() for w in pattern.split() if len(w) > 3]
            if not keywords:
                return None
            
            all_fixes = conn.execute("""
                SELECT * FROM fixes 
                WHERE success_count > failure_count
                ORDER BY (success_count * 1.0 / (success_count + failure_count + 1)) DESC
                LIMIT 20
            """).fetchall()
            
            for row in all_fixes:
                fix = self._row_to_fix(row)
                pattern_words = fix.pattern.lower().split()
                if any(k in pattern_words for k in keywords):
                    return fix
            
            return None
    
    def get_fix_success_rate(self) -> float:
        """Get overall fix success rate."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    SUM(success_count) as total_success,
                    SUM(failure_count) as total_failure
                FROM fixes
            """).fetchone()
            
            total = (row["total_success"] or 0) + (row["total_failure"] or 0)
            return (row["total_success"] or 0) / total if total > 0 else 0.0
    
    def _row_to_fix(self, row: sqlite3.Row) -> FixRecord:
        """Convert a database row to a FixRecord."""
        return FixRecord(
            id=row["id"],
            pattern=row["pattern"],
            fix_type=row["fix_type"],
            fix_details=row["fix_details"],
            success_count=row["success_count"],
            failure_count=row["failure_count"],
            avg_time_seconds=row["avg_time_seconds"] or 0.0,
            last_used=row["last_used"] or "",
            created_at=row["created_at"] or ""
        )
    
    # ========================================================================
    # PATTERN OPERATIONS
    # ========================================================================
    
    def record_pattern(self, pattern: PatternRecord) -> int:
        """Record a detected pattern."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO patterns 
                (pattern_type, description, trigger_conditions, predicted_outcome,
                 confidence, occurrence_count, last_triggered, preventive_action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_type,
                pattern.description,
                pattern.trigger_conditions,
                pattern.predicted_outcome,
                pattern.confidence,
                pattern.occurrence_count,
                pattern.last_triggered or datetime.now().isoformat(),
                pattern.preventive_action,
                datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def get_patterns(self, pattern_type: str = None, min_confidence: float = 0.5) -> List[PatternRecord]:
        """Get patterns above a confidence threshold."""
        with self._get_connection() as conn:
            if pattern_type:
                rows = conn.execute("""
                    SELECT * FROM patterns 
                    WHERE pattern_type = ? AND confidence >= ?
                    ORDER BY confidence DESC
                """, (pattern_type, min_confidence)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM patterns 
                    WHERE confidence >= ?
                    ORDER BY confidence DESC
                """, (min_confidence,)).fetchall()
            
            return [self._row_to_pattern(row) for row in rows]
    
    def update_pattern_occurrence(self, pattern_id: int):
        """Update a pattern when it's triggered."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE patterns SET
                    occurrence_count = occurrence_count + 1,
                    last_triggered = ?,
                    confidence = MIN(0.99, confidence + 0.01)
                WHERE id = ?
            """, (datetime.now().isoformat(), pattern_id))
    
    def _row_to_pattern(self, row: sqlite3.Row) -> PatternRecord:
        """Convert a database row to a PatternRecord."""
        return PatternRecord(
            id=row["id"],
            pattern_type=row["pattern_type"],
            description=row["description"],
            trigger_conditions=row["trigger_conditions"],
            predicted_outcome=row["predicted_outcome"],
            confidence=row["confidence"],
            occurrence_count=row["occurrence_count"],
            last_triggered=row["last_triggered"] or "",
            preventive_action=row["preventive_action"] or "",
            created_at=row["created_at"] or ""
        )
    
    # ========================================================================
    # VERIFICATION OPERATIONS
    # ========================================================================
    
    def record_verification(self, verification: VerificationRecord):
        """Record a verification result."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO verification_history 
                (timestamp, service, check_type, passed, details, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                verification.timestamp or datetime.now().isoformat(),
                verification.service,
                verification.check_type,
                verification.passed,
                verification.details,
                verification.response_time_ms
            ))
    
    def get_verification_trend(self, service: str, hours: int = 24) -> Dict[str, Any]:
        """Get verification trend for a service."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed,
                    AVG(response_time_ms) as avg_response_time
                FROM verification_history
                WHERE service = ? AND timestamp > ?
            """, (service, cutoff)).fetchone()
            
            total = rows["total"] or 0
            passed = rows["passed"] or 0
            
            return {
                "service": service,
                "hours": hours,
                "total_checks": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": passed / total if total > 0 else 0.0,
                "avg_response_time_ms": rows["avg_response_time"] or 0.0
            }
    
    # ========================================================================
    # LEARNING METRICS
    # ========================================================================
    
    def record_metric(self, name: str, value: float, context: str = None):
        """Record a learning metric."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO learning_metrics (timestamp, metric_name, metric_value, context)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), name, value, context))
    
    def get_metric_trend(self, name: str, days: int = 7) -> List[Tuple[str, float]]:
        """Get metric trend over time."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT timestamp, metric_value 
                FROM learning_metrics
                WHERE metric_name = ? AND timestamp > ?
                ORDER BY timestamp
            """, (name, cutoff)).fetchall()
            
            return [(row["timestamp"], row["metric_value"]) for row in rows]
    
    # ========================================================================
    # CONFIG SNAPSHOTS
    # ========================================================================
    
    def record_config_snapshot(self, key: str, value: str, is_valid: bool, error: str = None):
        """Record a config value snapshot."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO config_snapshots (timestamp, config_key, config_value, is_valid, validation_error)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), key, value, is_valid, error))
    
    def get_config_history(self, key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get config history for a key."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM config_snapshots
                WHERE config_key = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (key, limit)).fetchall()
            
            return [dict(row) for row in rows]
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_intelligence_stats(self) -> Dict[str, Any]:
        """Get overall intelligence system statistics."""
        with self._get_connection() as conn:
            # Failure stats
            failure_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_failures,
                    SUM(CASE WHEN fix_worked THEN 1 ELSE 0 END) as fixed_failures,
                    AVG(time_to_fix_seconds) as avg_fix_time
                FROM failures
            """).fetchone()
            
            # Fix stats
            fix_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_fix_patterns,
                    SUM(success_count) as total_successes,
                    SUM(failure_count) as total_fix_failures
                FROM fixes
            """).fetchone()
            
            # Pattern stats
            pattern_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_patterns,
                    AVG(confidence) as avg_confidence
                FROM patterns
            """).fetchone()
            
            return {
                "failures": {
                    "total": failure_stats["total_failures"] or 0,
                    "fixed": failure_stats["fixed_failures"] or 0,
                    "fix_rate": (failure_stats["fixed_failures"] or 0) / 
                               (failure_stats["total_failures"] or 1),
                    "avg_fix_time_seconds": failure_stats["avg_fix_time"] or 0
                },
                "fixes": {
                    "patterns_known": fix_stats["total_fix_patterns"] or 0,
                    "total_applications": (fix_stats["total_successes"] or 0) + 
                                         (fix_stats["total_fix_failures"] or 0),
                    "success_rate": self.get_fix_success_rate()
                },
                "patterns": {
                    "total": pattern_stats["total_patterns"] or 0,
                    "avg_confidence": pattern_stats["avg_confidence"] or 0
                }
            }


# ============================================================================
# SINGLETON
# ============================================================================

_db: Optional[IntelligenceDB] = None


def get_intelligence_db() -> IntelligenceDB:
    """Get or create the intelligence database instance."""
    global _db
    if _db is None:
        _db = IntelligenceDB()
    return _db









