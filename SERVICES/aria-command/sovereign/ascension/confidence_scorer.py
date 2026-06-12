#!/usr/bin/env python3
"""
ARIA ASCENSION - CONFIDENCE SCORER
==================================

Score proposed changes for autonomous execution:
- Factors: Similar changes succeeded, risk level, reversibility
- Threshold: Auto-apply if score > 90 AND risk = "low"

Enables self-improvement without human approval for safe changes.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.confidence")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")

# Auto-apply thresholds
AUTO_APPLY_CONFIDENCE = float(os.getenv("AUTO_APPLY_CONFIDENCE", "0.90"))
AUTO_APPLY_MAX_RISK = os.getenv("AUTO_APPLY_MAX_RISK", "low")


class RiskLevel(str, Enum):
    """Risk level of a change."""
    LOW = "low"           # Can auto-apply
    MEDIUM = "medium"     # Needs review
    HIGH = "high"         # Needs explicit approval
    CRITICAL = "critical" # Never auto-apply


class ChangeType(str, Enum):
    """Type of change being proposed."""
    PROMPT_UPDATE = "prompt_update"     # System prompt changes
    CONFIG_UPDATE = "config_update"     # Configuration changes
    CODE_REFACTOR = "code_refactor"     # Code improvements
    NEW_FEATURE = "new_feature"         # New functionality
    BUG_FIX = "bug_fix"                 # Bug fixes
    PERFORMANCE = "performance"         # Performance optimization
    RESPONSE_STYLE = "response_style"   # Response format changes


@dataclass
class ConfidenceScore:
    """Confidence score for a proposed change."""
    change_id: str
    change_type: ChangeType
    
    # Scores (0-1)
    similarity_score: float      # Similar changes succeeded before
    reversibility_score: float   # How easy to undo
    scope_score: float           # Limited vs broad impact
    test_coverage_score: float   # Has tests/verification
    
    # Overall
    total_score: float
    risk_level: RiskLevel
    
    # Decision
    can_auto_apply: bool
    reason: str
    
    # Context
    similar_changes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "similarity_score": self.similarity_score,
            "reversibility_score": self.reversibility_score,
            "scope_score": self.scope_score,
            "test_coverage_score": self.test_coverage_score,
            "total_score": self.total_score,
            "risk_level": self.risk_level.value,
            "can_auto_apply": self.can_auto_apply,
            "reason": self.reason,
            "similar_changes": self.similar_changes
        }


@dataclass
class ProposedChange:
    """A proposed change to be scored."""
    id: str
    change_type: ChangeType
    description: str
    files_affected: List[str]
    estimated_lines: int
    has_tests: bool
    has_rollback: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


CONFIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS change_history (
    id TEXT PRIMARY KEY,
    change_type TEXT NOT NULL,
    description TEXT,
    files_affected TEXT,
    applied_at TEXT,
    success INTEGER,
    rolled_back INTEGER DEFAULT 0,
    metrics_before TEXT,
    metrics_after TEXT
);

CREATE TABLE IF NOT EXISTS confidence_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    score REAL,
    risk_level TEXT,
    auto_applied INTEGER,
    outcome TEXT
);

CREATE INDEX IF NOT EXISTS idx_ch_type ON change_history(change_type);
CREATE INDEX IF NOT EXISTS idx_ch_success ON change_history(success);
CREATE INDEX IF NOT EXISTS idx_cd_change ON confidence_decisions(change_id);
"""


# ============================================================================
# RISK ASSESSMENT
# ============================================================================

# Files that should never be auto-modified
CRITICAL_FILES = [
    "brain/opus_brain.py",      # Core brain - too risky
    "brain/opus_router.py",     # Model routing
    "access/terminal.py",       # Security-sensitive
    ".env",                      # Credentials
    "main.py",                   # Entry point
]

# File patterns and their risk levels
FILE_RISK_PATTERNS = {
    RiskLevel.CRITICAL: [
        r".*\.env$",
        r".*secrets.*",
        r".*credentials.*",
        r".*/access/.*",
    ],
    RiskLevel.HIGH: [
        r".*/brain/opus.*",
        r".*/main\.py$",
        r".*/bot\.py$",
    ],
    RiskLevel.MEDIUM: [
        r".*/tools\.py$",
        r".*/config.*",
    ],
    RiskLevel.LOW: [
        r".*/proactive/.*",
        r".*/evolution/.*",
        r".*/ascension/.*",
    ]
}

# Change types and their base risk
CHANGE_TYPE_RISK = {
    ChangeType.PROMPT_UPDATE: RiskLevel.MEDIUM,
    ChangeType.CONFIG_UPDATE: RiskLevel.MEDIUM,
    ChangeType.CODE_REFACTOR: RiskLevel.MEDIUM,
    ChangeType.NEW_FEATURE: RiskLevel.HIGH,
    ChangeType.BUG_FIX: RiskLevel.LOW,
    ChangeType.PERFORMANCE: RiskLevel.LOW,
    ChangeType.RESPONSE_STYLE: RiskLevel.LOW,
}


