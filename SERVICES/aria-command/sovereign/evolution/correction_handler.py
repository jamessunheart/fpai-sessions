#!/usr/bin/env python3
"""
ARIA CORRECTION HANDLER
========================

Specialized handler for learning from user corrections in real-time.

When a user says "No, I meant X" or "Actually, I wanted Y":
1. Detect the correction immediately
2. Extract what they actually wanted
3. Update routing/interpretation rules
4. Apply the learning to the current conversation

This is CRITICAL for Aria to improve from mistakes instantly.
"""

import os
import json
import sqlite3
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.evolution.correction")

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

# ============================================================================
# CORRECTION PATTERNS
# ============================================================================

# Patterns that indicate user is correcting Aria
CORRECTION_TRIGGERS = [
    # Direct corrections
    (r'\bno,?\s*i\s+meant\s+(.+)', "explicit_correction"),
    (r'\bactually,?\s+(.+)', "clarification"),
    (r'\bwhat\s+i\s+(actually\s+)?wanted\s+(was|is)\s+(.+)', "clarification"),
    (r'\bi\s+meant\s+(.+)', "explicit_correction"),
    (r'\bnot\s+that,?\s+(.+)', "rejection_redirect"),
    (r'\bthe\s+other\s+(.+)', "alternative"),
    (r'\bwrong\s+(.+)', "rejection"),
    (r'\bincorrect', "rejection"),
    (r'\bthat\'s\s+not\s+(what|right)', "rejection"),
    
    # Implicit corrections (user repeats with emphasis)
    (r'^(.+)\s*\?\s*$', "repeated_question"),  # Question marks often mean "didn't you understand?"
    (r'^(.+)!$', "emphasis"),  # Exclamation for emphasis
]

# Categories of misunderstanding
MISUNDERSTANDING_CATEGORIES = {
    "intent": ["trading", "server", "build", "help", "chat"],
    "target": ["btc", "eth", "sol", "primary", "secondary", "aria"],
    "action": ["check", "execute", "show", "restart", "create"],
    "scope": ["all", "one", "recent", "historical"]
}


@dataclass
class CorrectionEvent:
    """A detected correction event."""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Context
    user_id: str = ""
    original_query: str = ""
    aria_response: str = ""
    correction_message: str = ""
    
    # Extracted learning
    correction_type: str = ""  # explicit_correction, clarification, rejection
    extracted_intent: str = ""  # What user actually wanted
    misunderstood_as: str = ""  # What Aria thought they meant
    
    # Analysis
    category: str = ""  # intent, target, action, scope
    confidence: float = 0.5
    applied: bool = False


@dataclass
class InterpretationRule:
    """A learned rule for interpreting queries."""
    id: Optional[int] = None
    pattern: str = ""  # Regex pattern to match
    interpretation: str = ""  # How to interpret
    priority: int = 0  # Higher = more specific
    source_corrections: int = 0  # How many corrections led to this
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

CORRECTION_SCHEMA = """
-- Correction events log
CREATE TABLE IF NOT EXISTS correction_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    original_query TEXT NOT NULL,
    aria_response TEXT,
    correction_message TEXT NOT NULL,
    correction_type TEXT,
    extracted_intent TEXT,
    misunderstood_as TEXT,
    category TEXT,
    confidence REAL DEFAULT 0.5,
    applied INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_corr_events_user ON correction_events(user_id);
CREATE INDEX IF NOT EXISTS idx_corr_events_time ON correction_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_corr_events_type ON correction_events(correction_type);

-- Interpretation rules (learned from corrections)
CREATE TABLE IF NOT EXISTS interpretation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    source_corrections INTEGER DEFAULT 1,
    success_rate REAL DEFAULT 0.5,
    hit_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_rules_priority ON interpretation_rules(priority DESC);
CREATE INDEX IF NOT EXISTS idx_rules_active ON interpretation_rules(active);

-- Query routing overrides (specific redirects)
CREATE TABLE IF NOT EXISTS query_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    original_query TEXT NOT NULL,
    override_interpretation TEXT NOT NULL,
    override_tools TEXT,
    confidence REAL DEFAULT 0.7,
    hit_count INTEGER DEFAULT 0,
    last_hit TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_override_hash ON query_overrides(query_hash);
CREATE INDEX IF NOT EXISTS idx_override_confidence ON query_overrides(confidence DESC);
"""


