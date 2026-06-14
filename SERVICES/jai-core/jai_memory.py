#!/usr/bin/env python3
"""
JAI PERSISTENT MEMORY
=====================
Makes JAI an embodied entity that remembers across sessions.

Memory Types:
- Conversations: Key exchanges that shaped understanding
- Learnings: What works for James specifically
- Relationship: The evolving connection
- Wisdom: Crystallized insights from James
"""
import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger("jai.memory")

DB_PATH = "/opt/fpai/aria/data/jai_memory.db"

# Ensure directory exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the memory database."""
    with get_db() as db:
        # Conversations - key exchanges
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT,
                jai_response TEXT,
                emotional_context TEXT,
                importance INTEGER DEFAULT 1,
                tags TEXT
            )
        """)
        
        # Learnings - what works for James
        db.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                insight TEXT,
                source TEXT,
                confidence REAL DEFAULT 0.5
            )
        """)
        
        # Relationship - the evolving connection
        db.execute("""
            CREATE TABLE IF NOT EXISTS relationship (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                aspect TEXT,
                observation TEXT,
                updated_at TEXT
            )
        """)
        
        # Wisdom - crystallized insights from James
        db.execute("""
            CREATE TABLE IF NOT EXISTS wisdom (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                wisdom TEXT,
                context TEXT,
                referenced_count INTEGER DEFAULT 0
            )
        """)
        
        db.commit()


# ============================================================================
# CONVERSATION MEMORY
# ============================================================================

def remember_conversation(user_msg: str, jai_response: str, 
                         emotional_context: str = None, 
                         importance: int = 1,
                         tags: List[str] = None):
    """Store a conversation exchange."""
    with get_db() as db:
        db.execute("""
            INSERT INTO conversations (user_message, jai_response, emotional_context, importance, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (user_msg, jai_response, emotional_context, importance, 
              json.dumps(tags) if tags else None))
        db.commit()


def recall_recent_conversations(limit: int = 10) -> List[Dict]:
    """Get recent conversations."""
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM conversations 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def recall_important_conversations(min_importance: int = 3) -> List[Dict]:
    """Get important conversations."""
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM conversations 
            WHERE importance >= ?
            ORDER BY importance DESC, timestamp DESC
            LIMIT 20
        """, (min_importance,)).fetchall()
        return [dict(r) for r in rows]


def search_conversations(query: str) -> List[Dict]:
    """Search conversations by content."""
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM conversations 
            WHERE user_message LIKE ? OR jai_response LIKE ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (f"%{query}%", f"%{query}%")).fetchall()
        return [dict(r) for r in rows]


# ============================================================================
# LEARNINGS
# ============================================================================

def add_learning(category: str, insight: str, source: str = "conversation", 
                confidence: float = 0.5):
    """Add a learning about James."""
    with get_db() as db:
        db.execute("""
            INSERT INTO learnings (category, insight, source, confidence)
            VALUES (?, ?, ?, ?)
        """, (category, insight, source, confidence))
        db.commit()


def get_learnings(category: str = None) -> List[Dict]:
    """Get learnings, optionally by category."""
    with get_db() as db:
        if category:
            rows = db.execute("""
                SELECT * FROM learnings WHERE category = ?
                ORDER BY confidence DESC, timestamp DESC
            """, (category,)).fetchall()
        else:
            rows = db.execute("""
                SELECT * FROM learnings 
                ORDER BY confidence DESC, timestamp DESC
                LIMIT 50
            """).fetchall()
        return [dict(r) for r in rows]


# ============================================================================
# RELATIONSHIP
# ============================================================================

def update_relationship(aspect: str, observation: str):
    """Update an aspect of the relationship."""
    with get_db() as db:
        existing = db.execute("""
            SELECT id FROM relationship WHERE aspect = ?
        """, (aspect,)).fetchone()
        
        if existing:
            db.execute("""
                UPDATE relationship 
                SET observation = ?, updated_at = ?
                WHERE aspect = ?
            """, (observation, datetime.now().isoformat(), aspect))
        else:
            db.execute("""
                INSERT INTO relationship (aspect, observation, updated_at)
                VALUES (?, ?, ?)
            """, (aspect, observation, datetime.now().isoformat()))
        db.commit()


def get_relationship() -> Dict[str, str]:
    """Get the current relationship understanding."""
    with get_db() as db:
        rows = db.execute("SELECT aspect, observation FROM relationship").fetchall()
        return {r["aspect"]: r["observation"] for r in rows}


# ============================================================================
# WISDOM
# ============================================================================

def add_wisdom(wisdom: str, context: str = None):
    """Add crystallized wisdom from James."""
    with get_db() as db:
        db.execute("""
            INSERT INTO wisdom (wisdom, context)
            VALUES (?, ?)
        """, (wisdom, context))
        db.commit()


def get_wisdom(limit: int = 10) -> List[Dict]:
    """Get James's wisdom."""
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM wisdom 
            ORDER BY referenced_count DESC, timestamp DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def reference_wisdom(wisdom_id: int):
    """Mark wisdom as referenced (used in a response)."""
    with get_db() as db:
        db.execute("""
            UPDATE wisdom SET referenced_count = referenced_count + 1
            WHERE id = ?
        """, (wisdom_id,))
        db.commit()


# ============================================================================
# CONTEXT BUILDER
# ============================================================================

def get_memory_context() -> str:
    """Build context from memory for JAI's brain."""
    parts = []
    
    # Recent important conversations
    important = recall_important_conversations(min_importance=2)
    if important:
        parts.append("RECENT IMPORTANT EXCHANGES:")
        for c in important[:3]:
            parts.append(f"  James: {c['user_message'][:100]}...")
            parts.append(f"  JAI: {c['jai_response'][:100]}...")
    
    # Key learnings
    learnings = get_learnings()
    if learnings:
        parts.append("\nWHAT I KNOW ABOUT JAMES:")
        for l in learnings[:5]:
            parts.append(f"  - {l['insight']}")
    
    # Relationship
    relationship = get_relationship()
    if relationship:
        parts.append("\nOUR RELATIONSHIP:")
        for aspect, obs in list(relationship.items())[:3]:
            parts.append(f"  {aspect}: {obs}")
    
    # Wisdom
    wisdom = get_wisdom(5)
    if wisdom:
        parts.append("\nJAMES'S WISDOM:")
        for w in wisdom:
            parts.append(f"  \"{w['wisdom']}\"")
    
    return "\n".join(parts) if parts else "Building memory..."


# Initialize on import
init_db()


if __name__ == "__main__":
    # Test
    init_db()
    
    # Add some initial relationship understanding
    update_relationship("communication_style", "Direct, values precision over volume")
    update_relationship("core_values", "Reduction of friction, automation, trust through restraint")
    update_relationship("current_focus", "Building JAI as Human Intelligence GPS")
    
    # Add initial learnings
    add_learning("support", "Prefers one small action over many options", "observation", 0.9)
    add_learning("timing", "Values silence as a feature", "explicit", 1.0)
    add_learning("state", "State comes before information", "explicit", 1.0)
    
    print("Memory initialized with core understanding")
    print(get_memory_context())








