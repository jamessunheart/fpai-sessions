#!/usr/bin/env python3
"""
ARIA SUCCESS DETECTOR
======================

Analyzes interactions to identify successful patterns that should be
reinforced and replicated.

Success signals:
- Explicit positive feedback (thanks, great, perfect)
- Task completion without follow-up
- User returns for similar tasks
- No corrections needed
- Quick resolution

Features:
- Pattern extraction from successful interactions
- Prompt fragment identification
- Tool combination analysis
- Response style analysis
"""

import os
import json
import sqlite3
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from collections import Counter
from contextlib import contextmanager
import threading

from .interaction_logger import (
    get_interaction_logger,
    SatisfactionSignal,
    IntentCategory
)

logger = logging.getLogger("aria.evolution.success")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")


@dataclass
class SuccessPattern:
    """A detected success pattern."""
    id: Optional[int] = None
    pattern_type: str = ""  # response_style, tool_combo, prompt_phrase
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    occurrence_count: int = 1
    success_rate: float = 1.0
    confidence: float = 0.5
    intent_category: str = ""
    sample_interactions: List[int] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


PATTERN_SCHEMA = """
CREATE TABLE IF NOT EXISTS success_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    pattern_data TEXT,
    occurrence_count INTEGER DEFAULT 1,
    success_rate REAL DEFAULT 1.0,
    confidence REAL DEFAULT 0.5,
    intent_category TEXT,
    sample_interactions TEXT,
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(pattern_type, pattern_data)
);

CREATE INDEX IF NOT EXISTS idx_sp_type ON success_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_sp_confidence ON success_patterns(confidence);
CREATE INDEX IF NOT EXISTS idx_sp_intent ON success_patterns(intent_category);
"""


# ============================================================================
# PATTERN EXTRACTORS
# ============================================================================

def extract_response_style(response: str) -> Dict[str, Any]:
    """Extract style characteristics from a response."""
    return {
        "length": len(response),
        "length_category": (
            "short" if len(response) < 200 else
            "medium" if len(response) < 1000 else
            "long"
        ),
        "has_code": "```" in response,
        "has_list": bool(re.search(r'^\s*[-•*\d]\s+', response, re.MULTILINE)),
        "has_emoji": bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]', response)),
        "starts_with_action": response.strip().lower().startswith(('i ', "i'll ", "i'm ", "done", "here")),
        "asks_question": "?" in response[-100:] if len(response) > 100 else "?" in response,
        "paragraph_count": len(re.findall(r'\n\n', response)) + 1
    }


def extract_tool_pattern(tools: List[str]) -> Dict[str, Any]:
    """Extract tool usage pattern."""
    return {
        "tools": sorted(tools),
        "tool_count": len(tools),
        "tool_combo": "_".join(sorted(tools)[:5]) if tools else "none"
    }


def extract_prompt_phrases(message: str, response: str) -> List[str]:
    """Extract key phrases that led to successful responses."""
    # Simple extraction - find unique informative phrases
    phrases = []
    
    # Look for action phrases in the response
    action_patterns = [
        r"I'll ([^.!?]+)",
        r"I'm ([^.!?]+)",
        r"Let me ([^.!?]+)",
        r"Here's ([^.!?]+)"
    ]
    
    for pattern in action_patterns:
        matches = re.findall(pattern, response[:500])
        phrases.extend(matches)
    
    return phrases[:5]  # Top 5 phrases


# ============================================================================
# SUCCESS DETECTOR
# ============================================================================

