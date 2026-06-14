"""
ARIA ABSTRACTION ENGINE
========================

Generalizes specific memories into abstract principles.

Human memory doesn't just store facts - it ABSTRACTS:
- "James corrected me 3 times about being too verbose" → "Be concise"
- "API timeouts happened 5 times this week" → "APIs are unreliable, add fallbacks"
- "Trading signals were wrong when volume was low" → "Low volume = low confidence"

This module:
1. Detects patterns across multiple memories
2. Generates abstract principles
3. Applies principles to new situations
4. Refines principles based on feedback
"""

import os
import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import contextmanager
from collections import Counter

logger = logging.getLogger("aria.memory.abstraction")

# Configuration
ABSTRACTION_DB_PATH = Path(os.getenv("ARIA_ABSTRACTION_DB", "/opt/fpai/aria-command/state/abstractions.db"))
MIN_OBSERVATIONS = 3  # Need at least 3 observations to form a principle


@dataclass
class Observation:
    """A single observation that contributes to a pattern."""
    id: str
    content: str
    category: str  # What kind of observation (correction, success, failure, preference)
    context: str   # What was happening
    timestamp: datetime
    memory_id: str  # Link to source memory
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "memory_id": self.memory_id
        }


@dataclass
class Principle:
    """An abstracted principle derived from observations."""
    id: str
    statement: str  # The principle itself (e.g., "Be concise with James")
    category: str   # communication, trading, technical, behavior
    confidence: float  # 0-1, based on number and consistency of observations
    observations: List[str]  # IDs of supporting observations
    created_at: datetime
    last_applied: Optional[datetime]
    times_applied: int
    times_validated: int  # When principle led to good outcome
    times_violated: int   # When principle was ignored and bad outcome
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "category": self.category,
            "confidence": self.confidence,
            "observation_count": len(self.observations),
            "created_at": self.created_at.isoformat(),
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
            "times_applied": self.times_applied,
            "times_validated": self.times_validated,
            "times_violated": self.times_violated,
            "effectiveness": self._effectiveness()
        }
    
    def _effectiveness(self) -> float:
        """Calculate how effective this principle has been."""
        total = self.times_validated + self.times_violated
        if total == 0:
            return 0.5  # Unknown
        return self.times_validated / total


