#!/usr/bin/env python3
"""
Report Scheduler
================
Determines when to send reports based on:
- Time of day
- User state
- Activity levels
- Learned patterns

Constraints:
- Max 8 proactive messages/day
- No messages during sleep/focus
- Batch when possible
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("reports.scheduler")


class ReportType(Enum):
    MORNING_BRIEF = "morning_brief"
    PROGRESS = "progress"
    STATUS = "status"
    HEADS_UP = "heads_up"
    DECISION = "decision"
    DIGEST = "digest"


@dataclass
class ScheduledReport:
    """A scheduled report."""
    report_type: ReportType
    scheduled_for: datetime
    priority: int  # 0 = critical, 4 = low
    can_batch: bool
    data: Dict


class ReportScheduler:
    """
    Schedules reports based on timing and state.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/reports.db"):
        self.db_path = db_path
        self.user_id = "james"
        self._ensure_tables()
        
        # Default schedule (can be learned)
        self.schedule = {
            "wake_time": 7,      # 7am
            "morning_brief": 8,  # 8am
            "status_intervals": [12, 16, 20],  # noon, 4pm, 8pm
            "digest_time": 21,   # 9pm
            "sleep_start": 23,   # 11pm
            "sleep_end": 6,      # 6am
        }
        
        # Constraints
        self.max_reports_per_day = 8
        self.min_gap_minutes = 30
    
    def _ensure_tables(self):
        """Create scheduler tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Scheduled reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_reports (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                report_type TEXT,
                scheduled_for TEXT,
                priority INTEGER DEFAULT 3,
                can_batch INTEGER DEFAULT 1,
                data TEXT,
                status TEXT DEFAULT 'pending',
                sent_at TEXT
            )
        """)
        
        # Report history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_history (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                report_type TEXT,
                content TEXT,
                sent_at TEXT DEFAULT (datetime('now')),
                user_state TEXT,
                user_intensity INTEGER
            )
        """)
        
        # Daily counts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_counts (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                date TEXT,
                count INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_today_count(self) -> int:
        """Get reports sent today."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT count FROM daily_counts
            WHERE user_id = ? AND date = ?
        """, (self.user_id, today))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 0
    
    def _increment_count(self):
        """Increment today's count."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO daily_counts (id, user_id, date, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET count = count + 1
        """, (f"{self.user_id}:{today}", self.user_id, today))
        
        conn.commit()
        conn.close()
    
    def _get_last_report_time(self) -> Optional[datetime]:
        """Get time of last report sent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT sent_at FROM report_history
            WHERE user_id = ?
            ORDER BY sent_at DESC
            LIMIT 1
        """, (self.user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            try:
                return datetime.fromisoformat(row[0])
            except:
                pass
        return None
    
    def is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours (sleep time)."""
        hour = datetime.now().hour
        
        if self.schedule["sleep_start"] > self.schedule["sleep_end"]:
            # Sleep spans midnight (e.g., 11pm - 6am)
            return hour >= self.schedule["sleep_start"] or hour < self.schedule["sleep_end"]
        else:
            return self.schedule["sleep_start"] <= hour < self.schedule["sleep_end"]
    
    def can_send_report(self, priority: int = 3) -> tuple:
        """
        Check if we can send a report now.
        
        Returns: (can_send, reason)
        """
        # Check quiet hours (except critical)
        if priority > 0 and self.is_quiet_hours():
            return False, "quiet_hours"
        
        # Check daily limit
        today_count = self._get_today_count()
        if today_count >= self.max_reports_per_day:
            if priority > 1:  # Allow critical and high priority
                return False, "daily_limit"
        
        # Check min gap
        last_time = self._get_last_report_time()
        if last_time:
            minutes_since = (datetime.now() - last_time).total_seconds() / 60
            if minutes_since < self.min_gap_minutes and priority > 1:
                return False, f"too_soon ({int(minutes_since)}m since last)"
        
        return True, "ok"
    
    def get_next_report_time(self, report_type: ReportType) -> Optional[datetime]:
        """Get next scheduled time for a report type."""
        now = datetime.now()
        
        if report_type == ReportType.MORNING_BRIEF:
            target_hour = self.schedule["morning_brief"]
            target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if now.hour >= target_hour:
                target += timedelta(days=1)
            return target
        
        elif report_type == ReportType.STATUS:
            for hour in self.schedule["status_intervals"]:
                if now.hour < hour:
                    return now.replace(hour=hour, minute=0, second=0, microsecond=0)
            # Next day
            return now.replace(hour=self.schedule["status_intervals"][0], minute=0) + timedelta(days=1)
        
        elif report_type == ReportType.DIGEST:
            target_hour = self.schedule["digest_time"]
            target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if now.hour >= target_hour:
                target += timedelta(days=1)
            return target
        
        return None
    
    def should_send_morning_brief(self) -> bool:
        """Check if we should send morning brief now."""
        now = datetime.now()
        hour = now.hour
        
        # Within 30 minutes of morning brief time
        if abs(hour - self.schedule["morning_brief"]) > 1:
            return False
        
        # Check if already sent today
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = now.strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT id FROM report_history
            WHERE user_id = ? AND report_type = 'morning_brief' AND date(sent_at) = ?
        """, (self.user_id, today))
        
        already_sent = cursor.fetchone() is not None
        conn.close()
        
        return not already_sent
    
    def should_send_status(self) -> bool:
        """Check if we should send a status report now."""
        now = datetime.now()
        hour = now.hour
        
        # Check if it's a status hour
        is_status_hour = hour in self.schedule["status_intervals"]
        if not is_status_hour:
            return False
        
        # Check if already sent this hour
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hour_start = now.replace(minute=0, second=0, microsecond=0).isoformat()
        
        cursor.execute("""
            SELECT id FROM report_history
            WHERE user_id = ? AND report_type = 'status' AND sent_at >= ?
        """, (self.user_id, hour_start))
        
        already_sent = cursor.fetchone() is not None
        conn.close()
        
        return not already_sent
    
    def should_send_digest(self) -> bool:
        """Check if we should send daily digest now."""
        now = datetime.now()
        hour = now.hour
        
        # Within digest time window
        if abs(hour - self.schedule["digest_time"]) > 1:
            return False
        
        # Check if already sent today
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = now.strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT id FROM report_history
            WHERE user_id = ? AND report_type = 'digest' AND date(sent_at) = ?
        """, (self.user_id, today))
        
        already_sent = cursor.fetchone() is not None
        conn.close()
        
        return not already_sent
    
    def record_report_sent(self, report_type: str, content: str, user_state: str = "", user_intensity: int = 0):
        """Record that a report was sent."""
        import uuid
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO report_history (id, user_id, report_type, content, user_state, user_intensity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), self.user_id, report_type, content, user_state, user_intensity))
        
        conn.commit()
        conn.close()
        
        self._increment_count()
        logger.info(f"Report sent: {report_type}")


# Singleton
_scheduler: Optional[ReportScheduler] = None

def get_scheduler() -> ReportScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ReportScheduler()
    return _scheduler








