#!/usr/bin/env python3
"""
Thread Carrying System
======================
Extracts and carries open threads across conversations.

A "thread" is something James is working on that spans multiple interactions.
Examples:
- "Working on the membership flow"
- "Stuck on deployment"
- "Trying to figure out X"

The system:
1. Extracts threads from messages
2. Stores them in the continuity ledger
3. Surfaces them naturally in future interactions
4. Auto-resolves after completion or dormancy
"""
import re
import uuid
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger("cis.threads")

@dataclass
class Thread:
    id: str
    description: str
    domain: str
    status: str  # active, dormant, resolved
    opened_at: str
    last_mentioned: str
    mentions: int


# Patterns that indicate a thread
THREAD_PATTERNS = [
    # Working on something
    (r"working on (the |a |)(.+)", "building"),
    (r"building (the |a |)(.+)", "building"),
    (r"implementing (the |a |)(.+)", "building"),
    (r"creating (the |a |)(.+)", "building"),
    
    # Stuck on something
    (r"stuck on (the |a |)(.+)", "building"),
    (r"blocked by (the |a |)(.+)", "building"),
    (r"can't figure out (.+)", "building"),
    
    # Trading related
    (r"looking at (sol|btc|eth|xrp|trading|position)", "trading"),
    (r"monitoring (sol|btc|eth|xrp|the trade)", "trading"),
    (r"waiting for (sol|btc|eth|price|signal)", "trading"),
    
    # Personal
    (r"dealing with (.+)", "personal"),
    (r"handling (.+)", "personal"),
    
    # System
    (r"deploying (.+)", "system"),
    (r"fixing (.+)", "system"),
    (r"debugging (.+)", "system"),
]

# Patterns that indicate resolution
RESOLUTION_PATTERNS = [
    r"got it working",
    r"finished (the |)(.+)",
    r"completed (the |)(.+)",
    r"done with (the |)(.+)",
    r"solved (the |)(.+)",
    r"fixed (the |)(.+)",
    r"deployed (the |)(.+)",
    r"all good now",
    r"working now",
]