# ============================================================================
# CONFIDENCE SCORER
# ============================================================================

class ConfidenceScorer:
    """
    Scores proposed changes for autonomous execution.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database."""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self._cursor() as cursor:
            cursor.executescript(CONFIDENCE_SCHEMA)
        
        logger.info(f"Confidence scorer initialized: {self.db_path}")
    
    # ========================================================================
    # SCORING
    # ========================================================================
    
    def score(self, change: ProposedChange) -> ConfidenceScore:
        """
        Score a proposed change.
        
        Returns ConfidenceScore with decision on auto-apply.
        """
        # Calculate individual scores
        similarity = self._calculate_similarity_score(change)
        reversibility = self._calculate_reversibility_score(change)
        scope = self._calculate_scope_score(change)
        test_coverage = self._calculate_test_coverage_score(change)
        
        # Calculate total (weighted average)
        weights = {
            "similarity": 0.35,
            "reversibility": 0.25,
            "scope": 0.25,
            "test_coverage": 0.15
        }
        
        total = (
            similarity * weights["similarity"] +
            reversibility * weights["reversibility"] +
            scope * weights["scope"] +
            test_coverage * weights["test_coverage"]
        )
        
        # Determine risk level
        risk = self._assess_risk(change)
        
        # Determine if can auto-apply
        can_auto, reason = self._can_auto_apply(total, risk, change)
        
        # Get similar successful changes
        similar = self._get_similar_changes(change)
        
        score = ConfidenceScore(
            change_id=change.id,
            change_type=change.change_type,
            similarity_score=similarity,
            reversibility_score=reversibility,
            scope_score=scope,
            test_coverage_score=test_coverage,
            total_score=total,
            risk_level=risk,
            can_auto_apply=can_auto,
            reason=reason,
            similar_changes=similar
        )
        
        # Record decision
        self._record_decision(score)
        
        return score
    
    def _calculate_similarity_score(self, change: ProposedChange) -> float:
        """Score based on similar past changes."""
        with self._cursor() as cursor:
            # Find similar changes
            cursor.execute("""
                SELECT success, COUNT(*) as count
                FROM change_history
                WHERE change_type = ?
                GROUP BY success
            """, (change.change_type.value,))
            
            results = {row["success"]: row["count"] for row in cursor.fetchall()}
        
        total = sum(results.values())
        if total == 0:
            return 0.5  # No history, neutral
        
        successes = results.get(1, 0)
        success_rate = successes / total
        
        # Boost confidence if many successful similar changes
        if total > 10:
            return min(0.95, success_rate + 0.1)
        elif total > 5:
            return success_rate
        else:
            return success_rate * 0.8  # Reduce confidence for limited data
    
    def _calculate_reversibility_score(self, change: ProposedChange) -> float:
        """Score based on how easy it is to undo."""
        score = 0.5  # Base score
        
        # Has explicit rollback plan
        if change.has_rollback:
            score += 0.3
        
        # Fewer files = easier to revert
        file_count = len(change.files_affected)
        if file_count <= 1:
            score += 0.2
        elif file_count <= 3:
            score += 0.1
        else:
            score -= 0.1
        
        # Fewer lines = easier to revert
        if change.estimated_lines <= 20:
            score += 0.1
        elif change.estimated_lines <= 50:
            pass
        else:
            score -= 0.1
        
        return max(0, min(1, score))
    
    def _calculate_scope_score(self, change: ProposedChange) -> float:
        """Score based on scope of change."""
        score = 0.8  # Start optimistic
        
        # Penalize broad changes
        file_count = len(change.files_affected)
        if file_count > 5:
            score -= 0.3
        elif file_count > 3:
            score -= 0.1
        
        # Check for critical files
        for file in change.files_affected:
            if any(cf in file for cf in CRITICAL_FILES):
                score -= 0.4
                break
        
        # Line count impact
        if change.estimated_lines > 100:
            score -= 0.2
        elif change.estimated_lines > 50:
            score -= 0.1
        
        return max(0, min(1, score))
    
    def _calculate_test_coverage_score(self, change: ProposedChange) -> float:
        """Score based on test coverage."""
        if change.has_tests:
            return 0.9
        
        # Bug fixes and performance changes are often safe without explicit tests
        if change.change_type in [ChangeType.BUG_FIX, ChangeType.PERFORMANCE]:
            return 0.6
        
        return 0.4
    
    def _assess_risk(self, change: ProposedChange) -> RiskLevel:
        """Assess overall risk level."""
        import re
        
        # Start with change type risk
        base_risk = CHANGE_TYPE_RISK.get(change.change_type, RiskLevel.MEDIUM)
        
        # Check files against risk patterns
        max_file_risk = RiskLevel.LOW
        for file in change.files_affected:
            for risk_level, patterns in FILE_RISK_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, file):
                        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
                        if risk_order.index(risk_level) > risk_order.index(max_file_risk):
                            max_file_risk = risk_level
                        break
        
        # Take higher of base risk and file risk
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        if risk_order.index(max_file_risk) > risk_order.index(base_risk):
            return max_file_risk
        
        return base_risk
    
    def _can_auto_apply(
        self,
        total_score: float,
        risk: RiskLevel,
        change: ProposedChange
    ) -> Tuple[bool, str]:
        """Determine if change can be auto-applied."""
        # Critical risk = never auto-apply
        if risk == RiskLevel.CRITICAL:
            return False, "Critical risk level requires human approval"
        
        # High risk = never auto-apply
        if risk == RiskLevel.HIGH:
            return False, "High risk changes require human approval"
        
        # Check risk threshold
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        max_risk_level = RiskLevel(AUTO_APPLY_MAX_RISK)
        
        if risk_order.index(risk) > risk_order.index(max_risk_level):
            return False, f"Risk level {risk.value} exceeds max auto-apply risk {max_risk_level.value}"
        
        # Check confidence threshold
        if total_score < AUTO_APPLY_CONFIDENCE:
            return False, f"Confidence {total_score:.2f} below threshold {AUTO_APPLY_CONFIDENCE}"
        
        # Check for critical files
        for file in change.files_affected:
            if any(cf in file for cf in CRITICAL_FILES):
                return False, f"Change affects critical file: {file}"
        
        return True, f"Score {total_score:.2f} with {risk.value} risk - approved for auto-apply"
    
    def _get_similar_changes(self, change: ProposedChange) -> List[str]:
        """Get IDs of similar successful changes."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT id FROM change_history
                WHERE change_type = ? AND success = 1
                ORDER BY applied_at DESC
                LIMIT 5
            """, (change.change_type.value,))
            
            return [row["id"] for row in cursor.fetchall()]
    
    def _record_decision(self, score: ConfidenceScore):
        """Record the scoring decision."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO confidence_decisions
                (change_id, timestamp, score, risk_level, auto_applied, outcome)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                score.change_id,
                datetime.now().isoformat(),
                score.total_score,
                score.risk_level.value,
                1 if score.can_auto_apply else 0,
                score.reason
            ))
    
    # ========================================================================
    # HISTORY
    # ========================================================================
    
    def record_change_outcome(
        self,
        change_id: str,
        change_type: ChangeType,
        description: str,
        files_affected: List[str],
        success: bool,
        metrics_before: Dict = None,
        metrics_after: Dict = None
    ):
        """Record the outcome of an applied change."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO change_history
                (id, change_type, description, files_affected, applied_at, success, metrics_before, metrics_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change_id,
                change_type.value,
                description,
                json.dumps(files_affected),
                datetime.now().isoformat(),
                1 if success else 0,
                json.dumps(metrics_before or {}),
                json.dumps(metrics_after or {})
            ))
    
    def record_rollback(self, change_id: str):
        """Record that a change was rolled back."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE change_history SET rolled_back = 1 WHERE id = ?
            """, (change_id,))
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scoring statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN rolled_back = 1 THEN 1 ELSE 0 END) as rollbacks
                FROM change_history
            """)
            history = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN auto_applied = 1 THEN 1 ELSE 0 END) as auto_applied
                FROM confidence_decisions
                WHERE timestamp > ?
            """, ((datetime.now() - timedelta(days=7)).isoformat(),))
            decisions = cursor.fetchone()
        
        return {
            "total_changes": history["total"] or 0,
            "success_rate": (history["successes"] or 0) / max(history["total"] or 1, 1),
            "rollback_rate": (history["rollbacks"] or 0) / max(history["total"] or 1, 1),
            "decisions_last_7d": decisions["total"] or 0,
            "auto_apply_rate": (decisions["auto_applied"] or 0) / max(decisions["total"] or 1, 1),
            "auto_apply_threshold": AUTO_APPLY_CONFIDENCE,
            "max_auto_risk": AUTO_APPLY_MAX_RISK
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_scorer: Optional[ConfidenceScorer] = None


def get_confidence_scorer() -> ConfidenceScorer:
    """Get global confidence scorer."""
    global _scorer
    if _scorer is None:
        _scorer = ConfidenceScorer()
    return _scorer


def score_change(change: ProposedChange) -> ConfidenceScore:
    """Score a proposed change."""
    return get_confidence_scorer().score(change)


def can_auto_apply(change: ProposedChange) -> Tuple[bool, str]:
    """Check if change can be auto-applied."""
    score = score_change(change)
    return score.can_auto_apply, score.reason


