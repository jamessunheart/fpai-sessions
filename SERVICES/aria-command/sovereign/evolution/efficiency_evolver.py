#!/usr/bin/env python3
"""
ARIA EFFICIENCY EVOLVER
========================

Automatically optimizes Aria's efficiency by:
- Caching frequent lookups
- Routing to cheaper models when appropriate
- Batching similar operations
- Pre-computing predictable requests

Features:
- Response time tracking
- Cost optimization
- Smart model routing
- Cache management
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from collections import defaultdict
import threading
import hashlib

from .interaction_logger import get_interaction_logger, IntentCategory

logger = logging.getLogger("aria.evolution.efficiency")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
CACHE_TTL_HOURS = 24
MAX_CACHE_SIZE_MB = 100


@dataclass
class CachedResponse:
    """A cached response."""
    id: Optional[int] = None
    query_hash: str = ""
    query_pattern: str = ""
    response: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    hit_count: int = 0
    avg_response_time_ms: float = 0
    saved_cost_usd: float = 0


@dataclass
class ModelRoutingRule:
    """A rule for routing to specific models."""
    id: Optional[int] = None
    intent: str = ""
    complexity: str = ""  # simple, moderate, complex
    recommended_model: str = ""
    avg_cost: float = 0
    avg_quality: float = 0  # 0-1 quality score
    sample_count: int = 0


EFFICIENCY_SCHEMA = """
CREATE TABLE IF NOT EXISTS response_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    query_pattern TEXT,
    response TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    hit_count INTEGER DEFAULT 0,
    avg_response_time_ms REAL DEFAULT 0,
    saved_cost_usd REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_rc_hash ON response_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_rc_expires ON response_cache(expires_at);

CREATE TABLE IF NOT EXISTS model_routing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent TEXT NOT NULL,
    complexity TEXT NOT NULL,
    recommended_model TEXT,
    avg_cost REAL DEFAULT 0,
    avg_quality REAL DEFAULT 0,
    sample_count INTEGER DEFAULT 0,
    UNIQUE(intent, complexity)
);

CREATE INDEX IF NOT EXISTS idx_mr_intent ON model_routing(intent);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model TEXT,
    intent TEXT,
    response_time_ms REAL,
    tokens_used INTEGER,
    cost_usd REAL,
    quality_score REAL
);

CREATE INDEX IF NOT EXISTS idx_pm_timestamp ON performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_pm_model ON performance_metrics(model);

