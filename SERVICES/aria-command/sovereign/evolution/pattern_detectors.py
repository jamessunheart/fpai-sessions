#!/usr/bin/env python3
"""
ARIA PATTERN DETECTORS
=======================

Specific pattern detectors that analyze interaction logs to find
common issues that indicate opportunities for improvement.

Detectors:
1. ApprovalOverhead - Read-only commands asked for approval
2. FollowThroughFailure - User sent "?" after Aria said "checking..."
3. ToolOveruse - Too many tool calls for simple query
4. SlowResponse - Response took too long for simple query
5. CorrectionNeeded - User had to correct Aria
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from contextlib import contextmanager
import threading

logger = logging.getLogger("aria.evolution.patterns")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

# Thresholds
SLOW_RESPONSE_THRESHOLD_MS = 10000  # 10 seconds
TOOL_OVERUSE_THRESHOLD = 3  # More than 3 tools for simple query
SIMPLE_QUERY_PATTERNS = [
    r"(?:what'?s?|get|show|check)\s+(?:the\s+)?(?:signal|status|price|balance)",
    r"how\s+(?:is|are)\s+(?:the\s+)?(?:servers?|system|trading)",
    r"^(?:hello|hi|hey|status|help)$",
]

# Correction indicators
CORRECTION_PATTERNS = [
    r"(?:no|nope),?\s+(?:i\s+meant|actually|not\s+that)",
    r"that'?s?\s+(?:not|wrong)",
    r"i\s+(?:said|meant|asked)\s+",
    r"try\s+again",
    r"wrong\s+(?:answer|response)",
]

# Follow-through failure indicators
FOLLOWTHROUGH_FAILURE_PATTERNS = [
    r"^\?+$",  # Just question marks
    r"^(?:hello|still\s+there|waiting|any\s+update)\??$",
]

PENDING_ACTION_PATTERNS = [
    r"(?:let\s+me|i'?ll)\s+(?:check|get|look|fetch)",
    r"one\s+moment",
    r"checking\s+now",
    r"i'?m\s+(?:checking|looking|fetching)",
]


@dataclass
class DetectedPattern:
    """A detected pattern that indicates an improvement opportunity."""
    detector: str
    severity: str  # low, medium, high
    interaction_ids: List[int] = field(default_factory=list)
    problem_description: str = ""
    suggested_fix: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "detected_at": self.detected_at.isoformat()
        }


# ============================================================================
# BASE DETECTOR
# ============================================================================

class PatternDetector(ABC):
    """Base class for pattern detectors."""
    
    name: str = "base"
    description: str = "Base detector"
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
    
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
        finally:
            pass  # Read-only, no commit needed
    
    @abstractmethod
    def detect(self, hours: int = 24) -> List[DetectedPattern]:
        """Detect patterns in the last N hours of interactions."""
        pass
    
    def detect_single(self, interaction: Dict) -> Optional[DetectedPattern]:
        """Detect pattern in a single interaction (for real-time detection)."""
        return None


# ============================================================================
# DETECTOR 1: APPROVAL OVERHEAD
# ============================================================================

class ApprovalOverheadDetector(PatternDetector):
    """
    Detects when read-only commands unnecessarily asked for approval.
    
    Example: "curl signal" -> "This requires approval"
    """
    
    name = "approval_overhead"
    description = "Read-only commands asking for approval"
    
    # Patterns that indicate approval was requested
    APPROVAL_PATTERNS = [
        r"requires?\s+(?:your\s+)?approval",
        r"approval\s+(?:id|needed|required)",
        r"would\s+you\s+like\s+(?:me\s+)?to\s+proceed",
        r"approve\s+(?:this\s+)?(?:command|action)",
    ]
    
    # Commands that should NOT require approval
    SAFE_COMMANDS = [
        r"curl.*(?:signal|status|health|api)",
        r"curl.*(?:8600|8601|8125)",  # Trading/data ports
        r"cat\s+",
        r"ls\s+",
        r"grep\s+",
        r"systemctl\s+status",
    ]
    
    def detect(self, hours: int = 24) -> List[DetectedPattern]:
        patterns = []
        
        with self._cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT id, user_message, response, tools_called, timestamp
                FROM interactions
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (since,))
            
            flagged_interactions = []
            
            for row in cursor.fetchall():
                response = row['response'] or ""
                user_msg = row['user_message'] or ""
                tools = row['tools_called'] or ""
                
                # Check if approval was requested
                approval_requested = any(
                    re.search(p, response, re.IGNORECASE) 
                    for p in self.APPROVAL_PATTERNS
                )
                
                if not approval_requested:
                    continue
                
                # Check if it was for a safe command
                is_safe_command = any(
                    re.search(p, response, re.IGNORECASE) or
                    re.search(p, tools, re.IGNORECASE) or
                    re.search(p, user_msg, re.IGNORECASE)
                    for p in self.SAFE_COMMANDS
                )
                
                if is_safe_command:
                    flagged_interactions.append({
                        "id": row['id'],
                        "user_message": user_msg[:100],
                        "timestamp": row['timestamp']
                    })
            
            if flagged_interactions:
                severity = "high" if len(flagged_interactions) >= 3 else "medium"
                patterns.append(DetectedPattern(
                    detector=self.name,
                    severity=severity,
                    interaction_ids=[i['id'] for i in flagged_interactions],
                    problem_description=f"Read-only commands asked for approval {len(flagged_interactions)} times",
                    suggested_fix="Add command patterns to GREEN_COMMANDS in terminal.py",
                    evidence={"interactions": flagged_interactions}
                ))
        
        return patterns
    
    def detect_single(self, interaction: Dict) -> Optional[DetectedPattern]:
        response = interaction.get('response', '')
        user_msg = interaction.get('user_message', '')
        
        approval_requested = any(
            re.search(p, response, re.IGNORECASE) 
            for p in self.APPROVAL_PATTERNS
        )
        
        if not approval_requested:
            return None
        
        is_safe_command = any(
            re.search(p, response, re.IGNORECASE) or
            re.search(p, user_msg, re.IGNORECASE)
            for p in self.SAFE_COMMANDS
        )
        
        if is_safe_command:
            return DetectedPattern(
                detector=self.name,
                severity="medium",
                interaction_ids=[interaction.get('id', 0)],
                problem_description="Read-only command asked for approval",
                suggested_fix="Add command pattern to GREEN_COMMANDS"
            )
        
        return None


# ============================================================================
# DETECTOR 2: FOLLOW-THROUGH FAILURE
# ============================================================================

class FollowThroughFailureDetector(PatternDetector):
    """
    Detects when user sent "?" after Aria said she would do something.
    
    Example: "I'll check now" -> (no response) -> "?"
    """
    
    name = "followthrough_failure"
    description = "Aria said she would do something but didn't follow through"
    
    def detect(self, hours: int = 24) -> List[DetectedPattern]:
        patterns = []
        
        with self._cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT id, user_message, response, timestamp
                FROM interactions
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """, (since,))
            
            rows = list(cursor.fetchall())
            flagged_sequences = []
            
            for i in range(len(rows) - 1):
                current = rows[i]
                next_msg = rows[i + 1]
                
                current_response = current['response'] or ""
                next_user_msg = next_msg['user_message'] or ""
                
                # Check if current response promised action
                promised_action = any(
                    re.search(p, current_response, re.IGNORECASE)
                    for p in PENDING_ACTION_PATTERNS
                )
                
                # Check if next message is frustration indicator
                is_frustration = any(
                    re.search(p, next_user_msg.strip(), re.IGNORECASE)
                    for p in FOLLOWTHROUGH_FAILURE_PATTERNS
                )
                
                if promised_action and is_frustration:
                    flagged_sequences.append({
                        "first_id": current['id'],
                        "second_id": next_msg['id'],
                        "promised": current_response[:100],
                        "follow_up": next_user_msg,
                        "timestamp": current['timestamp']
                    })
            
            if flagged_sequences:
                severity = "high" if len(flagged_sequences) >= 2 else "medium"
                patterns.append(DetectedPattern(
                    detector=self.name,
                    severity=severity,
                    interaction_ids=[s['first_id'] for s in flagged_sequences],
                    problem_description=f"User sent '?' after Aria promised action {len(flagged_sequences)} times",
                    suggested_fix="Ensure tool execution completes and sends results before responding",
                    evidence={"sequences": flagged_sequences}
                ))
        
        return patterns