class SuccessDetector:
    """
    Detects and records successful interaction patterns.
    
    Process:
    1. Analyze successful interactions
    2. Extract patterns (style, tools, phrases)
    3. Track pattern frequency
    4. Calculate confidence scores
    5. Recommend patterns for prompts
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self.interaction_logger = get_interaction_logger()
    
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
            cursor.executescript(PATTERN_SCHEMA)
        logger.info(f"Success detector initialized: {self.db_path}")
    
    def analyze_successes(self, hours: int = 24) -> List[SuccessPattern]:
        """
        Analyze recent successful interactions and extract patterns.
        
        Returns:
            List of detected success patterns.
        """
        # Get successful interactions
        successes = self.interaction_logger.get_successful_interactions(hours)
        
        if not successes:
            logger.info("No successful interactions to analyze")
            return []
        
        detected_patterns = []
        
        # Analyze response styles
        style_patterns = self._analyze_response_styles(successes)
        detected_patterns.extend(style_patterns)
        
        # Analyze tool combinations
        tool_patterns = self._analyze_tool_patterns(successes)
        detected_patterns.extend(tool_patterns)
        
        # Store patterns
        for pattern in detected_patterns:
            self._store_pattern(pattern)
        
        logger.info(f"Detected {len(detected_patterns)} success patterns from {len(successes)} interactions")
        return detected_patterns
    
    def _analyze_response_styles(self, interactions: List[Dict]) -> List[SuccessPattern]:
        """Analyze what response styles work best."""
        patterns = []
        
        # Group by intent
        by_intent: Dict[str, List[Dict]] = {}
        for interaction in interactions:
            intent = interaction.get("intent", "unknown")
            by_intent.setdefault(intent, []).append(interaction)
        
        for intent, intent_interactions in by_intent.items():
            if len(intent_interactions) < 3:
                continue
            
            # Extract styles
            styles = []
            for i in intent_interactions:
                response = i.get("response", "")
                style = extract_response_style(response)
                style["interaction_id"] = i["id"]
                style["satisfaction"] = i.get("satisfaction", "neutral")
                styles.append(style)
            
            # Find common characteristics in positive outcomes
            positive = [s for s in styles if s["satisfaction"] == "positive"]
            
            if len(positive) >= 2:
                # Find common style
                common_style = self._find_common_style(positive)
                
                if common_style:
                    patterns.append(SuccessPattern(
                        pattern_type="response_style",
                        pattern_data=common_style,
                        occurrence_count=len(positive),
                        success_rate=len(positive) / len(styles),
                        confidence=min(0.9, len(positive) / 10),  # More samples = higher confidence
                        intent_category=intent,
                        sample_interactions=[s["interaction_id"] for s in positive[:5]]
                    ))
        
        return patterns
    
    def _find_common_style(self, styles: List[Dict]) -> Optional[Dict]:
        """Find common characteristics across styles."""
        if not styles:
            return None
        
        # Count occurrences of each characteristic
        length_cats = Counter(s["length_category"] for s in styles)
        has_code = Counter(s["has_code"] for s in styles)
        has_list = Counter(s["has_list"] for s in styles)
        starts_action = Counter(s["starts_with_action"] for s in styles)
        
        # Find most common
        common = {}
        
        # Only include if > 60% share the characteristic
        threshold = len(styles) * 0.6
        
        if length_cats.most_common(1)[0][1] >= threshold:
            common["preferred_length"] = length_cats.most_common(1)[0][0]
        
        if has_code.most_common(1)[0][1] >= threshold:
            common["use_code_blocks"] = has_code.most_common(1)[0][0]
        
        if has_list.most_common(1)[0][1] >= threshold:
            common["use_lists"] = has_list.most_common(1)[0][0]
        
        if starts_action.most_common(1)[0][1] >= threshold:
            common["start_with_action"] = starts_action.most_common(1)[0][0]
        
        return common if common else None
    
    def _analyze_tool_patterns(self, interactions: List[Dict]) -> List[SuccessPattern]:
        """Analyze which tool combinations work well."""
        patterns = []
        
        # Group by intent
        by_intent: Dict[str, List[Dict]] = {}
        for interaction in interactions:
            intent = interaction.get("intent", "unknown")
            by_intent.setdefault(intent, []).append(interaction)
        
        for intent, intent_interactions in by_intent.items():
            # Count tool combinations
            tool_combos = Counter()
            for i in intent_interactions:
                tools_str = i.get("tools_called", "[]")
                try:
                    tools = json.loads(tools_str) if isinstance(tools_str, str) else tools_str
                    if tools:
                        combo = "_".join(sorted(tools)[:5])
                        tool_combos[combo] += 1
                except:
                    continue
            
            # Record frequent combinations
            for combo, count in tool_combos.most_common(5):
                if count >= 2:
                    patterns.append(SuccessPattern(
                        pattern_type="tool_combo",
                        pattern_data={"tools": combo.split("_"), "combo": combo},
                        occurrence_count=count,
                        success_rate=1.0,  # All from successful interactions
                        confidence=min(0.8, count / 10),
                        intent_category=intent
                    ))
        
        return patterns
    
    def _store_pattern(self, pattern: SuccessPattern):
        """Store or update a pattern in the database."""
        pattern_data_json = json.dumps(pattern.pattern_data, sort_keys=True)
        
        with self._cursor() as cursor:
            # Try to update existing
            cursor.execute("""
                SELECT id, occurrence_count, success_rate FROM success_patterns
                WHERE pattern_type = ? AND pattern_data = ?
            """, (pattern.pattern_type, pattern_data_json))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update with running average
                new_count = existing["occurrence_count"] + pattern.occurrence_count
                # Weighted average of success rates
                new_rate = (
                    existing["success_rate"] * existing["occurrence_count"] +
                    pattern.success_rate * pattern.occurrence_count
                ) / new_count
                
                cursor.execute("""
                    UPDATE success_patterns
                    SET occurrence_count = ?,
                        success_rate = ?,
                        confidence = ?,
                        last_seen = ?
                    WHERE id = ?
                """, (
                    new_count,
                    new_rate,
                    min(0.95, new_count / 20),  # Cap confidence
                    datetime.now().isoformat(),
                    existing["id"]
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO success_patterns (
                        pattern_type, pattern_data, occurrence_count,
                        success_rate, confidence, intent_category,
                        sample_interactions, created_at, last_seen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_type,
                    pattern_data_json,
                    pattern.occurrence_count,
                    pattern.success_rate,
                    pattern.confidence,
                    pattern.intent_category,
                    json.dumps(pattern.sample_interactions),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
    
    def get_patterns_for_intent(self, intent: str) -> List[SuccessPattern]:
        """Get success patterns for a specific intent."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM success_patterns
                WHERE intent_category = ?
                ORDER BY confidence DESC, occurrence_count DESC
            """, (intent,))
            
            return [
                SuccessPattern(
                    id=row["id"],
                    pattern_type=row["pattern_type"],
                    pattern_data=json.loads(row["pattern_data"]),
                    occurrence_count=row["occurrence_count"],
                    success_rate=row["success_rate"],
                    confidence=row["confidence"],
                    intent_category=row["intent_category"],
                    sample_interactions=json.loads(row["sample_interactions"]) if row["sample_interactions"] else [],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_seen=datetime.fromisoformat(row["last_seen"])
                )
                for row in cursor.fetchall()
            ]
    
    def get_top_patterns(self, limit: int = 20) -> List[SuccessPattern]:
        """Get top success patterns by confidence."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM success_patterns
                WHERE confidence >= 0.5
                ORDER BY confidence DESC, occurrence_count DESC
                LIMIT ?
            """, (limit,))
            
            return [
                SuccessPattern(
                    id=row["id"],
                    pattern_type=row["pattern_type"],
                    pattern_data=json.loads(row["pattern_data"]),
                    occurrence_count=row["occurrence_count"],
                    success_rate=row["success_rate"],
                    confidence=row["confidence"],
                    intent_category=row["intent_category"]
                )
                for row in cursor.fetchall()
            ]
    
    def get_recommendations(self, intent: str) -> Dict[str, Any]:
        """Get recommendations based on success patterns for an intent."""
        patterns = self.get_patterns_for_intent(intent)
        
        recommendations = {
            "response_style": {},
            "tool_suggestions": [],
            "confidence": 0.0
        }
        
        for pattern in patterns:
            if pattern.pattern_type == "response_style":
                recommendations["response_style"].update(pattern.pattern_data)
                recommendations["confidence"] = max(
                    recommendations["confidence"],
                    pattern.confidence
                )
            elif pattern.pattern_type == "tool_combo":
                tools = pattern.pattern_data.get("tools", [])
                recommendations["tool_suggestions"].extend(tools)
        
        # Deduplicate tool suggestions
        recommendations["tool_suggestions"] = list(set(recommendations["tool_suggestions"]))
        
        return recommendations
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_detector: Optional[SuccessDetector] = None


def get_success_detector() -> SuccessDetector:
    """Get or create global success detector."""
    global _detector
    if _detector is None:
        _detector = SuccessDetector()
    return _detector


def analyze_successes(hours: int = 24) -> List[SuccessPattern]:
    """Analyze recent successful interactions."""
    return get_success_detector().analyze_successes(hours)


def get_recommendations(intent: str) -> Dict[str, Any]:
    """Get success-based recommendations for an intent."""
    return get_success_detector().get_recommendations(intent)