class ThreadManager:
    """Manages open threads for continuity."""
    
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db_path = db_path
        self._ensure_table()
    
    def _ensure_table(self):
        """Ensure the open_threads table exists."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_threads (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    description TEXT NOT NULL,
                    domain TEXT,
                    opened_at TEXT DEFAULT (datetime('now')),
                    last_mentioned TEXT DEFAULT (datetime('now')),
                    status TEXT DEFAULT 'active',
                    mentions INTEGER DEFAULT 1,
                    resolved_at TEXT,
                    resolution TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Could not ensure thread table: {e}")
    
    def extract_threads(self, message: str) -> List[Dict]:
        """Extract potential threads from a message."""
        msg_lower = message.lower()
        threads = []
        
        for pattern, domain in THREAD_PATTERNS:
            match = re.search(pattern, msg_lower)
            if match:
                # Get the captured group (the thing they're working on)
                groups = match.groups()
                description = groups[-1].strip() if groups else match.group(0)
                
                # Clean up
                description = description.strip(".,!?")
                if len(description) < 3 or len(description) > 100:
                    continue
                
                threads.append({
                    "description": description,
                    "domain": domain
                })
        
        return threads
    
    def check_resolution(self, message: str) -> bool:
        """Check if message indicates thread resolution."""
        msg_lower = message.lower()
        
        for pattern in RESOLUTION_PATTERNS:
            if re.search(pattern, msg_lower):
                return True
        
        return False
    
    def process_message(self, user_id: str, message: str) -> Dict:
        """
        Process a message for thread updates.
        
        Returns:
            {
                "new_threads": [...],
                "mentioned_threads": [...],
                "resolved_threads": [...]
            }
        """
        result = {
            "new_threads": [],
            "mentioned_threads": [],
            "resolved_threads": []
        }
        
        # Check for resolution first
        if self.check_resolution(message):
            # Try to resolve matching threads
            active = self.get_active_threads(user_id)
            msg_lower = message.lower()
            
            for thread in active:
                # Check if thread description is mentioned
                if thread.description.lower() in msg_lower:
                    self.resolve_thread(thread.id, "completed")
                    result["resolved_threads"].append(thread)
        
        # Extract new threads
        extracted = self.extract_threads(message)
        
        for ext in extracted:
            # Check if this thread already exists
            existing = self.find_similar_thread(user_id, ext["description"])
            
            if existing:
                # Update existing thread
                self.touch_thread(existing.id)
                result["mentioned_threads"].append(existing)
            else:
                # Create new thread
                thread = self.create_thread(user_id, ext["description"], ext["domain"])
                if thread:
                    result["new_threads"].append(thread)
        
        return result
    
    def create_thread(self, user_id: str, description: str, domain: str) -> Optional[Thread]:
        """Create a new open thread."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            thread_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO open_threads (id, user_id, description, domain, opened_at, last_mentioned, status, mentions)
                VALUES (?, ?, ?, ?, ?, ?, 'active', 1)
            """, (thread_id, user_id, description, domain, now, now))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created thread: {description}")
            
            return Thread(
                id=thread_id,
                description=description,
                domain=domain,
                status="active",
                opened_at=now,
                last_mentioned=now,
                mentions=1
            )
        except Exception as e:
            logger.error(f"Could not create thread: {e}")
            return None
    
    def get_active_threads(self, user_id: str) -> List[Thread]:
        """Get all active threads for a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, description, domain, status, opened_at, last_mentioned, mentions
                FROM open_threads
                WHERE user_id = ? AND status = 'active'
                ORDER BY last_mentioned DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                Thread(
                    id=r[0], description=r[1], domain=r[2], status=r[3],
                    opened_at=r[4], last_mentioned=r[5], mentions=r[6]
                )
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Could not get threads: {e}")
            return []
    
    def find_similar_thread(self, user_id: str, description: str) -> Optional[Thread]:
        """Find an existing thread similar to this description."""
        active = self.get_active_threads(user_id)
        desc_lower = description.lower()
        
        for thread in active:
            thread_lower = thread.description.lower()
            
            # Check for overlap
            if desc_lower in thread_lower or thread_lower in desc_lower:
                return thread
            
            # Check word overlap
            desc_words = set(desc_lower.split())
            thread_words = set(thread_lower.split())
            overlap = len(desc_words & thread_words) / max(len(desc_words), 1)
            
            if overlap > 0.5:
                return thread
        
        return None
    
    def touch_thread(self, thread_id: str):
        """Update last_mentioned and increment mentions."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE open_threads 
                SET last_mentioned = datetime('now'), mentions = mentions + 1
                WHERE id = ?
            """, (thread_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Could not touch thread: {e}")
    
    def resolve_thread(self, thread_id: str, resolution: str):
        """Mark a thread as resolved."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE open_threads 
                SET status = 'resolved', resolved_at = datetime('now'), resolution = ?
                WHERE id = ?
            """, (resolution, thread_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Resolved thread: {thread_id}")
        except Exception as e:
            logger.error(f"Could not resolve thread: {e}")
    
    def auto_dormant(self, user_id: str, days: int = 7):
        """Mark threads as dormant if not mentioned in N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            cursor.execute("""
                UPDATE open_threads 
                SET status = 'dormant'
                WHERE user_id = ? AND status = 'active' AND last_mentioned < ?
            """, (user_id, cutoff))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Could not mark dormant: {e}")
    
    def get_thread_context(self, user_id: str) -> str:
        """Get a natural language summary of open threads."""
        threads = self.get_active_threads(user_id)
        
        if not threads:
            return ""
        
        if len(threads) == 1:
            return f"Open thread: {threads[0].description}"
        
        thread_list = ", ".join(t.description for t in threads[:3])
        return f"Open threads: {thread_list}"


# Singleton
_manager: Optional[ThreadManager] = None

def get_thread_manager() -> ThreadManager:
    global _manager
    if _manager is None:
        _manager = ThreadManager()
    return _manager

def extract_threads(message: str) -> List[Dict]:
    """Extract threads from a message."""
    return get_thread_manager().extract_threads(message)

def process_message_threads(user_id: str, message: str) -> Dict:
    """Process a message for thread updates."""
    return get_thread_manager().process_message(user_id, message)

def get_active_threads(user_id: str) -> List[Thread]:
    """Get active threads for a user."""
    return get_thread_manager().get_active_threads(user_id)

def get_thread_context(user_id: str) -> str:
    """Get thread context for prompts."""
    return get_thread_manager().get_thread_context(user_id)








