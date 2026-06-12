"""
ARIA EPISODIC MEMORY
=====================

Stores conversations and events as narratives, not just facts.

Human memory is episodic - we remember "that time when..."
This gives Aria the same ability:
- "That conversation on Tuesday where we debugged trading"
- "The time James was frustrated about the API key"
- "When we successfully deployed the consciousness loop"

Each episode has:
- Temporal context (when)
- Emotional context (how it felt)
- Key moments (highlights)
- Outcome (how it ended)

This transforms fragmented messages into coherent stories.
"""

import os
import sqlite3
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger("aria.memory.episodic")

# Configuration
EPISODE_DB_PATH = Path(os.getenv("ARIA_EPISODE_DB", "/opt/fpai/aria-command/state/episodes.db"))


class EpisodeType(str, Enum):
    """Types of episodes."""
    CONVERSATION = "conversation"
    DEBUG_SESSION = "debug"
    BUILDING = "building"
    PLANNING = "planning"
    CRISIS = "crisis"
    CELEBRATION = "celebration"
    LEARNING = "learning"


class EmotionalTone(str, Enum):
    """Emotional tone of an episode."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    URGENT = "urgent"
    CELEBRATORY = "celebratory"
    FOCUSED = "focused"


class Outcome(str, Enum):
    """How the episode ended."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ONGOING = "ongoing"
    ABANDONED = "abandoned"


@dataclass
class Episode:
    """A narrative episode (conversation/event)."""
    id: str
    title: str
    summary: str
    episode_type: EpisodeType
    emotional_tone: EmotionalTone
    outcome: Outcome
    
    # Temporal context
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: int
    
    # Content
    key_moments: List[str]  # Important quotes/events
    participants: List[str]  # Who was involved
    topics: List[str]  # What was discussed
    
    # Learning
    lessons_learned: List[str]
    decisions_made: List[str]
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "episode_type": self.episode_type.value,
            "emotional_tone": self.emotional_tone.value,
            "outcome": self.outcome.value,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes": self.duration_minutes,
            "key_moments": self.key_moments,
            "participants": self.participants,
            "topics": self.topics,
            "lessons_learned": self.lessons_learned,
            "decisions_made": self.decisions_made,
            "metadata": self.metadata,
            "importance": self.importance
        }
    
    def to_narrative(self) -> str:
        """Convert episode to a human-readable narrative."""
        date_str = self.started_at.strftime("%A, %B %d")
        duration = f"{self.duration_minutes} minutes" if self.duration_minutes else "brief"
        
        narrative = f"**{self.title}** ({date_str}, {duration})\n"
        narrative += f"{self.summary}\n"
        
        if self.key_moments:
            narrative += f"\nKey moments: {'; '.join(self.key_moments[:3])}"
        
        if self.lessons_learned:
            narrative += f"\nLearned: {'; '.join(self.lessons_learned[:2])}"
        
        if self.outcome != Outcome.ONGOING:
            narrative += f"\nOutcome: {self.outcome.value}"
        
        return narrative


