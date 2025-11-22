"""Event routing and history management"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from collections import deque
from .models import Event, EventType

logger = logging.getLogger(__name__)


class EventRouter:
    """Manages event history and routing"""

    def __init__(self, max_history: int = 1000, retention_hours: int = 1):
        self.max_history = max_history
        self.retention_hours = retention_hours

        # Circular buffer for event history
        self.event_history: deque = deque(maxlen=max_history)

        # Metrics
        self.events_total = 0
        self.events_by_type = {}
        self.last_event_time = None

    def create_event(
        self,
        event_type: EventType,
        session_id: str,
        payload: dict,
        ttl: int = 3600
    ) -> Event:
        """Create a new event with generated ID"""
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            payload=payload,
            ttl=ttl
        )

        # Store in history
        self.event_history.append(event)

        # Update metrics
        self.events_total += 1
        self.last_event_time = event.timestamp

        event_type_str = str(event_type)
        self.events_by_type[event_type_str] = self.events_by_type.get(event_type_str, 0) + 1

        logger.debug(f"Created event: {event.event_type} from {session_id}")

        return event

    def get_history(
        self,
        since: Optional[datetime] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Event]:
        """Retrieve event history with filters"""
        events = list(self.event_history)

        # Filter by timestamp
        if since:
            events = [e for e in events if e.timestamp >= since]

        # Filter by event type (supports wildcards)
        if event_type:
            if event_type.endswith(".*"):
                prefix = event_type[:-2]
                events = [e for e in events if str(e.event_type).startswith(prefix + ".")]
            else:
                events = [e for e in events if str(e.event_type) == event_type]

        # Apply limit
        events = events[-limit:]

        return events

    def prune_expired(self):
        """Remove expired events from history"""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self.retention_hours)

        # Filter out expired events
        valid_events = [
            event for event in self.event_history
            if event.timestamp >= cutoff
        ]

        pruned_count = len(self.event_history) - len(valid_events)

        if pruned_count > 0:
            self.event_history = deque(valid_events, maxlen=self.max_history)
            logger.info(f"Pruned {pruned_count} expired events")

    def get_metrics(self) -> dict:
        """Get event router metrics"""
        return {
            "events_total": self.events_total,
            "events_in_history": len(self.event_history),
            "events_by_type": self.events_by_type,
            "last_event_time": self.last_event_time
        }

    def get_events_per_second(self, window_seconds: int = 60) -> float:
        """Calculate events per second over a time window"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        recent_events = [
            e for e in self.event_history
            if e.timestamp >= cutoff
        ]

        if not recent_events:
            return 0.0

        return len(recent_events) / window_seconds