class AbstractionEngine:
    """
    Generates and applies abstract principles from observations.
    
    The key insight: Good memory isn't about storing everything,
    it's about learning the RIGHT lessons from experience.
    """
    
    # Categories of observations
    CATEGORIES = {
        "correction": ["corrected", "wrong", "actually", "instead", "not that"],
        "success": ["great", "perfect", "exactly", "good job", "thanks"],
        "failure": ["error", "failed", "broken", "didn't work", "bug"],
        "preference": ["prefer", "like", "want", "always", "never"],
        "pattern": ["usually", "often", "tends to", "pattern", "when"]
    }
    
    # Templates for generating principles
    PRINCIPLE_TEMPLATES = {
        "correction": "When {context}, {lesson}",
        "preference": "James prefers {preference}",
        "failure": "To avoid {failure}, {prevention}",
        "success": "For good outcomes, {action}",
        "pattern": "{pattern_description}"
    }
    
    def __init__(self):
        self._ensure_db()
        logger.info("🎓 Abstraction engine initialized")
    
    def _ensure_db(self):
        """Create database and tables."""
        ABSTRACTION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    memory_id TEXT,
                    principle_id TEXT
                );
                
                CREATE TABLE IF NOT EXISTS principles (
                    id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    observations TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    last_applied TEXT,
                    times_applied INTEGER DEFAULT 0,
                    times_validated INTEGER DEFAULT 0,
                    times_violated INTEGER DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_observations_category ON observations(category);
                CREATE INDEX IF NOT EXISTS idx_observations_principle ON observations(principle_id);
                CREATE INDEX IF NOT EXISTS idx_principles_category ON principles(category);
                CREATE INDEX IF NOT EXISTS idx_principles_confidence ON principles(confidence DESC);
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(ABSTRACTION_DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def record_observation(
        self,
        content: str,
        context: str = "",
        memory_id: str = None
    ) -> Optional[Observation]:
        """
        Record an observation from an interaction.
        
        Automatically categorizes and may trigger principle generation.
        """
        # Categorize the observation
        category = self._categorize(content)
        if not category:
            return None  # Not an interesting observation
        
        obs_id = f"obs_{datetime.now(timezone.utc).timestamp()}"
        now = datetime.now(timezone.utc)
        
        obs = Observation(
            id=obs_id,
            content=content[:500],
            category=category,
            context=context[:200],
            timestamp=now,
            memory_id=memory_id or ""
        )
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO observations (id, content, category, context, timestamp, memory_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (obs.id, obs.content, obs.category, obs.context, now.isoformat(), obs.memory_id))
        
        logger.debug(f"Recorded observation ({category}): {content[:50]}...")
        
        # Check if we can form a new principle
        self._try_form_principle(category)
        
        return obs
    
    def _categorize(self, content: str) -> Optional[str]:
        """Categorize an observation based on keywords."""
        content_lower = content.lower()
        
        for category, keywords in self.CATEGORIES.items():
            if any(kw in content_lower for kw in keywords):
                return category
        
        return None
    
    def _try_form_principle(self, category: str):
        """
        Try to form a principle from observations in a category.
        """
        with self._get_connection() as conn:
            # Get unassigned observations in this category
            rows = conn.execute("""
                SELECT * FROM observations
                WHERE category = ? AND (principle_id IS NULL OR principle_id = '')
                ORDER BY timestamp DESC
                LIMIT 20
            """, (category,)).fetchall()
            
            if len(rows) < MIN_OBSERVATIONS:
                return  # Not enough observations yet
            
            # Find common themes using simple word frequency
            observations = [self._row_to_observation(row) for row in rows]
            
            # Extract key words from observations
            all_words = []
            for obs in observations:
                words = obs.content.lower().split()
                # Filter to meaningful words (length > 3)
                all_words.extend([w for w in words if len(w) > 3])
            
            # Find most common words
            word_counts = Counter(all_words)
            common_words = [w for w, c in word_counts.most_common(5) if c >= MIN_OBSERVATIONS]
            
            if not common_words:
                return  # No clear pattern
            
            # Generate a principle
            principle = self._generate_principle(category, observations, common_words)
            
            if principle:
                self._store_principle(principle, [obs.id for obs in observations])
    
    def _generate_principle(
        self,
        category: str,
        observations: List[Observation],
        common_words: List[str]
    ) -> Optional[Principle]:
        """Generate a principle from observations."""
        # Simple principle generation based on category
        theme = " ".join(common_words[:3])
        
        statements = {
            "correction": f"When responding, remember: {observations[0].content[:100]}",
            "preference": f"James prefers: {theme}",
            "failure": f"Avoid issues with {theme} by being careful",
            "success": f"Good approach: {theme}",
            "pattern": f"Pattern noticed: {theme}"
        }
        
        statement = statements.get(category)
        if not statement:
            return None
        
        principle_id = f"prin_{datetime.now(timezone.utc).timestamp()}"
        
        # Calculate initial confidence based on observation count
        confidence = min(0.9, 0.3 + (len(observations) * 0.1))
        
        return Principle(
            id=principle_id,
            statement=statement,
            category=category,
            confidence=confidence,
            observations=[obs.id for obs in observations],
            created_at=datetime.now(timezone.utc),
            last_applied=None,
            times_applied=0,
            times_validated=0,
            times_violated=0
        )
    
    def _store_principle(self, principle: Principle, observation_ids: List[str]):
        """Store a principle and link observations."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO principles 
                (id, statement, category, confidence, observations, created_at,
                 times_applied, times_validated, times_violated)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0)
            """, (
                principle.id,
                principle.statement,
                principle.category,
                principle.confidence,
                json.dumps(principle.observations),
                principle.created_at.isoformat()
            ))
            
            # Link observations to principle
            for obs_id in observation_ids:
                conn.execute(
                    "UPDATE observations SET principle_id = ? WHERE id = ?",
                    (principle.id, obs_id)
                )
        
        logger.info(f"🎓 New principle formed: {principle.statement[:50]}...")
    
    def get_applicable_principles(
        self,
        context: str,
        limit: int = 5
    ) -> List[Principle]:
        """
        Get principles that might apply to a given context.
        """
        with self._get_connection() as conn:
            # Get all principles ordered by confidence
            rows = conn.execute("""
                SELECT * FROM principles
                WHERE confidence > 0.3
                ORDER BY confidence DESC, times_validated DESC
                LIMIT ?
            """, (limit * 2,)).fetchall()
            
            principles = [self._row_to_principle(row) for row in rows]
            
            # Filter to those relevant to context
            context_lower = context.lower()
            relevant = []
            
            for p in principles:
                # Check if principle keywords appear in context
                principle_words = set(p.statement.lower().split())
                context_words = set(context_lower.split())
                
                overlap = principle_words & context_words
                if len(overlap) >= 2:  # At least 2 common words
                    relevant.append(p)
            
            return relevant[:limit]
    
    def get_principles_prompt(self, context: str) -> str:
        """
        Get principles formatted for prompt injection.
        """
        principles = self.get_applicable_principles(context, limit=3)
        
        if not principles:
            return ""
        
        lines = ["\n## 🎓 Guiding Principles\n"]
        lines.append("*Lessons abstracted from past experience:*\n")
        
        for p in principles:
            confidence_bar = "●" * int(p.confidence * 5) + "○" * (5 - int(p.confidence * 5))
            lines.append(f"- [{confidence_bar}] {p.statement}")
        
        lines.append("\n---\n")
        return "\n".join(lines)
    
    def validate_principle(self, principle_id: str, was_helpful: bool):
        """
        Record whether following a principle led to good outcome.
        """
        with self._get_connection() as conn:
            if was_helpful:
                conn.execute("""
                    UPDATE principles 
                    SET times_validated = times_validated + 1,
                        last_applied = ?,
                        times_applied = times_applied + 1,
                        confidence = MIN(0.95, confidence + 0.05)
                    WHERE id = ?
                """, (datetime.now(timezone.utc).isoformat(), principle_id))
            else:
                conn.execute("""
                    UPDATE principles 
                    SET times_violated = times_violated + 1,
                        last_applied = ?,
                        times_applied = times_applied + 1,
                        confidence = MAX(0.1, confidence - 0.1)
                    WHERE id = ?
                """, (datetime.now(timezone.utc).isoformat(), principle_id))
    
    def get_all_principles(self, min_confidence: float = 0.0) -> List[Principle]:
        """Get all principles above a confidence threshold."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM principles
                WHERE confidence >= ?
                ORDER BY confidence DESC
            """, (min_confidence,)).fetchall()
            
            return [self._row_to_principle(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get abstraction engine statistics."""
        with self._get_connection() as conn:
            obs_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            prin_count = conn.execute("SELECT COUNT(*) FROM principles").fetchone()[0]
            
            by_category = dict(conn.execute(
                "SELECT category, COUNT(*) FROM observations GROUP BY category"
            ).fetchall())
            
            high_confidence = conn.execute(
                "SELECT COUNT(*) FROM principles WHERE confidence > 0.7"
            ).fetchone()[0]
            
            avg_effectiveness = conn.execute("""
                SELECT AVG(
                    CASE WHEN (times_validated + times_violated) > 0 
                    THEN CAST(times_validated AS REAL) / (times_validated + times_violated)
                    ELSE 0.5 END
                ) FROM principles
            """).fetchone()[0] or 0.5
            
            return {
                "total_observations": obs_count,
                "total_principles": prin_count,
                "observations_by_category": by_category,
                "high_confidence_principles": high_confidence,
                "avg_principle_effectiveness": round(avg_effectiveness, 2),
                "db_path": str(ABSTRACTION_DB_PATH)
            }
    
    def _row_to_observation(self, row: sqlite3.Row) -> Observation:
        """Convert row to Observation."""
        return Observation(
            id=row["id"],
            content=row["content"],
            category=row["category"],
            context=row["context"] or "",
            timestamp=datetime.fromisoformat(row["timestamp"]),
            memory_id=row["memory_id"] or ""
        )
    
    def _row_to_principle(self, row: sqlite3.Row) -> Principle:
        """Convert row to Principle."""
        return Principle(
            id=row["id"],
            statement=row["statement"],
            category=row["category"],
            confidence=row["confidence"],
            observations=json.loads(row["observations"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_applied=datetime.fromisoformat(row["last_applied"]) if row["last_applied"] else None,
            times_applied=row["times_applied"],
            times_validated=row["times_validated"],
            times_violated=row["times_violated"]
        )


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[AbstractionEngine] = None


def get_abstraction_engine() -> AbstractionEngine:
    """Get or create abstraction engine instance."""
    global _engine
    if _engine is None:
        _engine = AbstractionEngine()
    return _engine









