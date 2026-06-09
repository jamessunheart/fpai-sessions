#!/usr/bin/env python3
"""
ARIA ASCENSION - A/B TESTING FRAMEWORK
======================================

Test changes safely:
- Deploy changes to 20% of interactions
- Measure: response time, success rate, follow-up queries
- Auto-promote or rollback based on data

Enables data-driven self-improvement.
"""

import os
import json
import random
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.ascension.ab")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("ASCENSION_DB", "/opt/fpai/aria-command/state/ascension.db")

# A/B test settings
DEFAULT_TEST_PERCENTAGE = float(os.getenv("AB_TEST_PERCENTAGE", "0.20"))
MIN_SAMPLES_FOR_DECISION = int(os.getenv("AB_MIN_SAMPLES", "20"))
SIGNIFICANCE_THRESHOLD = float(os.getenv("AB_SIGNIFICANCE", "0.05"))


class TestStatus(str, Enum):
    """Status of an A/B test."""
    RUNNING = "running"
    COMPLETED = "completed"
    PROMOTED = "promoted"     # Variant won, now default
    ROLLED_BACK = "rolled_back"


class TestMetric(str, Enum):
    """Metrics to track in A/B tests."""
    RESPONSE_TIME = "response_time"
    SUCCESS_RATE = "success_rate"
    FOLLOWUP_RATE = "followup_rate"
    USER_SATISFACTION = "user_satisfaction"


@dataclass
class ABVariant:
    """A variant in an A/B test."""
    name: str  # "control" or "treatment"
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "config": self.config
        }


@dataclass
class ABTest:
    """An A/B test."""
    id: str
    name: str
    description: str
    control: ABVariant
    treatment: ABVariant
    traffic_percentage: float  # % of traffic to treatment
    primary_metric: TestMetric
    
    status: TestStatus = TestStatus.RUNNING
    created_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime = None
    
    # Results
    control_samples: int = 0
    treatment_samples: int = 0
    winner: str = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "control": self.control.to_dict(),
            "treatment": self.treatment.to_dict(),
            "traffic_percentage": self.traffic_percentage,
            "primary_metric": self.primary_metric.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "control_samples": self.control_samples,
            "treatment_samples": self.treatment_samples,
            "winner": self.winner
        }


@dataclass
class TestResult:
    """Results of an A/B test."""
    test_id: str
    control_metrics: Dict[str, float]
    treatment_metrics: Dict[str, float]
    improvement_pct: float
    is_significant: bool
    recommended_action: str
    
    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "control_metrics": self.control_metrics,
            "treatment_metrics": self.treatment_metrics,
            "improvement_pct": self.improvement_pct,
            "is_significant": self.is_significant,
            "recommended_action": self.recommended_action
        }


AB_SCHEMA = """
CREATE TABLE IF NOT EXISTS ab_tests (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    control_config TEXT,
    treatment_config TEXT,
    traffic_percentage REAL,
    primary_metric TEXT,
    status TEXT DEFAULT 'running',
    created_at TEXT NOT NULL,
    ended_at TEXT,
    winner TEXT
);

CREATE TABLE IF NOT EXISTS ab_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    response_time_ms REAL,
    success INTEGER,
    had_followup INTEGER,
    satisfaction_signal INTEGER,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_abs_test ON ab_samples(test_id);
CREATE INDEX IF NOT EXISTS idx_abs_variant ON ab_samples(test_id, variant);
CREATE INDEX IF NOT EXISTS idx_abs_timestamp ON ab_samples(timestamp);
"""


# ============================================================================
# A/B TESTER
# ============================================================================