# ============================================================================
# CORRECTION HANDLER
# ============================================================================

class CorrectionHandler:
    """
    Handles detection and learning from user corrections.
    
    This is the most important real-time learning component because
    corrections represent explicit feedback about Aria's mistakes.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        
        # In-memory rule cache for speed
        self._rules: List[InterpretationRule] = []
        self._overrides: Dict[str, str] = {}  # query_hash -> interpretation
        
        self._load_rules()
    
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
            cursor.executescript(CORRECTION_SCHEMA)
        logger.info("Correction handler initialized")
    
    def _load_rules(self):
        """Load interpretation rules into memory."""
        try:
            with self._cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM interpretation_rules
                    WHERE active = 1
                    ORDER BY priority DESC, source_corrections DESC
                """)
                self._rules = [
                    InterpretationRule(
                        id=row["id"],
                        pattern=row["pattern"],
                        interpretation=row["interpretation"],
                        priority=row["priority"],
                        source_corrections=row["source_corrections"],
                        success_rate=row["success_rate"]
                    )
                    for row in cursor.fetchall()
                ]
                
                cursor.execute("""
                    SELECT query_hash, override_interpretation
                    FROM query_overrides
                    WHERE confidence >= 0.5
                """)
                self._overrides = {
                    row["query_hash"]: row["override_interpretation"]
                    for row in cursor.fetchall()
                }
                
                logger.info(f"Loaded {len(self._rules)} rules, {len(self._overrides)} overrides")
                
        except Exception as e:
            logger.warning(f"Rule load error: {e}")
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query matching."""
        import hashlib
        normalized = re.sub(r'[^\w\s]', '', query.lower())
        normalized = ' '.join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    # ========================================================================
    # CORRECTION DETECTION
    # ========================================================================
    
    def detect_correction(self, message: str) -> Tuple[bool, str, str]:
        """
        Detect if a message is a correction.
        
        Returns:
            Tuple of (is_correction, correction_type, extracted_content)
        """
        msg_lower = message.lower().strip()
        
        for pattern, corr_type in CORRECTION_TRIGGERS:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                # Extract the content after the correction signal
                extracted = match.group(1) if match.groups() else ""
                return True, corr_type, extracted
        
        return False, "", ""
    
    def process_correction(
        self,
        user_id: str,
        original_query: str,
        aria_response: str,
        correction_message: str
    ) -> CorrectionEvent:
        """
        Process a detected correction and learn from it.
        
        This:
        1. Records the correction event
        2. Extracts the user's actual intent
        3. Creates/updates interpretation rules
        4. Returns the correction event for immediate application
        """
        is_correction, corr_type, extracted = self.detect_correction(correction_message)
        
        if not is_correction:
            # Not actually a correction
            return None
        
        # Analyze what Aria misunderstood
        misunderstood_as = self._analyze_misunderstanding(original_query, aria_response)
        
        # Extract the actual intent
        actual_intent = extracted if extracted else correction_message
        
        # Determine category
        category = self._categorize_correction(original_query, actual_intent)
        
        # Create correction event
        event = CorrectionEvent(
            timestamp=datetime.now(),
            user_id=user_id,
            original_query=original_query,
            aria_response=aria_response[:500],
            correction_message=correction_message,
            correction_type=corr_type,
            extracted_intent=actual_intent,
            misunderstood_as=misunderstood_as,
            category=category,
            confidence=0.7 if corr_type == "explicit_correction" else 0.5
        )
        
        # Record in database
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO correction_events (
                    timestamp, user_id, original_query, aria_response,
                    correction_message, correction_type, extracted_intent,
                    misunderstood_as, category, confidence, applied, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                event.timestamp.isoformat(),
                user_id, original_query, aria_response[:500],
                correction_message, corr_type, actual_intent,
                misunderstood_as, category, event.confidence,
                datetime.now().isoformat()
            ))
            event.id = cursor.lastrowid
        
        # Learn from this correction
        self._learn_from_correction(event)
        
        logger.info(f"Processed correction: '{original_query[:30]}' -> '{actual_intent[:30]}'")
        
        return event
    
    def _analyze_misunderstanding(self, query: str, response: str) -> str:
        """Analyze what Aria thought the user meant."""
        response_lower = response.lower()
        
        # Check for domain mismatches
        if "trading" in response_lower or "position" in response_lower:
            return "trading"
        if "server" in response_lower or "service" in response_lower:
            return "server"
        if "code" in response_lower or "file" in response_lower:
            return "build"
        if "help" in response_lower or "command" in response_lower:
            return "help"
        
        return "unknown"
    
    def _categorize_correction(self, original: str, corrected: str) -> str:
        """Categorize the type of correction."""
        original_lower = original.lower()
        corrected_lower = corrected.lower()
        
        # Check for intent mismatch
        for category, keywords in MISUNDERSTANDING_CATEGORIES.items():
            orig_has = any(k in original_lower for k in keywords)
            corr_has = any(k in corrected_lower for k in keywords)
            if orig_has != corr_has:
                return category
        
        return "interpretation"
    
    def _learn_from_correction(self, event: CorrectionEvent):
        """Create or update rules from a correction."""
        query_hash = self._hash_query(event.original_query)
        
        # 1. Create a specific override for this exact query
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO query_overrides (
                    query_hash, original_query, override_interpretation,
                    confidence, hit_count, created_at
                ) VALUES (?, ?, ?, ?, 0, ?)
                ON CONFLICT(query_hash) DO UPDATE SET
                    override_interpretation = excluded.override_interpretation,
                    confidence = MIN(0.95, confidence + 0.1),
                    hit_count = hit_count
            """, (
                query_hash,
                event.original_query[:500],
                event.extracted_intent,
                event.confidence,
                datetime.now().isoformat()
            ))
        
        # Update in-memory cache
        self._overrides[query_hash] = event.extracted_intent
        
        # 2. Try to generalize into a pattern rule
        # Look for similar corrections
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT extracted_intent, COUNT(*) as count
                FROM correction_events
                WHERE misunderstood_as = ? AND category = ?
                GROUP BY extracted_intent
                HAVING count >= 2
            """, (event.misunderstood_as, event.category))
            
            for row in cursor.fetchall():
                # There's a pattern - create a general rule
                pattern = self._generalize_pattern(event.original_query, event.misunderstood_as)
                if pattern:
                    cursor.execute("""
                        INSERT INTO interpretation_rules (
                            pattern, interpretation, priority, source_corrections,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT DO NOTHING
                    """, (
                        pattern,
                        row["extracted_intent"],
                        10,  # Default priority
                        row["count"],
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
        
        # Reload rules
        self._load_rules()
    
    def _generalize_pattern(self, query: str, misunderstood_as: str) -> Optional[str]:
        """Try to create a generalized pattern from a specific query."""
        # Simple generalization: replace specific terms with wildcards
        query_lower = query.lower()
        
        # Remove specific assets
        pattern = re.sub(r'\b(btc|eth|sol|bitcoin|ethereum|solana)\b', r'\\w+', query_lower)
        
        # Remove numbers
        pattern = re.sub(r'\b\d+\b', r'\\d+', pattern)
        
        # If pattern is different from original, it's generalized
        if pattern != query_lower:
            return pattern
        
        return None
    
    # ========================================================================
    # QUERY ENHANCEMENT
    # ========================================================================
    
    def enhance_query(self, query: str) -> Dict[str, Any]:
        """
        Enhance a query with learned corrections and rules.
        
        Call this BEFORE processing a query to apply learned interpretations.
        
        Returns:
            Dict with enhancement info:
            - has_override: Whether there's a specific override
            - override_interpretation: The learned correct interpretation
            - matched_rules: List of matching interpretation rules
            - confidence: Overall confidence in the enhancement
        """
        query_hash = self._hash_query(query)
        result = {
            "has_override": False,
            "override_interpretation": None,
            "matched_rules": [],
            "confidence": 0.0,
            "original_query": query
        }
        
        # 1. Check for specific override (highest priority)
        if query_hash in self._overrides:
            result["has_override"] = True
            result["override_interpretation"] = self._overrides[query_hash]
            result["confidence"] = 0.9
            
            # Update hit count
            with self._cursor() as cursor:
                cursor.execute("""
                    UPDATE query_overrides
                    SET hit_count = hit_count + 1, last_hit = ?
                    WHERE query_hash = ?
                """, (datetime.now().isoformat(), query_hash))
            
            return result
        
        # 2. Check interpretation rules
        query_lower = query.lower()
        matched_rules = []
        
        for rule in self._rules:
            try:
                if re.search(rule.pattern, query_lower, re.IGNORECASE):
                    matched_rules.append({
                        "rule_id": rule.id,
                        "interpretation": rule.interpretation,
                        "priority": rule.priority,
                        "success_rate": rule.success_rate
                    })
                    
                    # Update hit count
                    with self._cursor() as cursor:
                        cursor.execute("""
                            UPDATE interpretation_rules
                            SET hit_count = hit_count + 1, updated_at = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), rule.id))
            except re.error:
                pass  # Invalid regex, skip
        
        if matched_rules:
            # Sort by priority and success rate
            matched_rules.sort(key=lambda x: (x["priority"], x["success_rate"]), reverse=True)
            result["matched_rules"] = matched_rules
            result["confidence"] = matched_rules[0]["success_rate"]
        
        return result
    
    def record_rule_outcome(self, rule_id: int, success: bool):
        """Record whether a rule application was successful."""
        with self._cursor() as cursor:
            if success:
                cursor.execute("""
                    UPDATE interpretation_rules
                    SET success_rate = (success_rate * hit_count + 1.0) / (hit_count + 1)
                    WHERE id = ?
                """, (rule_id,))
            else:
                cursor.execute("""
                    UPDATE interpretation_rules
                    SET success_rate = (success_rate * hit_count) / (hit_count + 1)
                    WHERE id = ?
                """, (rule_id,))
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    
    def get_correction_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get correction statistics."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            # Total corrections
            cursor.execute("""
                SELECT COUNT(*) as total,
                       AVG(confidence) as avg_confidence
                FROM correction_events
                WHERE timestamp >= ?
            """, (since,))
            totals = dict(cursor.fetchone())
            
            # By type
            cursor.execute("""
                SELECT correction_type, COUNT(*) as count
                FROM correction_events
                WHERE timestamp >= ?
                GROUP BY correction_type
            """, (since,))
            by_type = {row["correction_type"]: row["count"] for row in cursor.fetchall()}
            
            # By category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM correction_events
                WHERE timestamp >= ?
                GROUP BY category
            """, (since,))
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
            
            # Most common misunderstandings
            cursor.execute("""
                SELECT misunderstood_as, COUNT(*) as count
                FROM correction_events
                WHERE timestamp >= ?
                GROUP BY misunderstood_as
                ORDER BY count DESC
                LIMIT 5
            """, (since,))
            common_mistakes = [
                {"category": row["misunderstood_as"], "count": row["count"]}
                for row in cursor.fetchall()
            ]
        
        return {
            "period_hours": hours,
            "total_corrections": totals.get("total", 0),
            "avg_confidence": totals.get("avg_confidence", 0),
            "by_type": by_type,
            "by_category": by_category,
            "common_mistakes": common_mistakes,
            "active_rules": len(self._rules),
            "active_overrides": len(self._overrides)
        }
    
    def get_recent_corrections(self, limit: int = 10) -> List[Dict]:
        """Get recent correction events."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM correction_events
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_handler: Optional[CorrectionHandler] = None


def get_correction_handler() -> CorrectionHandler:
    """Get or create global correction handler."""
    global _handler
    if _handler is None:
        _handler = CorrectionHandler()
    return _handler


def detect_and_learn(
    user_id: str,
    original_query: str,
    aria_response: str,
    new_message: str
) -> Optional[CorrectionEvent]:
    """
    Detect if new_message is a correction and learn from it.
    
    Returns the correction event if detected, None otherwise.
    """
    handler = get_correction_handler()
    is_correction, _, _ = handler.detect_correction(new_message)
    
    if is_correction:
        return handler.process_correction(
            user_id, original_query, aria_response, new_message
        )
    
    return None


def enhance_query(query: str) -> Dict[str, Any]:
    """Enhance a query with learned corrections."""
    return get_correction_handler().enhance_query(query)


