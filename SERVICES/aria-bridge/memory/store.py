"""
ARIA MEMORY STORE
=================

Core memory storage system using SQLite.

Memory layers:
- Identity: Who Sunheart is (permanent)
- Context: Current state (changes daily/weekly)
- Conversation: Recent exchanges (rolling window)
- Learning: Patterns and insights (grows over time)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

logger = logging.getLogger("aria.memory.store")

# Database path
MEMORY_DB = Path("/opt/fpai/aria-bridge/memory/memory.db")


class MemoryCategory(str, Enum):
    """Categories of memory."""
    IDENTITY = "identity"           # Who Sunheart is
    CONTEXT = "context"             # Current state
    CONVERSATION = "conversation"   # Exchanges
    LEARNING = "learning"           # Insights
    PREFERENCE = "preference"       # Discovered preferences
    DECISION = "decision"           # Decisions made
    OUTCOME = "outcome"             # Results of actions
    PATTERN = "pattern"             # Detected patterns


class MemoryImportance(str, Enum):
    """Importance levels."""
    CRITICAL = "critical"   # Never forget (identity, major decisions)
    HIGH = "high"          # Remember long-term
    MEDIUM = "medium"      # Standard retention
    LOW = "low"            # Can be compressed/forgotten


@dataclass
class Memory:
    """A single memory entry."""
    id: str
    content: str
    category: MemoryCategory
    importance: MemoryImportance
    created_at: str
    updated_at: str
    
    # Optional metadata
    source: Optional[str] = None      # Where this came from
    related_ids: Optional[List[str]] = None  # Related memories
    tags: Optional[List[str]] = None
    embedding: Optional[List[float]] = None  # For semantic search
    
    # For conversation memories
    user_message: Optional[str] = None
    aria_response: Optional[str] = None
    dimension: Optional[str] = None
    
    # For learning memories
    action: Optional[str] = None
    outcome: Optional[str] = None
    insight: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MemoryStore:
    """
    Core memory storage.
    
    Handles CRUD operations for all memory types.
    """
    
    def __init__(self, db_path: Path = MEMORY_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"MemoryStore initialized: {self.db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Main memories table
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                importance TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT,
                related_ids TEXT,
                tags TEXT,
                embedding TEXT,
                user_message TEXT,
                aria_response TEXT,
                dimension TEXT,
                action TEXT,
                outcome TEXT,
                insight TEXT,
                compressed INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0
            )
        """)
        
        # Identity table (special - key-value for core identity)
        c.execute("""
            CREATE TABLE IF NOT EXISTS identity (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'core',
                updated_at TEXT NOT NULL
            )
        """)
        
        # Context table (current state)
        c.execute("""
            CREATE TABLE IF NOT EXISTS context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'state',
                updated_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)
        
        # Summaries table (compressed conversations)
        c.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id TEXT PRIMARY KEY,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                summary TEXT NOT NULL,
                themes TEXT,
                decisions TEXT,
                outcomes TEXT,
                memory_count INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        
        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_memories_compressed ON memories(compressed)")
        
        conn.commit()
        conn.close()
    
    def _generate_id(self, content: str, category: str) -> str:
        """Generate a unique memory ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        hash_input = f"{content[:100]}_{category}_{timestamp}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"mem_{category[:4]}_{short_hash}"
    
    # ==================== STORE OPERATIONS ====================
    
    def store(
        self,
        content: str,
        category: MemoryCategory,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        source: str = None,
        tags: List[str] = None,
        related_ids: List[str] = None,
        **kwargs
    ) -> Memory:
        """
        Store a new memory.
        
        Args:
            content: The memory content
            category: Memory category
            importance: How important this is
            source: Where this memory came from
            tags: Tags for categorization
            related_ids: IDs of related memories
            **kwargs: Additional fields (user_message, aria_response, etc.)
        """
        memory_id = self._generate_id(content, category.value)
        now = datetime.utcnow().isoformat()
        
        memory = Memory(
            id=memory_id,
            content=content,
            category=category,
            importance=importance,
            created_at=now,
            updated_at=now,
            source=source,
            related_ids=related_ids or [],
            tags=tags or [],
            **kwargs
        )
        
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO memories 
            (id, content, category, importance, created_at, updated_at,
             source, related_ids, tags, embedding, user_message, aria_response,
             dimension, action, outcome, insight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
            memory.content,
            memory.category.value,
            memory.importance.value,
            memory.created_at,
            memory.updated_at,
            memory.source,
            json.dumps(memory.related_ids),
            json.dumps(memory.tags),
            json.dumps(memory.embedding) if memory.embedding else None,
            memory.user_message,
            memory.aria_response,
            memory.dimension,
            memory.action,
            memory.outcome,
            memory.insight
        ))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Stored memory: {memory_id} [{category.value}]")
        return memory
    
    def store_exchange(
        self,
        user_message: str,
        aria_response: str,
        dimension: str = None,
        importance: MemoryImportance = MemoryImportance.MEDIUM
    ) -> Memory:
        """Store a conversation exchange."""
        content = f"User: {user_message[:200]}\nAria: {aria_response[:200]}"
        
        return self.store(
            content=content,
            category=MemoryCategory.CONVERSATION,
            importance=importance,
            user_message=user_message,
            aria_response=aria_response,
            dimension=dimension,
            source="conversation"
        )
    
    # ==================== RETRIEVE OPERATIONS ====================
    
    def get(self, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return self._row_to_memory(row)
        return None
    
    def get_by_category(
        self,
        category: MemoryCategory,
        limit: int = 50,
        include_compressed: bool = False
    ) -> List[Memory]:
        """Get memories by category."""
        conn = self._get_conn()
        c = conn.cursor()
        
        if include_compressed:
            c.execute("""
                SELECT * FROM memories 
                WHERE category = ? AND archived = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (category.value, limit))
        else:
            c.execute("""
                SELECT * FROM memories 
                WHERE category = ? AND compressed = 0 AND archived = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (category.value, limit))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_memory(row) for row in rows]
    
    def get_recent(
        self,
        limit: int = 20,
        categories: List[MemoryCategory] = None
    ) -> List[Memory]:
        """Get recent memories."""
        conn = self._get_conn()
        c = conn.cursor()
        
        if categories:
            placeholders = ",".join("?" * len(categories))
            c.execute(f"""
                SELECT * FROM memories 
                WHERE category IN ({placeholders}) AND compressed = 0 AND archived = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, [cat.value for cat in categories] + [limit])
        else:
            c.execute("""
                SELECT * FROM memories 
                WHERE compressed = 0 AND archived = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_memory(row) for row in rows]
    
    def get_conversations(self, limit: int = 20) -> List[Memory]:
        """Get recent conversation memories."""
        return self.get_by_category(MemoryCategory.CONVERSATION, limit)
    
    def search_content(self, query: str, limit: int = 10) -> List[Memory]:
        """Simple text search in memory content."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM memories 
            WHERE content LIKE ? AND archived = 0
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """, (f"%{query}%", limit))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_memory(row) for row in rows]
    
    def _row_to_memory(self, row) -> Memory:
        """Convert database row to Memory object."""
        return Memory(
            id=row["id"],
            content=row["content"],
            category=MemoryCategory(row["category"]),
            importance=MemoryImportance(row["importance"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source=row["source"],
            related_ids=json.loads(row["related_ids"]) if row["related_ids"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            embedding=json.loads(row["embedding"]) if row["embedding"] else None,
            user_message=row["user_message"],
            aria_response=row["aria_response"],
            dimension=row["dimension"],
            action=row["action"],
            outcome=row["outcome"],
            insight=row["insight"]
        )
    
    # ==================== IDENTITY OPERATIONS ====================
    
    def set_identity(self, key: str, value: Any, category: str = "core"):
        """Set an identity value."""
        conn = self._get_conn()
        c = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        c.execute("""
            INSERT OR REPLACE INTO identity (key, value, category, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, value_str, category, now))
        
        conn.commit()
        conn.close()
    
    def get_identity(self, key: str = None) -> Any:
        """Get identity value(s)."""
        conn = self._get_conn()
        c = conn.cursor()
        
        if key:
            c.execute("SELECT value FROM identity WHERE key = ?", (key,))
            row = c.fetchone()
            conn.close()
            if row:
                try:
                    return json.loads(row["value"])
                except:
                    return row["value"]
            return None
        else:
            c.execute("SELECT key, value, category FROM identity")
            rows = c.fetchall()
            conn.close()
            
            identity = {}
            for row in rows:
                try:
                    identity[row["key"]] = json.loads(row["value"])
                except:
                    identity[row["key"]] = row["value"]
            return identity
    
    # ==================== CONTEXT OPERATIONS ====================
    
    def set_context(self, key: str, value: Any, expires_hours: int = None):
        """Set a context value."""
        conn = self._get_conn()
        c = conn.cursor()
        
        now = datetime.utcnow()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        expires_at = (now + timedelta(hours=expires_hours)).isoformat() if expires_hours else None
        
        c.execute("""
            INSERT OR REPLACE INTO context (key, value, updated_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (key, value_str, now.isoformat(), expires_at))
        
        conn.commit()
        conn.close()
    
    def get_context(self, key: str = None) -> Any:
        """Get context value(s)."""
        conn = self._get_conn()
        c = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        if key:
            c.execute("""
                SELECT value FROM context 
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (key, now))
            row = c.fetchone()
            conn.close()
            if row:
                try:
                    return json.loads(row["value"])
                except:
                    return row["value"]
            return None
        else:
            c.execute("""
                SELECT key, value FROM context 
                WHERE expires_at IS NULL OR expires_at > ?
            """, (now,))
            rows = c.fetchall()
            conn.close()
            
            context = {}
            for row in rows:
                try:
                    context[row["key"]] = json.loads(row["value"])
                except:
                    context[row["key"]] = row["value"]
            return context
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Count by category
        c.execute("""
            SELECT category, COUNT(*) as count FROM memories 
            WHERE archived = 0
            GROUP BY category
        """)
        by_category = {row["category"]: row["count"] for row in c.fetchall()}
        
        # Count by importance
        c.execute("""
            SELECT importance, COUNT(*) as count FROM memories 
            WHERE archived = 0
            GROUP BY importance
        """)
        by_importance = {row["importance"]: row["count"] for row in c.fetchall()}
        
        # Total and compressed
        c.execute("SELECT COUNT(*) as total FROM memories WHERE archived = 0")
        total = c.fetchone()["total"]
        
        c.execute("SELECT COUNT(*) as compressed FROM memories WHERE compressed = 1")
        compressed = c.fetchone()["compressed"]
        
        # Identity count
        c.execute("SELECT COUNT(*) as count FROM identity")
        identity_count = c.fetchone()["count"]
        
        conn.close()
        
        return {
            "total_memories": total,
            "compressed": compressed,
            "by_category": by_category,
            "by_importance": by_importance,
            "identity_keys": identity_count
        }


# Singleton
_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get or create memory store instance."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store


