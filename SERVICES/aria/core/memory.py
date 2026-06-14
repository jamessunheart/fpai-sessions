"""
ARIA MEMORY SYSTEM
==================

Persistent conversation memory using SQLite.

Features:
- Per-user conversation history (last 10 exchanges)
- User preferences storage
- Cross-channel context sync
- Past decision tracking
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading

logger = logging.getLogger("aria.memory")

# Database path
MEMORY_DB = Path("/opt/fpai/aria/memory.db")


@dataclass
class Message:
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    channel: str  # "telegram", "dashboard", "api"
    model_used: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class UserProfile:
    """User preferences and context."""
    user_id: str
    name: Optional[str] = None
    preferred_channel: str = "telegram"
    communication_style: str = "friendly"  # friendly, technical, brief
    interests: List[str] = None
    trading_risk_level: str = "moderate"  # conservative, moderate, aggressive
    last_active: Optional[str] = None
    total_conversations: int = 0
    metadata: Optional[Dict] = None


class AriaMemory:
    """
    Persistent memory system for Aria.
    
    Stores:
    - Conversation history per user (last 10 exchanges)
    - User profiles and preferences
    - Past decisions and their outcomes
    - Cross-channel context
    """
    
    def __init__(self, db_path: Path = MEMORY_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        logger.info(f"Memory initialized: {self.db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Conversation history table
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                channel TEXT NOT NULL,
                model_used TEXT,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # User profiles table
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                preferred_channel TEXT DEFAULT 'telegram',
                communication_style TEXT DEFAULT 'friendly',
                interests TEXT,
                trading_risk_level TEXT DEFAULT 'moderate',
                total_conversations INTEGER DEFAULT 0,
                last_active TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Decisions tracking table
        c.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                context TEXT,
                decision TEXT NOT NULL,
                outcome TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Context facts (things Aria learned about the user)
        c.execute("""
            CREATE TABLE IF NOT EXISTS context_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                timestamp TEXT NOT NULL,
                UNIQUE(user_id, fact_type)
            )
        """)
        
        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_facts_user ON context_facts(user_id)")
        
        conn.commit()
    
    # ======================= MESSAGE HISTORY =======================
    
    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        channel: str = "telegram",
        model_used: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Add a message to conversation history."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO messages (user_id, role, content, channel, model_used, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, role, content, channel, model_used,
            json.dumps(metadata) if metadata else None,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        
        # Update user profile
        self._update_user_activity(user_id)
        
        # Auto-extract context facts from user messages
        if role == "user":
            self._extract_facts(user_id, content)
    
    def get_history(
        self,
        user_id: str,
        limit: int = 10,
        channel: Optional[str] = None
    ) -> List[Message]:
        """Get recent conversation history for a user."""
        conn = self._get_conn()
        c = conn.cursor()
        
        if channel:
            c.execute("""
                SELECT * FROM messages 
                WHERE user_id = ? AND channel = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, channel, limit))
        else:
            c.execute("""
                SELECT * FROM messages 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
        
        rows = c.fetchall()
        return [
            Message(
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                channel=row["channel"],
                model_used=row["model_used"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None
            )
            for row in reversed(rows)  # Return in chronological order
        ]
    
    def get_history_as_text(self, user_id: str, limit: int = 10) -> str:
        """Get conversation history formatted for AI prompts."""
        messages = self.get_history(user_id, limit)
        if not messages:
            return ""
        
        lines = ["Recent conversation:"]
        for msg in messages:
            prefix = "User:" if msg.role == "user" else "Aria:"
            # Truncate long messages
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            lines.append(f"{prefix} {content}")
        
        return "\n".join(lines)
    
    # ======================= USER PROFILES =======================
    
    def get_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        if row:
            return UserProfile(
                user_id=row["user_id"],
                name=row["name"],
                preferred_channel=row["preferred_channel"],
                communication_style=row["communication_style"],
                interests=json.loads(row["interests"]) if row["interests"] else [],
                trading_risk_level=row["trading_risk_level"],
                last_active=row["last_active"],
                total_conversations=row["total_conversations"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None
            )
        else:
            # Create default profile
            profile = UserProfile(user_id=user_id)
            self.save_profile(profile)
            return profile
    
    def save_profile(self, profile: UserProfile):
        """Save user profile."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO user_profiles 
            (user_id, name, preferred_channel, communication_style, interests,
             trading_risk_level, total_conversations, last_active, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            profile.user_id,
            profile.name,
            profile.preferred_channel,
            profile.communication_style,
            json.dumps(profile.interests) if profile.interests else None,
            profile.trading_risk_level,
            profile.total_conversations,
            profile.last_active,
            json.dumps(profile.metadata) if profile.metadata else None
        ))
        
        conn.commit()
    
    def _update_user_activity(self, user_id: str):
        """Update user's last activity and conversation count."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Ensure profile exists
        c.execute("SELECT 1 FROM user_profiles WHERE user_id = ?", (user_id,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO user_profiles (user_id, last_active, total_conversations)
                VALUES (?, datetime('now'), 1)
            """, (user_id,))
        else:
            c.execute("""
                UPDATE user_profiles 
                SET last_active = datetime('now'),
                    total_conversations = total_conversations + 1,
                    updated_at = datetime('now')
                WHERE user_id = ?
            """, (user_id,))
        
        conn.commit()
    
    # ======================= CONTEXT FACTS =======================
    
    def set_fact(
        self,
        user_id: str,
        fact_type: str,
        fact_value: str,
        confidence: float = 1.0,
        source: str = "conversation"
    ):
        """Store a fact about the user."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO context_facts 
            (user_id, fact_type, fact_value, confidence, source, timestamp)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (user_id, fact_type, fact_value, confidence, source))
        
        conn.commit()
    
    def get_fact(self, user_id: str, fact_type: str) -> Optional[str]:
        """Get a specific fact about the user."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT fact_value FROM context_facts 
            WHERE user_id = ? AND fact_type = ?
        """, (user_id, fact_type))
        
        row = c.fetchone()
        return row["fact_value"] if row else None
    
    def get_all_facts(self, user_id: str) -> Dict[str, str]:
        """Get all facts about a user."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT fact_type, fact_value FROM context_facts 
            WHERE user_id = ?
        """, (user_id,))
        
        return {row["fact_type"]: row["fact_value"] for row in c.fetchall()}
    
    def _extract_facts(self, user_id: str, message: str):
        """Extract facts from user message."""
        message_lower = message.lower()
        
        # Extract name mentions
        if "my name is" in message_lower:
            try:
                name = message_lower.split("my name is")[1].strip().split()[0].capitalize()
                self.set_fact(user_id, "name", name, confidence=0.9)
            except:
                pass
        elif "i'm " in message_lower and len(message_lower.split("i'm ")[1].split()) > 0:
            try:
                word = message_lower.split("i'm ")[1].split()[0]
                if word[0].isupper() or len(word) < 10:  # Likely a name
                    self.set_fact(user_id, "name", word.capitalize(), confidence=0.5)
            except:
                pass
        
        # Extract trading preferences
        if any(w in message_lower for w in ["conservative", "safe", "low risk"]):
            self.set_fact(user_id, "risk_preference", "conservative")
        elif any(w in message_lower for w in ["aggressive", "high risk", "yolo"]):
            self.set_fact(user_id, "risk_preference", "aggressive")
        
        # Extract interests
        if "interested in" in message_lower:
            try:
                interest = message_lower.split("interested in")[1].strip().split(".")[0]
                existing = self.get_fact(user_id, "interests") or ""
                if interest not in existing:
                    new_interests = f"{existing}, {interest}" if existing else interest
                    self.set_fact(user_id, "interests", new_interests)
            except:
                pass
    
    # ======================= DECISIONS =======================
    
    def record_decision(
        self,
        user_id: str,
        decision_type: str,
        context: str,
        decision: str
    ):
        """Record a decision made for the user."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO decisions (user_id, decision_type, context, decision, timestamp)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (user_id, decision_type, context, decision))
        
        conn.commit()
    
    def get_past_decisions(
        self,
        user_id: str,
        decision_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Get past decisions for a user."""
        conn = self._get_conn()
        c = conn.cursor()
        
        if decision_type:
            c.execute("""
                SELECT * FROM decisions 
                WHERE user_id = ? AND decision_type = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (user_id, decision_type, limit))
        else:
            c.execute("""
                SELECT * FROM decisions 
                WHERE user_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (user_id, limit))
        
        return [dict(row) for row in c.fetchall()]
    
    # ======================= CONTEXT BUILDING =======================
    
    def build_context(self, user_id: str) -> Dict[str, Any]:
        """Build full context for AI prompts."""
        profile = self.get_profile(user_id)
        facts = self.get_all_facts(user_id)
        history = self.get_history_as_text(user_id, limit=10)
        past_decisions = self.get_past_decisions(user_id, limit=3)
        
        return {
            "user": {
                "id": user_id,
                "name": facts.get("name", profile.name),
                "style": profile.communication_style,
                "risk_level": facts.get("risk_preference", profile.trading_risk_level),
                "interests": facts.get("interests", ""),
                "total_conversations": profile.total_conversations,
            },
            "history": history,
            "facts": facts,
            "recent_decisions": [
                {"type": d.get("decision_type"), "decision": d.get("decision")}
                for d in past_decisions
            ]
        }
    
    def format_context_for_prompt(self, user_id: str) -> str:
        """Format context for inclusion in AI prompts."""
        ctx = self.build_context(user_id)
        
        lines = []
        
        # User info
        if ctx["user"]["name"]:
            lines.append(f"User: {ctx['user']['name']}")
        lines.append(f"Communication style: {ctx['user']['style']}")
        if ctx["user"]["interests"]:
            lines.append(f"Interests: {ctx['user']['interests']}")
        lines.append(f"Trading risk level: {ctx['user']['risk_level']}")
        
        # History
        if ctx["history"]:
            lines.append("")
            lines.append(ctx["history"])
        
        return "\n".join(lines)


# Singleton instance
_memory: Optional[AriaMemory] = None


def get_memory() -> AriaMemory:
    """Get or create the global memory instance."""
    global _memory
    if _memory is None:
        _memory = AriaMemory()
    return _memory