CREATE TABLE IF NOT EXISTS optimization_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    optimization_type TEXT,
    description TEXT,
    impact_cost REAL,
    impact_speed_ms REAL
);
"""


# ============================================================================
# COMPLEXITY DETECTION
# ============================================================================

def estimate_complexity(message: str, intent: str) -> str:
    """Estimate query complexity."""
    # Simple heuristics
    words = len(message.split())
    
    # Simple queries
    if words < 10:
        return "simple"
    
    # Complex indicators
    complex_indicators = [
        "explain", "analyze", "compare", "design", "implement",
        "multiple", "comprehensive", "detailed", "all",
        "code", "build", "create"
    ]
    
    if any(ind in message.lower() for ind in complex_indicators):
        return "complex"
    
    # Moderate queries
    if words < 30:
        return "moderate"
    
    return "complex"


# ============================================================================
# MODEL COST TABLE
# ============================================================================

MODEL_COSTS = {
    # Per 1K tokens (input, output)
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.005, 0.015),
    "claude-sonnet-4-20250514": (0.003, 0.015),
    "claude-opus-4-20250514": (0.015, 0.075),
    "ollama/llama3": (0, 0),  # Local, free
}

MODEL_QUALITY = {
    "gpt-4o-mini": 0.7,
    "gpt-4o": 0.9,
    "claude-sonnet-4-20250514": 0.85,
    "claude-opus-4-20250514": 0.95,
    "ollama/llama3": 0.6,
}


# ============================================================================
# EFFICIENCY EVOLVER
# ============================================================================

class EfficiencyEvolver:
    """
    Optimizes Aria's efficiency.
    
    Strategies:
    1. Cache frequent/similar queries
    2. Route to cheaper models when appropriate
    3. Track performance metrics
    4. Suggest optimizations
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._response_cache: Dict[str, CachedResponse] = {}
    
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
            cursor.executescript(EFFICIENCY_SCHEMA)
        logger.info(f"Efficiency evolver initialized: {self.db_path}")
    
    def _hash_query(self, query: str) -> str:
        """Generate a hash for a query."""
        # Normalize: lowercase, remove extra whitespace
        normalized = " ".join(query.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def check_cache(self, query: str) -> Optional[str]:
        """Check if we have a cached response for this query."""
        query_hash = self._hash_query(query)
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM response_cache
                WHERE query_hash = ? AND expires_at > ?
            """, (query_hash, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                # Update hit count
                cursor.execute("""
                    UPDATE response_cache
                    SET hit_count = hit_count + 1
                    WHERE id = ?
                """, (row["id"],))
                
                logger.debug(f"Cache hit for query hash {query_hash[:8]}")
                return row["response"]
        
        return None
    
    def cache_response(
        self,
        query: str,
        response: str,
        response_time_ms: float,
        cost_usd: float,
        ttl_hours: int = CACHE_TTL_HOURS
    ):
        """Cache a response for future use."""
        query_hash = self._hash_query(query)
        
        # Only cache if response is substantial
        if len(response) < 50:
            return
        
        # Extract pattern (first few words)
        pattern = " ".join(query.split()[:5])
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO response_cache (
                    query_hash, query_pattern, response,
                    created_at, expires_at, avg_response_time_ms, saved_cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                pattern,
                response[:10000],  # Truncate
                datetime.now().isoformat(),
                (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
                response_time_ms,
                cost_usd
            ))
    
    def recommend_model(self, message: str, intent: str) -> Tuple[str, float]:
        """
        Recommend a model based on the query.
        
        Returns:
            Tuple of (model_name, expected_cost)
        """
        complexity = estimate_complexity(message, intent)
        
        # Check if we have learned routing
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT recommended_model, avg_cost, avg_quality
                FROM model_routing
                WHERE intent = ? AND complexity = ?
            """, (intent, complexity))
            
            row = cursor.fetchone()
            if row and row["sample_count"] >= 10:
                return row["recommended_model"], row["avg_cost"]
        
        # Default routing
        if complexity == "simple":
            return "gpt-4o-mini", MODEL_COSTS["gpt-4o-mini"][0] * 0.5  # Estimate
        elif complexity == "moderate":
            return "claude-sonnet-4-20250514", MODEL_COSTS["claude-sonnet-4-20250514"][0] * 1.0
        else:
            return "claude-opus-4-20250514", MODEL_COSTS["claude-opus-4-20250514"][0] * 2.0
    
    def record_performance(
        self,
        model: str,
        intent: str,
        response_time_ms: float,
        tokens_used: int,
        cost_usd: float,
        quality_score: float = None
    ):
        """Record performance metrics for learning."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO performance_metrics (
                    timestamp, model, intent, response_time_ms,
                    tokens_used, cost_usd, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                model,
                intent,
                response_time_ms,
                tokens_used,
                cost_usd,
                quality_score
            ))
        
        # Update routing recommendations
        complexity = "simple" if tokens_used < 500 else ("moderate" if tokens_used < 2000 else "complex")
        self._update_routing(model, intent, complexity, cost_usd, quality_score or 0.7)
    
    def _update_routing(
        self,
        model: str,
        intent: str,
        complexity: str,
        cost: float,
        quality: float
    ):
        """Update model routing recommendations."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM model_routing
                WHERE intent = ? AND complexity = ?
            """, (intent, complexity))
            
            row = cursor.fetchone()
            
            if row:
                # Running average
                new_count = row["sample_count"] + 1
                new_cost = (row["avg_cost"] * row["sample_count"] + cost) / new_count
                new_quality = (row["avg_quality"] * row["sample_count"] + quality) / new_count
                
                # Only update recommendation if this model is better (quality/cost ratio)
                if quality / max(cost, 0.0001) > row["avg_quality"] / max(row["avg_cost"], 0.0001):
                    cursor.execute("""
                        UPDATE model_routing
                        SET recommended_model = ?, avg_cost = ?, avg_quality = ?, sample_count = ?
                        WHERE intent = ? AND complexity = ?
                    """, (model, new_cost, new_quality, new_count, intent, complexity))
                else:
                    cursor.execute("""
                        UPDATE model_routing
                        SET avg_cost = ?, avg_quality = ?, sample_count = ?
                        WHERE intent = ? AND complexity = ?
                    """, (new_cost, new_quality, new_count, intent, complexity))
            else:
                cursor.execute("""
                    INSERT INTO model_routing (
                        intent, complexity, recommended_model, avg_cost, avg_quality, sample_count
                    ) VALUES (?, ?, ?, ?, ?, 1)
                """, (intent, complexity, model, cost, quality))
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get suggestions for efficiency improvements."""
        suggestions = []
        
        with self._cursor() as cursor:
            # Check for expensive repeated queries
            cursor.execute("""
                SELECT query_pattern, COUNT(*) as count, AVG(avg_response_time_ms) as avg_time
                FROM response_cache
                GROUP BY query_pattern
                HAVING count > 5
                ORDER BY count DESC
                LIMIT 5
            """)
            
            for row in cursor.fetchall():
                suggestions.append({
                    "type": "frequent_query",
                    "pattern": row["query_pattern"],
                    "count": row["count"],
                    "suggestion": f"Consider pre-computing or caching '{row['query_pattern']}' responses"
                })
            
            # Check model routing efficiency
            cursor.execute("""
                SELECT model, intent, AVG(cost_usd) as avg_cost, COUNT(*) as count
                FROM performance_metrics
                WHERE timestamp >= ?
                GROUP BY model, intent
                HAVING count > 10
                ORDER BY avg_cost DESC
                LIMIT 5
            """, ((datetime.now() - timedelta(days=7)).isoformat(),))
            
            for row in cursor.fetchall():
                if row["avg_cost"] > 0.01:  # High cost threshold
                    suggestions.append({
                        "type": "expensive_routing",
                        "model": row["model"],
                        "intent": row["intent"],
                        "avg_cost": row["avg_cost"],
                        "suggestion": f"Consider using a cheaper model for {row['intent']} queries"
                    })
        
        return suggestions
    
    def get_efficiency_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get efficiency statistics."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._cursor() as cursor:
            # Cache stats
            cursor.execute("""
                SELECT SUM(hit_count) as total_hits, SUM(saved_cost_usd) as total_saved
                FROM response_cache
            """)
            cache = cursor.fetchone()
            
            # Model usage
            cursor.execute("""
                SELECT model, COUNT(*) as count, AVG(cost_usd) as avg_cost, AVG(response_time_ms) as avg_time
                FROM performance_metrics
                WHERE timestamp >= ?
                GROUP BY model
            """, (since,))
            by_model = {
                row["model"]: {
                    "count": row["count"],
                    "avg_cost": row["avg_cost"],
                    "avg_time_ms": row["avg_time"]
                }
                for row in cursor.fetchall()
            }
            
            # Total costs
            cursor.execute("""
                SELECT SUM(cost_usd) as total_cost
                FROM performance_metrics
                WHERE timestamp >= ?
            """, (since,))
            total_cost = cursor.fetchone()["total_cost"] or 0
        
        return {
            "period_days": days,
            "cache_hits": cache["total_hits"] or 0,
            "cost_saved_by_cache": cache["total_saved"] or 0,
            "total_cost": total_cost,
            "by_model": by_model
        }
    
    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries."""
        with self._cursor() as cursor:
            cursor.execute("""
                DELETE FROM response_cache
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            return cursor.rowcount
    
    def record_optimization(self, opt_type: str, description: str, cost_impact: float = 0, speed_impact: float = 0):
        """Record an optimization that was applied."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO optimization_history (timestamp, optimization_type, description, impact_cost, impact_speed_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                opt_type,
                description,
                cost_impact,
                speed_impact
            ))
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_evolver: Optional[EfficiencyEvolver] = None


def get_efficiency_evolver() -> EfficiencyEvolver:
    """Get or create global efficiency evolver."""
    global _evolver
    if _evolver is None:
        _evolver = EfficiencyEvolver()
    return _evolver


def check_cache(query: str) -> Optional[str]:
    """Check cache for a response."""
    return get_efficiency_evolver().check_cache(query)


def recommend_model(message: str, intent: str) -> Tuple[str, float]:
    """Get model recommendation."""
    return get_efficiency_evolver().recommend_model(message, intent)


def record_efficiency_metrics(model: str, intent: str, time_ms: float, tokens: int, cost: float, quality: float = None):
    """Record performance metrics."""
    get_efficiency_evolver().record_performance(model, intent, time_ms, tokens, cost, quality)


