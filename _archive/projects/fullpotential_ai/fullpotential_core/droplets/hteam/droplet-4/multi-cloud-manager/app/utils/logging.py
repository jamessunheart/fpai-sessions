"""
Structured logging utilities
Following CODE_STANDARDS logging patterns
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from collections import deque

from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s","droplet_id":' + str(settings.droplet_id) + '}'
)

logger = logging.getLogger(__name__)

# In-memory storage for UDC compliance
recent_events = deque(maxlen=100)
recent_logs = deque(maxlen=1000)
last_actions = deque(maxlen=50)


class StructuredLogger:
    """Structured logging class"""
    
    @staticmethod
    def info(event: str, **kwargs):
        """Log info level"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "event": event,
            "droplet_id": settings.droplet_id,
            **kwargs
        }
        recent_logs.append(log_entry)
        logger.info(json.dumps(log_entry))
    
    @staticmethod
    def warning(event: str, **kwargs):
        """Log warning level"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "WARNING",
            "event": event,
            "droplet_id": settings.droplet_id,
            **kwargs
        }
        recent_logs.append(log_entry)
        logger.warning(json.dumps(log_entry))
    
    @staticmethod
    def error(event: str, **kwargs):
        """Log error level"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "event": event,
            "droplet_id": settings.droplet_id,
            **kwargs
        }
        recent_logs.append(log_entry)
        logger.error(json.dumps(log_entry))
    
    @staticmethod
    def debug(event: str, **kwargs):
        """Log debug level"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "DEBUG",
            "event": event,
            "droplet_id": settings.droplet_id,
            **kwargs
        }
        recent_logs.append(log_entry)
        logger.debug(json.dumps(log_entry))


log = StructuredLogger()


def log_event(event_type: str, details: Dict[str, Any], trace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Log an event to the event stream
    
    Args:
        event_type: Type of event (e.g., "droplet_startup", "api_call")
        details: Event details dictionary
        trace_id: Optional trace ID for correlation
    
    Returns:
        Event dictionary with generated event_id
    """
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "droplet_id": settings.droplet_id,
        "trace_id": trace_id or str(uuid.uuid4()),
        "details": details
    }
    recent_events.append(event)
    log.info(f"event_{event_type}", trace_id=event["trace_id"], **details)
    return event


def record_action(action: str, trace_id: str) -> Dict[str, Any]:
    """
    Record an action for proof generation
    
    Args:
        action: Action description
        trace_id: Trace ID for correlation
    
    Returns:
        Proof dictionary with signature
    """
    proof = {
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
        "trace_id": trace_id,
        "droplet_id": settings.droplet_id,
        "signature": f"proof_{uuid.uuid4().hex[:16]}"
    }
    last_actions.append(proof)
    log.info("action_recorded", action=action, trace_id=trace_id)
    return proof


def get_recent_logs(limit: int = 100, level: Optional[str] = None) -> list:
    """Get recent logs with optional filtering"""
    logs = list(recent_logs)
    
    if level:
        logs = [log_entry for log_entry in logs if log_entry["level"] == level.upper()]
    
    return logs[-limit:]


def get_recent_events(limit: int = 50, event_type: Optional[str] = None) -> list:
    """Get recent events with optional filtering"""
    events = list(recent_events)
    
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    
    return events[-limit:]


def get_last_action() -> Optional[Dict[str, Any]]:
    """Get the last recorded action"""
    if not last_actions:
        return None
    return last_actions[-1]
