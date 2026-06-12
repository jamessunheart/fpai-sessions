"""WebSocket connection manager for NEXUS"""
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket
from datetime import datetime
from .models import ConnectedSession, Event, EventType

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message routing"""

    def __init__(self):
        # session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # session_id -> ConnectedSession
        self.sessions: Dict[str, ConnectedSession] = {}

        # session_id -> set of topic patterns
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, session_info: ConnectedSession):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.sessions[session_id] = session_info
        self.subscriptions[session_id] = set()

        logger.info(f"Session {session_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.subscriptions:
            del self.subscriptions[session_id]

        logger.info(f"Session {session_id} disconnected. Remaining connections: {len(self.active_connections)}")

    def subscribe(self, session_id: str, topics: List[str]):
        """Subscribe a session to topics"""
        if session_id not in self.subscriptions:
            self.subscriptions[session_id] = set()

        for topic in topics:
            self.subscriptions[session_id].add(topic)

        logger.info(f"Session {session_id} subscribed to: {topics}")

    def unsubscribe(self, session_id: str, topics: List[str]):
        """Unsubscribe a session from topics"""
        if session_id in self.subscriptions:
            for topic in topics:
                self.subscriptions[session_id].discard(topic)

        logger.info(f"Session {session_id} unsubscribed from: {topics}")

    def matches_topic(self, event_type: str, topic_pattern: str) -> bool:
        """Check if event_type matches topic pattern (supports wildcards)"""
        # Exact match
        if event_type == topic_pattern:
            return True

        # Wildcard match (e.g., "work.*" matches "work.claimed")
        if topic_pattern.endswith(".*"):
            prefix = topic_pattern[:-2]
            return event_type.startswith(prefix + ".")

        # Broadcast matches everything
        if topic_pattern == "broadcast":
            return True

        return False

    async def broadcast(self, event: Event, exclude_sender: bool = False):
        """Broadcast event to all subscribed sessions"""
        event_json = event.model_dump_json()
        sender_id = event.session_id

        sent_count = 0
        for session_id, websocket in list(self.active_connections.items()):
            # Skip sender if requested
            if exclude_sender and session_id == sender_id:
                continue

            # Check if session is subscribed to this event type
            if session_id in self.subscriptions:
                is_subscribed = any(
                    self.matches_topic(event.event_type, pattern)
                    for pattern in self.subscriptions[session_id]
                )

                if not is_subscribed:
                    continue

            # Send event
            try:
                await websocket.send_text(event_json)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending to {session_id}: {e}")
                # Don't disconnect here - let main loop handle it

        logger.debug(f"Broadcast event {event.event_type} to {sent_count} sessions")

    async def send_to_session(self, session_id: str, event: Event):
        """Send event to a specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(event.model_dump_json())
                logger.debug(f"Sent event to {session_id}")
            except Exception as e:
                logger.error(f"Error sending to {session_id}: {e}")

    def get_connected_sessions(self) -> List[ConnectedSession]:
        """Get list of all connected sessions"""
        return list(self.sessions.values())

    def get_session(self, session_id: str) -> ConnectedSession:
        """Get session info"""
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, **kwargs):
        """Update session attributes"""
        if session_id in self.sessions:
            for key, value in kwargs.items():
                if hasattr(self.sessions[session_id], key):
                    setattr(self.sessions[session_id], key, value)

            # Update last_event timestamp
            self.sessions[session_id].last_event = datetime.utcnow()

    def get_sessions_by_capability(self, capability: str) -> List[ConnectedSession]:
        """Find sessions with a specific capability"""
        return [
            session for session in self.sessions.values()
            if capability in session.capabilities
        ]

    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected"""
        return session_id in self.active_connections

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