# ============================================================================
# DETECTOR 3: TOOL OVERUSE
# ============================================================================

class ToolOveruseDetector(PatternDetector):
    """
    Detects when too many tools were called for a simple query.
    
    Example: 6 curl commands for "What's the signal on SOL?"
    """
    
    name = "tool_overuse"
    description = "Too many tool calls for simple queries"
    
    def detect(self, hours: int = 24) -> List[DetectedPattern]:
        patterns = []
        
        with self._cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT id, user_message, tool_count, tools_called, total_time_ms, timestamp
                FROM interactions
                WHERE timestamp > ? AND tool_count > ?
                ORDER BY timestamp DESC
            """, (since, TOOL_OVERUSE_THRESHOLD))
            
            flagged_interactions = []
            
            for row in cursor.fetchall():
                user_msg = row['user_message'] or ""
                
                # Check if it was a simple query
                is_simple = any(
                    re.search(p, user_msg, re.IGNORECASE)
                    for p in SIMPLE_QUERY_PATTERNS
                )
                
                if is_simple:
                    flagged_interactions.append({
                        "id": row['id'],
                        "user_message": user_msg[:100],
                        "tool_count": row['tool_count'],
                        "total_time_ms": row['total_time_ms'],
                        "timestamp": row['timestamp']
                    })
            
            if flagged_interactions:
                avg_tools = sum(i['tool_count'] for i in flagged_interactions) / len(flagged_interactions)
                severity = "high" if avg_tools > 5 else "medium"
                patterns.append(DetectedPattern(
                    detector=self.name,
                    severity=severity,
                    interaction_ids=[i['id'] for i in flagged_interactions],
                    problem_description=f"Simple queries used avg {avg_tools:.1f} tool calls",
                    suggested_fix="Add smart shortcuts in bot.py _handle_natural() for common queries",
                    evidence={"interactions": flagged_interactions}
                ))
        
        return patterns
    
    def detect_single(self, interaction: Dict) -> Optional[DetectedPattern]:
        tool_count = interaction.get('tool_count', 0)
        user_msg = interaction.get('user_message', '')
        
        if tool_count <= TOOL_OVERUSE_THRESHOLD:
            return None
        
        is_simple = any(
            re.search(p, user_msg, re.IGNORECASE)
            for p in SIMPLE_QUERY_PATTERNS
        )
        
        if is_simple:
            return DetectedPattern(
                detector=self.name,
                severity="medium",
                interaction_ids=[interaction.get('id', 0)],
                problem_description=f"Simple query used {tool_count} tool calls",
                suggested_fix="Add smart shortcut for this query type"
            )
        
        return None


# ============================================================================
# DETECTOR 4: SLOW RESPONSE
# ============================================================================

class SlowResponseDetector(PatternDetector):
    """
    Detects when responses took too long for simple queries.
    
    Example: "What's the signal?" -> 40 seconds
    """
    
    name = "slow_response"
    description = "Response took too long for simple query"
    
    def detect(self, hours: int = 24) -> List[DetectedPattern]:
        patterns = []
        
        with self._cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT id, user_message, total_time_ms, tool_count, timestamp
                FROM interactions
                WHERE timestamp > ? AND total_time_ms > ?
                ORDER BY timestamp DESC
            """, (since, SLOW_RESPONSE_THRESHOLD_MS))
            
            flagged_interactions = []
            
            for row in cursor.fetchall():
                user_msg = row['user_message'] or ""
                
                # Check if it was a simple query
                is_simple = any(
                    re.search(p, user_msg, re.IGNORECASE)
                    for p in SIMPLE_QUERY_PATTERNS
                )
                
                if is_simple:
                    flagged_interactions.append({
                        "id": row['id'],
                        "user_message": user_msg[:100],
                        "total_time_ms": row['total_time_ms'],
                        "tool_count": row['tool_count'],
                        "timestamp": row['timestamp']
                    })
            
            if flagged_interactions:
                avg_time = sum(i['total_time_ms'] for i in flagged_interactions) / len(flagged_interactions)
                severity = "high" if avg_time > 20000 else "medium"
                patterns.append(DetectedPattern(
                    detector=self.name,
                    severity=severity,
                    interaction_ids=[i['id'] for i in flagged_interactions],
                    problem_description=f"Simple queries took avg {avg_time/1000:.1f}s",
                    suggested_fix="Add caching or direct API shortcuts for common queries",
                    evidence={"interactions": flagged_interactions, "avg_time_ms": avg_time}
                ))
        
        return patterns
    
    def detect_single(self, interaction: Dict) -> Optional[DetectedPattern]:
        total_time = interaction.get('total_time_ms', 0)
        user_msg = interaction.get('user_message', '')
        
        if total_time <= SLOW_RESPONSE_THRESHOLD_MS:
            return None
        
        is_simple = any(
            re.search(p, user_msg, re.IGNORECASE)
            for p in SIMPLE_QUERY_PATTERNS
        )
        
        if is_simple:
            return DetectedPattern(
                detector=self.name,
                severity="medium" if total_time < 20000 else "high",
                interaction_ids=[interaction.get('id', 0)],
                problem_description=f"Simple query took {total_time/1000:.1f}s",
                suggested_fix="Add caching or shortcut for this query type"
            )
        
        return None


