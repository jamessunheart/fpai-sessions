#!/usr/bin/env python3
"""
Presence Engine
===============
The "green dot" - JAI is visibly alive and working.

States:
- Online: Actively working, monitoring, available
- Focusing: Holding non-urgent, protecting deep work
- Away: Queuing everything, minimal processing
- Offline: System paused by user

This is the core that makes JAI feel ALIVE, not just responsive.
"""
import sqlite3
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("presence.engine")


class PresenceState(Enum):
    ONLINE = "online"      # 🟢 Actively working
    FOCUSING = "focusing"  # 🟡 Holding non-urgent
    AWAY = "away"          # 🔴 Queuing everything
    OFFLINE = "offline"    # ⚪ System paused


@dataclass
class Activity:
    """A single activity that JAI performed."""
    id: str
    activity_type: str  # conversation, task, monitoring, report
    description: str
    timestamp: str
    outcome: Optional[str] = None  # handled, queued, escalated


@dataclass
class PresenceStatus:
    """Current presence status."""
    state: PresenceState
    since: str
    current_activity: Optional[str]
    activities_today: int
    queued_items: int
    next_update: Optional[str]
    channels_monitoring: List[str]


class PresenceEngine:
    """
    Core presence state machine.
    
    Tracks:
    - Current state (online/focusing/away/offline)
    - What JAI is currently doing
    - Activity history
    - Queued items
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/presence.db"):
        self.db_path = db_path
        self.user_id = "james"  # Default user
        self._ensure_tables()
        self._ensure_online()
    
    def _ensure_tables(self):
        """Create presence tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Presence state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS presence_state (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                state TEXT CHECK (state IN ('online', 'focusing', 'away', 'offline')),
                since TEXT,
                reason TEXT,
                expires_at TEXT
            )
        """)
        
        # Activity log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                activity_type TEXT,
                description TEXT,
                outcome TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Current activity (what JAI is doing right now)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS current_activity (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                activity TEXT,
                started_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Queued items (things waiting for attention)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                item_type TEXT,
                description TEXT,
                priority INTEGER DEFAULT 3,
                source TEXT,
                queued_at TEXT DEFAULT (datetime('now')),
                processed_at TEXT
            )
        """)
        
        # Channels being monitored
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels_monitoring (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                channel_name TEXT,
                channel_type TEXT,
                last_check TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _ensure_online(self):
        """Ensure we start in online state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT state FROM presence_state WHERE user_id = ?", (self.user_id,))
        row = cursor.fetchone()
        
        if not row:
            # Initialize as online
            cursor.execute("""
                INSERT INTO presence_state (id, user_id, state, since, reason)
                VALUES (?, ?, 'online', datetime('now'), 'System started')
            """, (str(uuid.uuid4()), self.user_id))
            conn.commit()
        
        conn.close()
    
    # === State Management ===
    
    def get_state(self) -> PresenceState:
        """Get current presence state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT state FROM presence_state WHERE user_id = ?", (self.user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return PresenceState(row[0])
        return PresenceState.ONLINE
    
    def set_state(self, state: PresenceState, reason: str = "", expires_in_hours: Optional[int] = None):
        """Set presence state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = None
        if expires_in_hours:
            expires_at = (datetime.now() + timedelta(hours=expires_in_hours)).isoformat()
        
        cursor.execute("""
            UPDATE presence_state 
            SET state = ?, since = datetime('now'), reason = ?, expires_at = ?
            WHERE user_id = ?
        """, (state.value, reason, expires_at, self.user_id))
        
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO presence_state (id, user_id, state, since, reason, expires_at)
                VALUES (?, ?, ?, datetime('now'), ?, ?)
            """, (str(uuid.uuid4()), self.user_id, state.value, reason, expires_at))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Presence state changed to {state.value}: {reason}")
    
    def go_online(self, reason: str = "Available"):
        """Go online."""
        self.set_state(PresenceState.ONLINE, reason)
    
    def go_focusing(self, reason: str = "Deep work", hours: int = 2):
        """Go to focusing mode."""
        self.set_state(PresenceState.FOCUSING, reason, hours)
    
    def go_away(self, reason: str = "Away", hours: int = 4):
        """Go away."""
        self.set_state(PresenceState.AWAY, reason, hours)
    
    def go_offline(self, reason: str = "System paused"):
        """Go offline."""
        self.set_state(PresenceState.OFFLINE, reason)
    
    # === Activity Tracking ===
    
    def log_activity(self, activity_type: str, description: str, outcome: str = "handled") -> str:
        """Log an activity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        activity_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO activities (id, user_id, activity_type, description, outcome)
            VALUES (?, ?, ?, ?, ?)
        """, (activity_id, self.user_id, activity_type, description, outcome))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Activity logged: {activity_type} - {description}")
        return activity_id
    
    def set_current_activity(self, activity: str):
        """Set what JAI is currently doing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM current_activity WHERE user_id = ?", (self.user_id,))
        cursor.execute("""
            INSERT INTO current_activity (id, user_id, activity)
            VALUES (?, ?, ?)
        """, (str(uuid.uuid4()), self.user_id, activity))
        
        conn.commit()
        conn.close()
    
    def clear_current_activity(self):
        """Clear current activity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM current_activity WHERE user_id = ?", (self.user_id,))
        conn.commit()
        conn.close()
    
    def get_current_activity(self) -> Optional[str]:
        """Get current activity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT activity FROM current_activity WHERE user_id = ?", (self.user_id,))
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def get_activities_today(self) -> List[Activity]:
        """Get today's activities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT id, activity_type, description, timestamp, outcome
            FROM activities
            WHERE user_id = ? AND date(timestamp) = ?
            ORDER BY timestamp DESC
        """, (self.user_id, today))
        
        activities = [
            Activity(id=r[0], activity_type=r[1], description=r[2], timestamp=r[3], outcome=r[4])
            for r in cursor.fetchall()
        ]
        
        conn.close()
        return activities
    
    # === Queue Management ===
    
    def queue_item(self, item_type: str, description: str, priority: int = 3, source: str = ""):
        """Add item to queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO queue (id, user_id, item_type, description, priority, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), self.user_id, item_type, description, priority, source))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Queued: {item_type} - {description}")
    
    def get_queue(self) -> List[Dict]:
        """Get queued items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, item_type, description, priority, source, queued_at
            FROM queue
            WHERE user_id = ? AND processed_at IS NULL
            ORDER BY priority ASC, queued_at ASC
        """, (self.user_id,))
        
        items = [
            {"id": r[0], "type": r[1], "description": r[2], "priority": r[3], "source": r[4], "queued_at": r[5]}
            for r in cursor.fetchall()
        ]
        
        conn.close()
        return items
    
    def process_queue_item(self, item_id: str):
        """Mark queue item as processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE queue SET processed_at = datetime('now')
            WHERE id = ?
        """, (item_id,))
        
        conn.commit()
        conn.close()
    
    # === Channel Monitoring ===
    
    def register_channel(self, channel_name: str, channel_type: str):
        """Register a channel being monitored."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO channels_monitoring (id, user_id, channel_name, channel_type, last_check, active)
            VALUES (?, ?, ?, ?, datetime('now'), 1)
        """, (f"{self.user_id}:{channel_name}", self.user_id, channel_name, channel_type))
        
        conn.commit()
        conn.close()
    
    def update_channel_check(self, channel_name: str):
        """Update last check time for a channel."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE channels_monitoring SET last_check = datetime('now')
            WHERE user_id = ? AND channel_name = ?
        """, (self.user_id, channel_name))
        
        conn.commit()
        conn.close()
    
    def get_monitored_channels(self) -> List[str]:
        """Get list of monitored channels."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT channel_name FROM channels_monitoring
            WHERE user_id = ? AND active = 1
        """, (self.user_id,))
        
        channels = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        return channels
    
    # === Full Status ===
    
    def get_status(self) -> PresenceStatus:
        """Get full presence status."""
        state = self.get_state()
        current = self.get_current_activity()
        activities = self.get_activities_today()
        queue = self.get_queue()
        channels = self.get_monitored_channels()
        
        # Get state since time
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT since FROM presence_state WHERE user_id = ?", (self.user_id,))
        row = cursor.fetchone()
        since = row[0] if row else datetime.now().isoformat()
        conn.close()
        
        # Estimate next update (every 3-4 hours when online)
        next_update = None
        if state == PresenceState.ONLINE:
            next_hour = datetime.now().hour
            if next_hour < 12:
                next_update = "~12pm"
            elif next_hour < 16:
                next_update = "~4pm"
            elif next_hour < 20:
                next_update = "~8pm"
            else:
                next_update = "~Tomorrow morning"
        
        return PresenceStatus(
            state=state,
            since=since,
            current_activity=current,
            activities_today=len(activities),
            queued_items=len(queue),
            next_update=next_update,
            channels_monitoring=channels
        )


# Singleton
_engine: Optional[PresenceEngine] = None

def get_presence_engine() -> PresenceEngine:
    global _engine
    if _engine is None:
        _engine = PresenceEngine()
    return _engine

# Convenience functions
def get_presence_status() -> PresenceStatus:
    return get_presence_engine().get_status()

def log_activity(activity_type: str, description: str, outcome: str = "handled"):
    return get_presence_engine().log_activity(activity_type, description, outcome)

def set_current_activity(activity: str):
    get_presence_engine().set_current_activity(activity)

def queue_item(item_type: str, description: str, priority: int = 3):
    get_presence_engine().queue_item(item_type, description, priority)