class ABTester:
    """
    A/B testing framework for safe experimentation.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._active_tests: Dict[str, ABTest] = {}
        self._init_db()
        self._load_active_tests()
    
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
            cursor.executescript(AB_SCHEMA)
        
        logger.info(f"A/B tester initialized: {self.db_path}")
    
    def _load_active_tests(self):
        """Load active tests from database."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM ab_tests WHERE status = 'running'
            """)
            
            for row in cursor.fetchall():
                test = ABTest(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    control=ABVariant("control", "Control", json.loads(row["control_config"] or "{}")),
                    treatment=ABVariant("treatment", "Treatment", json.loads(row["treatment_config"] or "{}")),
                    traffic_percentage=row["traffic_percentage"],
                    primary_metric=TestMetric(row["primary_metric"]),
                    status=TestStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"])
                )
                self._active_tests[test.id] = test
    
    # ========================================================================
    # TEST MANAGEMENT
    # ========================================================================
    
    def create_test(
        self,
        test_id: str,
        name: str,
        description: str,
        control_config: Dict,
        treatment_config: Dict,
        primary_metric: TestMetric = TestMetric.SUCCESS_RATE,
        traffic_percentage: float = DEFAULT_TEST_PERCENTAGE
    ) -> ABTest:
        """Create a new A/B test."""
        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            control=ABVariant("control", "Control", control_config),
            treatment=ABVariant("treatment", "Treatment", treatment_config),
            traffic_percentage=traffic_percentage,
            primary_metric=primary_metric
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO ab_tests
                (id, name, description, control_config, treatment_config, 
                 traffic_percentage, primary_metric, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test.id, test.name, test.description,
                json.dumps(test.control.config),
                json.dumps(test.treatment.config),
                test.traffic_percentage,
                test.primary_metric.value,
                test.status.value,
                test.created_at.isoformat()
            ))
        
        self._active_tests[test.id] = test
        logger.info(f"Created A/B test: {test.name}")
        
        return test
    
    def get_test(self, test_id: str) -> Optional[ABTest]:
        """Get a test by ID."""
        return self._active_tests.get(test_id)
    
    def end_test(self, test_id: str, winner: str = None):
        """End a test."""
        if test_id not in self._active_tests:
            return
        
        test = self._active_tests[test_id]
        test.status = TestStatus.COMPLETED
        test.ended_at = datetime.now()
        test.winner = winner
        
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE ab_tests 
                SET status = ?, ended_at = ?, winner = ?
                WHERE id = ?
            """, (test.status.value, test.ended_at.isoformat(), winner, test_id))
        
        del self._active_tests[test_id]
        logger.info(f"Ended A/B test: {test.name}, winner: {winner}")
    
    # ========================================================================
    # VARIANT SELECTION
    # ========================================================================
    
    def get_variant(self, test_id: str) -> str:
        """
        Get variant for a new interaction.
        Returns "control" or "treatment".
        """
        test = self._active_tests.get(test_id)
        if not test:
            return "control"
        
        # Random selection based on traffic percentage
        if random.random() < test.traffic_percentage:
            return "treatment"
        return "control"
    
    def get_config_for_variant(self, test_id: str, variant: str) -> Dict:
        """Get configuration for a specific variant."""
        test = self._active_tests.get(test_id)
        if not test:
            return {}
        
        if variant == "treatment":
            return test.treatment.config
        return test.control.config
    
    def get_active_variant_config(self, test_id: str) -> tuple[str, Dict]:
        """
        Get variant and its config for a new interaction.
        Returns (variant_name, config_dict).
        """
        variant = self.get_variant(test_id)
        config = self.get_config_for_variant(test_id, variant)
        return variant, config
    
    # ========================================================================
    # SAMPLE RECORDING
    # ========================================================================
    
    def record_sample(
        self,
        test_id: str,
        variant: str,
        response_time_ms: float = None,
        success: bool = True,
        had_followup: bool = False,
        satisfaction_signal: int = None,  # -1, 0, 1
        metadata: Dict = None
    ):
        """Record a sample for an A/B test."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO ab_samples
                (test_id, variant, timestamp, response_time_ms, success, had_followup, satisfaction_signal, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id, variant, datetime.now().isoformat(),
                response_time_ms, 1 if success else 0,
                1 if had_followup else 0, satisfaction_signal,
                json.dumps(metadata or {})
            ))
        
        # Update sample counts
        if test_id in self._active_tests:
            test = self._active_tests[test_id]
            if variant == "control":
                test.control_samples += 1
            else:
                test.treatment_samples += 1
    
    # ========================================================================
    # ANALYSIS
    # ========================================================================
    
    def analyze_test(self, test_id: str) -> TestResult:
        """Analyze results of an A/B test."""
        with self._cursor() as cursor:
            # Get control metrics
            cursor.execute("""
                SELECT 
                    AVG(response_time_ms) as avg_time,
                    AVG(success) as success_rate,
                    AVG(had_followup) as followup_rate,
                    COUNT(*) as samples
                FROM ab_samples
                WHERE test_id = ? AND variant = 'control'
            """, (test_id,))
            control = cursor.fetchone()
            
            # Get treatment metrics
            cursor.execute("""
                SELECT 
                    AVG(response_time_ms) as avg_time,
                    AVG(success) as success_rate,
                    AVG(had_followup) as followup_rate,
                    COUNT(*) as samples
                FROM ab_samples
                WHERE test_id = ? AND variant = 'treatment'
            """, (test_id,))
            treatment = cursor.fetchone()
        
        control_metrics = {
            "response_time": control["avg_time"] or 0,
            "success_rate": control["success_rate"] or 0,
            "followup_rate": control["followup_rate"] or 0,
            "samples": control["samples"] or 0
        }
        
        treatment_metrics = {
            "response_time": treatment["avg_time"] or 0,
            "success_rate": treatment["success_rate"] or 0,
            "followup_rate": treatment["followup_rate"] or 0,
            "samples": treatment["samples"] or 0
        }
        
        # Calculate improvement for primary metric
        test = self._active_tests.get(test_id)
        primary = test.primary_metric if test else TestMetric.SUCCESS_RATE
        
        if primary == TestMetric.RESPONSE_TIME:
            # Lower is better for response time
            ctrl_val = control_metrics["response_time"]
            treat_val = treatment_metrics["response_time"]
            if ctrl_val > 0:
                improvement = (ctrl_val - treat_val) / ctrl_val * 100
            else:
                improvement = 0
        else:
            # Higher is better for other metrics
            ctrl_val = control_metrics.get(primary.value, 0)
            treat_val = treatment_metrics.get(primary.value, 0)
            if ctrl_val > 0:
                improvement = (treat_val - ctrl_val) / ctrl_val * 100
            else:
                improvement = 0
        
        # Check statistical significance (simplified)
        total_samples = control_metrics["samples"] + treatment_metrics["samples"]
        is_significant = (
            total_samples >= MIN_SAMPLES_FOR_DECISION and
            abs(improvement) > 5  # At least 5% difference
        )
        
        # Recommendation
        if not is_significant:
            if total_samples < MIN_SAMPLES_FOR_DECISION:
                recommendation = f"Need more samples ({total_samples}/{MIN_SAMPLES_FOR_DECISION})"
            else:
                recommendation = "No significant difference - keep running or end test"
        elif improvement > 0:
            recommendation = f"Treatment wins by {improvement:.1f}% - promote"
        else:
            recommendation = f"Control wins by {-improvement:.1f}% - rollback treatment"
        
        return TestResult(
            test_id=test_id,
            control_metrics=control_metrics,
            treatment_metrics=treatment_metrics,
            improvement_pct=improvement,
            is_significant=is_significant,
            recommended_action=recommendation
        )
    
    def auto_decide(self, test_id: str) -> tuple[str, str]:
        """
        Automatically decide test outcome based on results.
        Returns (action, reason).
        Actions: "continue", "promote", "rollback"
        """
        result = self.analyze_test(test_id)
        
        if not result.is_significant:
            return "continue", result.recommended_action
        
        if result.improvement_pct > 5:
            # Treatment is better
            self.end_test(test_id, winner="treatment")
            return "promote", f"Treatment improved by {result.improvement_pct:.1f}%"
        elif result.improvement_pct < -5:
            # Control is better
            self.end_test(test_id, winner="control")
            return "rollback", f"Treatment degraded by {-result.improvement_pct:.1f}%"
        else:
            # No meaningful difference
            return "continue", "Difference not meaningful enough"
    
    # ========================================================================
    # STATS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get A/B testing statistics."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM ab_tests WHERE status = 'running'")
            active = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT winner, COUNT(*) as count
                FROM ab_tests
                WHERE status = 'completed' OR status = 'promoted'
                GROUP BY winner
            """)
            outcomes = {row["winner"]: row["count"] for row in cursor.fetchall()}
        
        return {
            "active_tests": active,
            "completed_tests": sum(outcomes.values()),
            "treatment_wins": outcomes.get("treatment", 0),
            "control_wins": outcomes.get("control", 0),
            "active_test_ids": list(self._active_tests.keys())
        }


# ============================================================================
# SINGLETON & CONVENIENCE
# ============================================================================

_tester: Optional[ABTester] = None


def get_ab_tester() -> ABTester:
    """Get global A/B tester."""
    global _tester
    if _tester is None:
        _tester = ABTester()
    return _tester


def create_ab_test(test_id: str, name: str, **kwargs) -> ABTest:
    """Create a new A/B test."""
    return get_ab_tester().create_test(test_id, name, **kwargs)


def get_variant_config(test_id: str) -> tuple[str, Dict]:
    """Get variant and config for an interaction."""
    return get_ab_tester().get_active_variant_config(test_id)


def record_ab_sample(test_id: str, variant: str, **kwargs):
    """Record an A/B test sample."""
    get_ab_tester().record_sample(test_id, variant, **kwargs)