# ============================================================================
# DETECTOR 5: CORRECTION NEEDED
# ============================================================================

class CorrectionNeededDetector(PatternDetector):
    """
    Detects when user had to correct Aria.
    
    Example: "No, I meant..." or "That's wrong"
    """
    
    name = "correction_needed"
    description = "User had to correct Aria's response"
    
    def detect(self, hours: int = 24) -> List[DetectedPattern]:
        patterns = []
        
        with self._cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute("""
                SELECT id, user_message, response, timestamp
                FROM interactions
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """, (since,))
            
            rows = list(cursor.fetchall())
            flagged_corrections = []
            
            for i in range(1, len(rows)):
                user_msg = rows[i]['user_message'] or ""
                prev_response = rows[i-1]['response'] or ""
                
                # Check if this message is a correction
                is_correction = any(
                    re.search(p, user_msg, re.IGNORECASE)
                    for p in CORRECTION_PATTERNS
                )
                
                if is_correction:
                    flagged_corrections.append({
                        "id": rows[i]['id'],
                        "prev_id": rows[i-1]['id'],
                        "correction": user_msg[:100],
                        "prev_response": prev_response[:100],
                        "timestamp": rows[i]['timestamp']
                    })
            
            if flagged_corrections:
                severity = "high" if len(flagged_corrections) >= 3 else "medium"
                patterns.append(DetectedPattern(
                    detector=self.name,
                    severity=severity,
                    interaction_ids=[c['id'] for c in flagged_corrections],
                    problem_description=f"User corrected Aria {len(flagged_corrections)} times",
                    suggested_fix="Improve understanding of user intent in system prompt",
                    evidence={"corrections": flagged_corrections}
                ))
        
        return patterns
    
    def detect_single(self, interaction: Dict) -> Optional[DetectedPattern]:
        user_msg = interaction.get('user_message', '')
        
        is_correction = any(
            re.search(p, user_msg, re.IGNORECASE)
            for p in CORRECTION_PATTERNS
        )
        
        if is_correction:
            return DetectedPattern(
                detector=self.name,
                severity="medium",
                interaction_ids=[interaction.get('id', 0)],
                problem_description="User corrected Aria",
                suggested_fix="Review previous response and improve handling"
            )
        
        return None


