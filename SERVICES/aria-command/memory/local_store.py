"""
ARIA LOCAL MEMORY STORE
========================

SQLite-based local memory storage.

This provides:
- Redundant fallback when Mem0 is unavailable
- Fast local search for frequently accessed memories
- Offline capability
- Sync queue for eventual consistency with cloud

The goal: Memory that NEVER fails.
"""

import os
import sqlite3
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from pathlib import Path
from contextlib import contextmanager
from enum import Enum
import asyncio

logger = logging.getLogger("aria.memory.local")

# Configuration
DB_PATH = Path(os.getenv("ARIA_MEMORY_DB", "/opt/fpai/aria-command/state/memory.db"))
SYNC_QUEUE_PATH = Path(os.getenv("ARIA_SYNC_QUEUE", "/opt/fpai/aria-command/state/sync_queue.db"))


class MemoryType(str, Enum):
    """Types of memories."""
    FACT = "fact"           # Static knowledge
    LEARNING = "learning"   # Learned patterns
    EPISODE = "episode"     # Conversation/event narrative
    PREFERENCE = "preference"  # User preferences
    IDENTITY = "identity"   # Self-knowledge
    CORRECTION = "correction"  # Learned corrections


class SyncStatus(str, Enum):
    """Sync status for cloud backup."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass
class LocalMemory:
    """A memory stored locally."""
    id: str
    content: str
    memory_type: MemoryType
    importance: float  # 0-1
    created_at: datetime
    last_accessed: datetime
    access_count: int
    decay_factor: float  # 0-1, decreases over time
    metadata: Dict[str, Any]
    sync_status: SyncStatus
    mem0_id: Optional[str] = None  # ID in Mem0 cloud
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "decay_factor": self.decay_factor,
            "metadata": self.metadata,
            "sync_status": self.sync_status.value,
            "mem0_id": self.mem0_id
        }
    
    def effective_importance(self) -> float:
        """Get importance adjusted for decay and access frequency."""
        # More accesses = more important
        access_boost = min(0.2, self.access_count * 0.02)
        return min(1.0, self.importance * self.decay_factor + access_boost)


class LocalMemoryStore:
    """
    SQLite-based local memory storage.
    
    Features:
    - Fast full-text search
    - Importance decay over time
    - Sync queue for Mem0 backup
    - Automatic consolidation
    """
    
    def __init__(self):
        self._ensure_db()
        logger.info(f"📚 Local memory store initialized at {DB_PATH}")
    
    def _ensure_db(self):
        """Create database and tables if they don't exist."""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            conn.executescript("""
                -- Main memories table
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    decay_factor REAL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    sync_status TEXT DEFAULT 'pending',
                    mem0_id TEXT
                );
                
                -- Full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    content='memories',
                    content_rowid='rowid'
                );
                
                -- Triggers to keep FTS in sync
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END;
                
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                END;
                
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END;
                
                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
                CREATE INDEX IF NOT EXISTS idx_memories_sync ON memories(sync_status);
                CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
                
                -- Sync queue for Mem0 backup
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT
                );
            """)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _generate_id(self, content: str) -> str:
        """Generate a unique ID for a memory."""
        timestamp = datetime.now(timezone.utc).isoformat()
        hash_input = f"{content}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.LEARNING,
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> LocalMemory:
        """
        Store a new memory.
        
        Args:
            content: The memory content
            memory_type: Type of memory
            importance: 0-1 importance score
            metadata: Optional additional data
        
        Returns:
            The stored LocalMemory
        """
        memory_id = self._generate_id(content)
        now = datetime.now(timezone.utc)
        
        memory = LocalMemory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=min(1.0, max(0.0, importance)),
            created_at=now,
            last_accessed=now,
            access_count=0,
            decay_factor=1.0,
            metadata=metadata or {},
            sync_status=SyncStatus.PENDING
        )
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO memories (id, content, memory_type, importance, created_at, 
                                       last_accessed, access_count, decay_factor, metadata, sync_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.content,
                memory.memory_type.value,
                memory.importance,
                memory.created_at.isoformat(),
                memory.last_accessed.isoformat(),
                memory.access_count,
                memory.decay_factor,
                json.dumps(memory.metadata),
                memory.sync_status.value
            ))
            
            # Add to sync queue
            conn.execute("""
                INSERT INTO sync_queue (memory_id, action, created_at)
                VALUES (?, 'store', ?)
            """, (memory.id, now.isoformat()))
        
        logger.info(f"💾 Stored local memory: {content[:50]}...")
        return memory
    
    def search(
        self,
        query: str,
        limit: int = 5,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0
    ) -> List[LocalMemory]:
        """
        Search memories using full-text search.
        
        Args:
            query: Search query
            limit: Max results
            memory_type: Filter by type
            min_importance: Minimum importance threshold
        
        Returns:
            List of matching LocalMemory objects
        """
        with self._get_connection() as conn:
            # Build query
            sql = """
                SELECT m.*, bm25(memories_fts) as rank
                FROM memories m
                JOIN memories_fts ON m.rowid = memories_fts.rowid
                WHERE memories_fts MATCH ?
                AND m.importance >= ?
            """
            params = [query, min_importance]
            
            if memory_type:
                sql += " AND m.memory_type = ?"
                params.append(memory_type.value)
            
            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)
            
            try:
                rows = conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                # FTS query failed, fall back to LIKE
                sql = """
                    SELECT * FROM memories
                    WHERE content LIKE ?
                    AND importance >= ?
                """
                params = [f"%{query}%", min_importance]
                
                if memory_type:
                    sql += " AND memory_type = ?"
                    params.append(memory_type.value)
                
                sql += " ORDER BY importance DESC LIMIT ?"
                params.append(limit)
                
                rows = conn.execute(sql, params).fetchall()
            
            memories = []
            for row in rows:
                mem = self._row_to_memory(row)
                memories.append(mem)
                
                # Update access tracking
                self._record_access(conn, mem.id)
            
            return memories
    
    def get_by_id(self, memory_id: str) -> Optional[LocalMemory]:
        """Get a specific memory by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            
            if row:
                mem = self._row_to_memory(row)
                self._record_access(conn, mem.id)
                return mem
            return None
    
    def get_recent(
        self,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[LocalMemory]:
        """Get most recent memories."""
        with self._get_connection() as conn:
            sql = "SELECT * FROM memories"
            params = []
            
            if memory_type:
                sql += " WHERE memory_type = ?"
                params.append(memory_type.value)
            
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_memory(row) for row in rows]
    
    def get_important(
        self,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[LocalMemory]:
        """Get most important memories (adjusted for decay)."""
        with self._get_connection() as conn:
            sql = """
                SELECT *, (importance * decay_factor + MIN(0.2, access_count * 0.02)) as effective_importance
                FROM memories
            """
            params = []
            
            if memory_type:
                sql += " WHERE memory_type = ?"
                params.append(memory_type.value)
            
            sql += " ORDER BY effective_importance DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_memory(row) for row in rows]
    
    def update_importance(self, memory_id: str, new_importance: float):
        """Update a memory's importance."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE memories SET importance = ? WHERE id = ?",
                (min(1.0, max(0.0, new_importance)), memory_id)
            )
    
    def delete(self, memory_id: str):
        """Delete a memory."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.execute(
                "INSERT INTO sync_queue (memory_id, action, created_at) VALUES (?, 'delete', ?)",
                (memory_id, datetime.now(timezone.utc).isoformat())
            )
    
    def apply_decay(self, decay_rate: float = 0.001):
        """
        Apply decay to all memories.
        
        Should be run periodically (e.g., daily).
        Memories that are accessed frequently resist decay.
        """
        with self._get_connection() as conn:
            # Decay memories that haven't been accessed recently
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            conn.execute("""
                UPDATE memories
                SET decay_factor = MAX(0.1, decay_factor - ?)
                WHERE last_accessed < ?
                AND decay_factor > 0.1
            """, (decay_rate, cutoff))
            
            affected = conn.execute("SELECT changes()").fetchone()[0]
            if affected > 0:
                logger.info(f"Applied decay to {affected} memories")
    
    def get_pending_sync(self, limit: int = 50) -> List[Tuple[str, str]]:
        """Get memories pending sync to Mem0."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT memory_id, action FROM sync_queue
                WHERE attempts < 3
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [(row["memory_id"], row["action"]) for row in rows]
    
    def mark_synced(self, memory_id: str, mem0_id: str = None):
        """Mark a memory as synced to Mem0."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE memories SET sync_status = ?, mem0_id = ? WHERE id = ?",
                (SyncStatus.SYNCED.value, mem0_id, memory_id)
            )
            conn.execute(
                "DELETE FROM sync_queue WHERE memory_id = ?",
                (memory_id,)
            )
    
    def mark_sync_failed(self, memory_id: str, error: str):
        """Mark a sync attempt as failed."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_queue
                SET attempts = attempts + 1, last_error = ?
                WHERE memory_id = ?
            """, (error, memory_id))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            by_type = dict(conn.execute(
                "SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type"
            ).fetchall())
            pending_sync = conn.execute(
                "SELECT COUNT(*) FROM sync_queue WHERE attempts < 3"
            ).fetchone()[0]
            avg_importance = conn.execute(
                "SELECT AVG(importance * decay_factor) FROM memories"
            ).fetchone()[0] or 0
            
            return {
                "total_memories": total,
                "by_type": by_type,
                "pending_sync": pending_sync,
                "avg_effective_importance": round(avg_importance, 3),
                "db_path": str(DB_PATH)
            }
    
    def _row_to_memory(self, row: sqlite3.Row) -> LocalMemory:
        """Convert a database row to LocalMemory."""
        return LocalMemory(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            importance=row["importance"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            access_count=row["access_count"],
            decay_factor=row["decay_factor"],
            metadata=json.loads(row["metadata"]),
            sync_status=SyncStatus(row["sync_status"]),
            mem0_id=row["mem0_id"]
        )
    
    def _record_access(self, conn: sqlite3.Connection, memory_id: str):
        """Record that a memory was accessed."""
        conn.execute("""
            UPDATE memories
            SET last_accessed = ?, access_count = access_count + 1
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), memory_id))


# ============================================================================
# SINGLETON
# ============================================================================

_store: Optional[LocalMemoryStore] = None


def get_local_store() -> LocalMemoryStore:
    """Get or create local memory store."""
    global _store
    if _store is None:
        _store = LocalMemoryStore()
    return _store









