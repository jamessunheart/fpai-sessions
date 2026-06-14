#!/usr/bin/env python3
"""
Signal Consolidation Engine
============================
Central engine for processing all incoming signals.

Pipeline:
1. Source identification
2. Sender recognition
3. Content analysis
4. Priority calculation
5. Decision: Handle | Queue | Escalate

Channels:
- Telegram (primary)
- Email (Gmail)
- Calendar events
- Public interface requests
"""
import uuid
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

from .priority import calculate_priority, PriorityLevel, PriorityResult
from .contacts import get_contact_manager, get_contact_info

logger = logging.getLogger("signals.engine")


class SignalStatus(Enum):
    PENDING = "pending"
    HANDLED = "handled"
    ESCALATED = "escalated"
    ARCHIVED = "archived"


class SignalAction(Enum):
    IMMEDIATE = "immediate"
    NEXT_REPORT = "next_report"
    DAILY_BATCH = "daily_batch"
    WEEKLY_DIGEST = "weekly_digest"
    FILTER = "filter"


@dataclass
class Signal:
    """An incoming signal from any channel."""
    id: str
    channel: str
    sender: str
    sender_id: Optional[str]
    content: str
    content_summary: str
    priority: PriorityLevel
    action: SignalAction
    status: SignalStatus
    received_at: str
    processed_at: Optional[str]
    metadata: Dict


class SignalEngine:
    """
    Central signal processing engine.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/signals.db"):
        self.db_path = db_path
        self.contact_manager = get_contact_manager()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create signal tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                channel TEXT,
                sender TEXT,
                sender_id TEXT,
                content TEXT,
                content_summary TEXT,
                priority INTEGER,
                action TEXT,
                status TEXT DEFAULT 'pending',
                received_at TEXT DEFAULT (datetime('now')),
                processed_at TEXT,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def process_signal(
        self,
        channel: str,
        sender: str,
        content: str,
        sender_id: str = None,
        metadata: Dict = None
    ) -> Signal:
        """
        Process an incoming signal.
        
        Args:
            channel: Source channel (telegram, email, public, etc)
            sender: Sender name or identifier
            content: Signal content
            sender_id: Sender ID (email, telegram ID, etc)
            metadata: Additional signal data
        
        Returns:
            Processed Signal object
        """
        # Get contact info for priority calculation
        contact_info = None
        if sender_id:
            contact_info = get_contact_info(sender_id)
        
        # Calculate priority
        priority_result = calculate_priority(
            content=content,
            sender=sender,
            channel=channel,
            contact_info=contact_info
        )
        
        # Create summary (first 100 chars)
        summary = content[:100] + "..." if len(content) > 100 else content
        
        # Determine action
        action = SignalAction(priority_result.action)
        
        # Create signal
        signal = Signal(
            id=str(uuid.uuid4()),
            channel=channel,
            sender=sender,
            sender_id=sender_id,
            content=content,
            content_summary=summary,
            priority=priority_result.level,
            action=action,
            status=SignalStatus.PENDING,
            received_at=datetime.now().isoformat(),
            processed_at=None,
            metadata=metadata or {}
        )
        
        # Save to database
        self._save_signal(signal)
        
        # Log activity
        try:
            from presence import log_activity
            log_activity("signal", f"Signal from {sender} via {channel}", "received")
        except:
            pass
        
        logger.info(f"Signal processed: {channel}/{sender} -> P{priority_result.level.value}")
        return signal
    
    def _save_signal(self, signal: Signal):
        """Save signal to database."""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO signals (id, channel, sender, sender_id, content, content_summary,
                                priority, action, status, received_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.id, signal.channel, signal.sender, signal.sender_id,
            signal.content, signal.content_summary, signal.priority.value,
            signal.action.value, signal.status.value, signal.received_at,
            json.dumps(signal.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def update_status(self, signal_id: str, status: SignalStatus):
        """Update signal status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE signals 
            SET status = ?, processed_at = datetime('now')
            WHERE id = ?
        """, (status.value, signal_id))
        
        conn.commit()
        conn.close()
    
    def get_pending_signals(self, action: SignalAction = None) -> List[Signal]:
        """Get pending signals, optionally filtered by action."""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if action:
            cursor.execute("""
                SELECT id, channel, sender, sender_id, content, content_summary,
                       priority, action, status, received_at, processed_at, metadata
                FROM signals 
                WHERE status = 'pending' AND action = ?
                ORDER BY priority ASC, received_at ASC
            """, (action.value,))
        else:
            cursor.execute("""
                SELECT id, channel, sender, sender_id, content, content_summary,
                       priority, action, status, received_at, processed_at, metadata
                FROM signals 
                WHERE status = 'pending'
                ORDER BY priority ASC, received_at ASC
            """)
        
        signals = []
        for row in cursor.fetchall():
            signals.append(Signal(
                id=row[0], channel=row[1], sender=row[2], sender_id=row[3],
                content=row[4], content_summary=row[5], priority=PriorityLevel(row[6]),
                action=SignalAction(row[7]), status=SignalStatus(row[8]),
                received_at=row[9], processed_at=row[10], metadata=json.loads(row[11])
            ))
        
        conn.close()
        return signals
    
    def get_signals_for_report(self, report_type: str) -> List[Signal]:
        """Get signals for a specific report type."""
        action_map = {
            "morning_brief": SignalAction.IMMEDIATE,
            "status": SignalAction.NEXT_REPORT,
            "digest": SignalAction.DAILY_BATCH
        }
        
        action = action_map.get(report_type)
        if action:
            return self.get_pending_signals(action)
        return []
    
    def batch_signals(self) -> Dict[str, List[Signal]]:
        """Batch signals by action type."""
        pending = self.get_pending_signals()
        
        batches = {
            "immediate": [],
            "next_report": [],
            "daily_batch": [],
            "weekly_digest": []
        }
        
        for signal in pending:
            if signal.action.value in batches:
                batches[signal.action.value].append(signal)
        
        return batches
    
    async def poll_all_channels(self):
        """Poll all configured channels for new signals."""
        signals = []
        
        # Poll Gmail
        try:
            from .gmail import fetch_unread_emails
            emails = await fetch_unread_emails()
            
            for email in emails:
                signal = self.process_signal(
                    channel="email",
                    sender=email.sender,
                    content=f"{email.subject}\n\n{email.body}",
                    sender_id=email.sender_email,
                    metadata={"email_id": email.id, "subject": email.subject}
                )
                signals.append(signal)
        except Exception as e:
            logger.debug(f"Gmail poll error: {e}")
        
        # Poll Calendar for heads-up events
        try:
            from .calendar import get_heads_up_events
            events = await get_heads_up_events()
            
            for event in events:
                signal = self.process_signal(
                    channel="calendar",
                    sender="Calendar",
                    content=f"Upcoming: {event['name']} in {event['time_until']}",
                    metadata=event
                )
                signals.append(signal)
        except Exception as e:
            logger.debug(f"Calendar poll error: {e}")
        
        return signals


# Singleton
_engine: Optional[SignalEngine] = None

def get_signal_engine() -> SignalEngine:
    global _engine
    if _engine is None:
        _engine = SignalEngine()
    return _engine


def process_signal(channel: str, sender: str, content: str, sender_id: str = None) -> Signal:
    return get_signal_engine().process_signal(channel, sender, content, sender_id)


async def poll_channels():
    return await get_signal_engine().poll_all_channels()