# ============================================================================
# PATTERN DETECTOR MANAGER
# ============================================================================

class PatternDetectorManager:
    """Manages all pattern detectors."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.detectors: List[PatternDetector] = [
            ApprovalOverheadDetector(db_path),
            FollowThroughFailureDetector(db_path),
            ToolOveruseDetector(db_path),
            SlowResponseDetector(db_path),
            CorrectionNeededDetector(db_path),
        ]
        self._local = threading.local()
    
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
    
    def detect_all(self, hours: int = 24) -> List[DetectedPattern]:
        """Run all detectors and return all detected patterns."""
        all_patterns = []
        
        for detector in self.detectors:
            try:
                patterns = detector.detect(hours)
                all_patterns.extend(patterns)
                logger.info(f"Detector {detector.name}: found {len(patterns)} patterns")
            except Exception as e:
                logger.error(f"Detector {detector.name} failed: {e}")
        
        return all_patterns
    
    def detect_single(self, interaction: Dict) -> List[DetectedPattern]:
        """Run all detectors on a single interaction (real-time)."""
        patterns = []
        
        for detector in self.detectors:
            try:
                pattern = detector.detect_single(interaction)
                if pattern:
                    patterns.append(pattern)
            except Exception as e:
                logger.error(f"Detector {detector.name} single check failed: {e}")
        
        return patterns
    
    def get_high_severity_patterns(self, hours: int = 24) -> List[DetectedPattern]:
        """Get only high severity patterns."""
        all_patterns = self.detect_all(hours)
        return [p for p in all_patterns if p.severity == "high"]
    
    def save_detected_patterns(self, patterns: List[DetectedPattern]) -> None:
        """Save detected patterns to database for tracking."""
        with self._cursor() as cursor:
            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detected_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detector TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    interaction_ids TEXT,
                    problem_description TEXT,
                    suggested_fix TEXT,
                    evidence TEXT,
                    detected_at TEXT NOT NULL,
                    addressed INTEGER DEFAULT 0
                )
            """)
            
            for pattern in patterns:
                cursor.execute("""
                    INSERT INTO detected_patterns
                    (detector, severity, interaction_ids, problem_description, 
                     suggested_fix, evidence, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.detector,
                    pattern.severity,
                    json.dumps(pattern.interaction_ids),
                    pattern.problem_description,
                    pattern.suggested_fix,
                    json.dumps(pattern.evidence),
                    pattern.detected_at.isoformat()
                ))


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_manager: Optional[PatternDetectorManager] = None


def get_pattern_manager() -> PatternDetectorManager:
    """Get global pattern detector manager."""
    global _manager
    if _manager is None:
        _manager = PatternDetectorManager()
    return _manager


def detect_patterns(hours: int = 24) -> List[DetectedPattern]:
    """Detect all patterns in the last N hours."""
    return get_pattern_manager().detect_all(hours)


def detect_patterns_single(interaction: Dict) -> List[DetectedPattern]:
    """Detect patterns in a single interaction."""
    return get_pattern_manager().detect_single(interaction)


def get_high_severity_patterns(hours: int = 24) -> List[DetectedPattern]:
    """Get high severity patterns only."""
    return get_pattern_manager().get_high_severity_patterns(hours)


def save_patterns(patterns: List[DetectedPattern]) -> None:
    """Save detected patterns to database."""
    get_pattern_manager().save_detected_patterns(patterns)