class EpisodeBuilder:
    """
    Builds an episode from conversation messages.
    
    Call add_message() as messages come in,
    then finalize() when conversation ends.
    """
    
    def __init__(self, chat_id: str, initial_topic: str = None):
        self.chat_id = chat_id
        self.messages: List[Dict] = []
        self.started_at = datetime.now(timezone.utc)
        self.initial_topic = initial_topic
        self.emotional_samples: List[str] = []
        self.topics: List[str] = [initial_topic] if initial_topic else []
        self.key_moments: List[str] = []
        self.decisions: List[str] = []
    
    def add_message(
        self,
        role: str,
        content: str,
        emotion: str = None,
        is_key_moment: bool = False
    ):
        """Add a message to the episode being built."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "emotion": emotion
        })
        
        if emotion:
            self.emotional_samples.append(emotion)
        
        if is_key_moment:
            self.key_moments.append(content[:100])
    
    def add_topic(self, topic: str):
        """Add a topic that was discussed."""
        if topic not in self.topics:
            self.topics.append(topic)
    
    def add_decision(self, decision: str):
        """Record a decision made during the episode."""
        self.decisions.append(decision)
    
    def mark_key_moment(self, content: str):
        """Mark something as a key moment."""
        self.key_moments.append(content[:100])
    
    def get_dominant_emotion(self) -> EmotionalTone:
        """Determine the dominant emotional tone."""
        if not self.emotional_samples:
            return EmotionalTone.NEUTRAL
        
        # Count emotions
        counts = {}
        for emotion in self.emotional_samples:
            emotion_lower = emotion.lower()
            if "frustrat" in emotion_lower or "angry" in emotion_lower:
                counts["frustrated"] = counts.get("frustrated", 0) + 1
            elif "happy" in emotion_lower or "excit" in emotion_lower or "great" in emotion_lower:
                counts["positive"] = counts.get("positive", 0) + 1
            elif "urgent" in emotion_lower or "quick" in emotion_lower:
                counts["urgent"] = counts.get("urgent", 0) + 1
            elif "focus" in emotion_lower or "work" in emotion_lower:
                counts["focused"] = counts.get("focused", 0) + 1
            else:
                counts["neutral"] = counts.get("neutral", 0) + 1
        
        if not counts:
            return EmotionalTone.NEUTRAL
        
        dominant = max(counts, key=counts.get)
        return EmotionalTone(dominant)
    
    def infer_type(self) -> EpisodeType:
        """Infer episode type from content."""
        all_content = " ".join(m["content"].lower() for m in self.messages)
        
        if "error" in all_content or "bug" in all_content or "fix" in all_content:
            return EpisodeType.DEBUG_SESSION
        elif "build" in all_content or "create" in all_content or "implement" in all_content:
            return EpisodeType.BUILDING
        elif "plan" in all_content or "strategy" in all_content or "design" in all_content:
            return EpisodeType.PLANNING
        elif "urgent" in all_content or "down" in all_content or "broken" in all_content:
            return EpisodeType.CRISIS
        elif "success" in all_content or "deployed" in all_content or "working" in all_content:
            return EpisodeType.CELEBRATION
        else:
            return EpisodeType.CONVERSATION
    
    def generate_title(self) -> str:
        """Generate a title for the episode."""
        if self.topics:
            return f"Working on {self.topics[0]}"
        
        episode_type = self.infer_type()
        date = self.started_at.strftime("%B %d")
        
        type_titles = {
            EpisodeType.DEBUG_SESSION: f"Debugging session on {date}",
            EpisodeType.BUILDING: f"Building session on {date}",
            EpisodeType.PLANNING: f"Planning session on {date}",
            EpisodeType.CRISIS: f"Resolving issue on {date}",
            EpisodeType.CELEBRATION: f"Success on {date}",
            EpisodeType.CONVERSATION: f"Conversation on {date}"
        }
        
        return type_titles.get(episode_type, f"Session on {date}")
    
    def generate_summary(self) -> str:
        """Generate a summary of the episode."""
        if len(self.messages) < 2:
            return "Brief interaction"
        
        # Use first user message and topics
        first_user = next(
            (m["content"] for m in self.messages if m["role"] == "user"),
            ""
        )
        
        summary_parts = []
        
        if first_user:
            summary_parts.append(f"Started with: '{first_user[:50]}...'")
        
        if self.topics:
            summary_parts.append(f"Covered: {', '.join(self.topics[:3])}")
        
        if self.decisions:
            summary_parts.append(f"Decided: {self.decisions[0][:50]}")
        
        return " ".join(summary_parts) or "Conversation with James"
    
    def finalize(self, outcome: Outcome = Outcome.SUCCESS) -> Episode:
        """Finalize the episode."""
        ended_at = datetime.now(timezone.utc)
        duration = int((ended_at - self.started_at).total_seconds() / 60)
        
        # Extract lessons from the conversation
        lessons = []
        for msg in self.messages:
            content = msg["content"].lower()
            if "learned" in content or "remember" in content or "important" in content:
                lessons.append(msg["content"][:100])
        
        return Episode(
            id=f"ep_{self.chat_id}_{self.started_at.timestamp()}",
            title=self.generate_title(),
            summary=self.generate_summary(),
            episode_type=self.infer_type(),
            emotional_tone=self.get_dominant_emotion(),
            outcome=outcome,
            started_at=self.started_at,
            ended_at=ended_at,
            duration_minutes=duration,
            key_moments=self.key_moments[:5],
            participants=["James", "Aria"],
            topics=self.topics[:5],
            lessons_learned=lessons[:3],
            decisions_made=self.decisions[:5],
            importance=0.5 + (len(self.key_moments) * 0.1)
        )


class EpisodicMemory:
    """
    Stores and retrieves episodic memories.
    
    Features:
    - Store completed episodes
    - Search by time, topic, emotion
    - Get related episodes
    - Narrative generation
    """
    
    def __init__(self):
        self._active_builders: Dict[str, EpisodeBuilder] = {}
        self._ensure_db()
        
        logger.info("📖 Episodic memory initialized")
    
    def _ensure_db(self):
        """Create database and tables."""
        EPISODE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    episode_type TEXT NOT NULL,
                    emotional_tone TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_minutes INTEGER,
                    key_moments TEXT,
                    participants TEXT,
                    topics TEXT,
                    lessons_learned TEXT,
                    decisions_made TEXT,
                    metadata TEXT,
                    importance REAL DEFAULT 0.5
                );
                
                CREATE INDEX IF NOT EXISTS idx_episodes_started ON episodes(started_at DESC);
                CREATE INDEX IF NOT EXISTS idx_episodes_type ON episodes(episode_type);
                CREATE INDEX IF NOT EXISTS idx_episodes_importance ON episodes(importance DESC);
                
                -- Full-text search for narratives
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                    title, summary, topics,
                    content='episodes',
                    content_rowid='rowid'
                );
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(EPISODE_DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def start_episode(self, chat_id: str, topic: str = None) -> EpisodeBuilder:
        """Start building a new episode."""
        builder = EpisodeBuilder(str(chat_id), topic)
        self._active_builders[str(chat_id)] = builder
        return builder
    
    def get_active_builder(self, chat_id: str) -> Optional[EpisodeBuilder]:
        """Get the active episode builder for a chat."""
        return self._active_builders.get(str(chat_id))
    
    def end_episode(
        self,
        chat_id: str,
        outcome: Outcome = Outcome.SUCCESS
    ) -> Optional[Episode]:
        """End and save an episode."""
        builder = self._active_builders.pop(str(chat_id), None)
        
        if not builder:
            return None
        
        # Only save if there was meaningful content
        if len(builder.messages) < 2:
            return None
        
        episode = builder.finalize(outcome)
        self.store(episode)
        
        return episode
    
    def store(self, episode: Episode):
        """Store an episode to database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO episodes
                (id, title, summary, episode_type, emotional_tone, outcome,
                 started_at, ended_at, duration_minutes, key_moments, participants,
                 topics, lessons_learned, decisions_made, metadata, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode.id,
                episode.title,
                episode.summary,
                episode.episode_type.value,
                episode.emotional_tone.value,
                episode.outcome.value,
                episode.started_at.isoformat(),
                episode.ended_at.isoformat() if episode.ended_at else None,
                episode.duration_minutes,
                json.dumps(episode.key_moments),
                json.dumps(episode.participants),
                json.dumps(episode.topics),
                json.dumps(episode.lessons_learned),
                json.dumps(episode.decisions_made),
                json.dumps(episode.metadata),
                episode.importance
            ))
        
        logger.info(f"📖 Stored episode: {episode.title}")
    
    def search(
        self,
        query: str = None,
        episode_type: EpisodeType = None,
        since: datetime = None,
        limit: int = 10
    ) -> List[Episode]:
        """Search episodes."""
        with self._get_connection() as conn:
            conditions = []
            params = []
            
            if query:
                # Use FTS if available, else LIKE
                try:
                    conditions.append("id IN (SELECT rowid FROM episodes_fts WHERE episodes_fts MATCH ?)")
                    params.append(query)
                except:
                    conditions.append("(title LIKE ? OR summary LIKE ? OR topics LIKE ?)")
                    params.extend([f"%{query}%"] * 3)
            
            if episode_type:
                conditions.append("episode_type = ?")
                params.append(episode_type.value)
            
            if since:
                conditions.append("started_at >= ?")
                params.append(since.isoformat())
            
            sql = "SELECT * FROM episodes"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_episode(row) for row in rows]
    
    def get_recent(self, limit: int = 5) -> List[Episode]:
        """Get most recent episodes."""
        return self.search(limit=limit)
    
    def get_by_topic(self, topic: str, limit: int = 5) -> List[Episode]:
        """Get episodes about a topic."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM episodes
                WHERE topics LIKE ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (f"%{topic}%", limit)).fetchall()
            
            return [self._row_to_episode(row) for row in rows]
    
    def get_context_prompt(self, topic: str = None, limit: int = 2) -> str:
        """Get episodic context for prompt injection."""
        if topic:
            episodes = self.get_by_topic(topic, limit)
        else:
            episodes = self.get_recent(limit)
        
        if not episodes:
            return ""
        
        lines = ["\n## 📖 Relevant Past Episodes\n"]
        
        for ep in episodes:
            lines.append(ep.to_narrative())
            lines.append("")
        
        lines.append("---\n")
        
        return "\n".join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get episodic memory statistics."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT episode_type, COUNT(*) FROM episodes GROUP BY episode_type"
            ).fetchall())
            by_outcome = dict(conn.execute(
                "SELECT outcome, COUNT(*) FROM episodes GROUP BY outcome"
            ).fetchall())
            
            return {
                "total_episodes": total,
                "active_builders": len(self._active_builders),
                "by_type": by_type,
                "by_outcome": by_outcome,
                "db_path": str(EPISODE_DB_PATH)
            }
    
    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        """Convert database row to Episode."""
        return Episode(
            id=row["id"],
            title=row["title"],
            summary=row["summary"],
            episode_type=EpisodeType(row["episode_type"]),
            emotional_tone=EmotionalTone(row["emotional_tone"]),
            outcome=Outcome(row["outcome"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            duration_minutes=row["duration_minutes"] or 0,
            key_moments=json.loads(row["key_moments"] or "[]"),
            participants=json.loads(row["participants"] or "[]"),
            topics=json.loads(row["topics"] or "[]"),
            lessons_learned=json.loads(row["lessons_learned"] or "[]"),
            decisions_made=json.loads(row["decisions_made"] or "[]"),
            metadata=json.loads(row["metadata"] or "{}"),
            importance=row["importance"]
        )


# ============================================================================
# SINGLETON
# ============================================================================

_episodic: Optional[EpisodicMemory] = None


def get_episodic_memory() -> EpisodicMemory:
    """Get or create episodic memory instance."""
    global _episodic
    if _episodic is None:
        _episodic = EpisodicMemory()
    return _episodic









