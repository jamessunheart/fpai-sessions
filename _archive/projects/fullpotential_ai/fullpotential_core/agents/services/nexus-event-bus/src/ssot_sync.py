"""SSOT synchronization - keep filesystem in sync with event bus state"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from .models import ConnectedSession, Event, EventType

logger = logging.getLogger(__name__)


class SSOTSync:
    """Synchronizes event bus state with SSOT filesystem"""

    def __init__(self, coordination_path: str = "/Users/jamessunheart/Development/docs/coordination"):
        self.coordination_path = Path(coordination_path)
        self.ssot_file = self.coordination_path / "SSOT.json"
        self.sessions_file = self.coordination_path / "claude_sessions.json"
        self.heartbeats_dir = self.coordination_path / "heartbeats"
        self.messages_dir = self.coordination_path / "messages"

        # Create directories if they don't exist
        self.heartbeats_dir.mkdir(exist_ok=True, parents=True)
        self.messages_dir.mkdir(exist_ok=True, parents=True)

    def load_ssot(self) -> Optional[dict]:
        """Load SSOT.json"""
        try:
            if self.ssot_file.exists():
                with open(self.ssot_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading SSOT.json: {e}")
        return None

    def save_ssot(self, data: dict):
        """Save SSOT.json"""
        try:
            with open(self.ssot_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug("SSOT.json updated")
        except Exception as e:
            logger.error(f"Error saving SSOT.json: {e}")

    def load_sessions(self) -> Optional[dict]:
        """Load claude_sessions.json"""
        try:
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading claude_sessions.json: {e}")
        return None

    def save_sessions(self, data: dict):
        """Save claude_sessions.json"""
        try:
            with open(self.sessions_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug("claude_sessions.json updated")
        except Exception as e:
            logger.error(f"Error saving claude_sessions.json: {e}")

    def on_session_connected(self, session: ConnectedSession):
        """Update SSOT when session connects"""
        try:
            # Update claude_sessions.json
            sessions_data = self.load_sessions() or {}

            session_key = str(session.session_id).replace("session-", "")

            if session_key in sessions_data:
                sessions_data[session_key]["status"] = "active"
                sessions_data[session_key]["last_heartbeat"] = datetime.utcnow().isoformat()

            self.save_sessions(sessions_data)

            # Create heartbeat file
            self.create_heartbeat(session.session_id, "connected", "NEXUS event bus")

            logger.info(f"SSOT updated: session {session.session_id} connected")

        except Exception as e:
            logger.error(f"Error updating SSOT on session connect: {e}")

    def on_session_disconnected(self, session_id: str):
        """Update SSOT when session disconnects"""
        try:
            # Don't mark as inactive immediately - let timeout handle it
            # Just create a disconnect heartbeat
            self.create_heartbeat(session_id, "disconnected", "NEXUS event bus")

            logger.info(f"SSOT updated: session {session_id} disconnected")

        except Exception as e:
            logger.error(f"Error updating SSOT on session disconnect: {e}")

    def on_work_claimed(self, session_id: str, work_id: str, description: str):
        """Update SSOT when work is claimed"""
        try:
            sessions_data = self.load_sessions() or {}

            session_key = str(session_id).replace("session-", "")

            if session_key in sessions_data:
                sessions_data[session_key]["current_work"] = description
                sessions_data[session_key]["status"] = "working"

            self.save_sessions(sessions_data)

            self.create_heartbeat(session_id, "work_claimed", work_id)

            logger.info(f"SSOT updated: session {session_id} claimed work {work_id}")

        except Exception as e:
            logger.error(f"Error updating SSOT on work claim: {e}")

    def on_work_completed(self, session_id: str, work_id: str):
        """Update SSOT when work is completed"""
        try:
            sessions_data = self.load_sessions() or {}

            session_key = str(session_id).replace("session-", "")

            if session_key in sessions_data:
                sessions_data[session_key]["current_work"] = None
                sessions_data[session_key]["status"] = "active"

            self.save_sessions(sessions_data)

            self.create_heartbeat(session_id, "work_completed", work_id)

            logger.info(f"SSOT updated: session {session_id} completed work {work_id}")

        except Exception as e:
            logger.error(f"Error updating SSOT on work complete: {e}")

    def on_status_update(self, session_id: str, status: str, current_work: Optional[str] = None):
        """Update SSOT when session status changes"""
        try:
            sessions_data = self.load_sessions() or {}

            session_key = str(session_id).replace("session-", "")

            if session_key in sessions_data:
                sessions_data[session_key]["status"] = status
                if current_work:
                    sessions_data[session_key]["current_work"] = current_work

            self.save_sessions(sessions_data)

            logger.debug(f"SSOT updated: session {session_id} status -> {status}")

        except Exception as e:
            logger.error(f"Error updating SSOT on status update: {e}")

    def create_heartbeat(self, session_id: str, action: str, target: str):
        """Create a heartbeat file"""
        try:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}-{session_id}.json"
            filepath = self.heartbeats_dir / filename

            heartbeat_data = {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "target": target
            }

            with open(filepath, 'w') as f:
                json.dump(heartbeat_data, f, indent=2)

            logger.debug(f"Heartbeat created: {filename}")

        except Exception as e:
            logger.error(f"Error creating heartbeat: {e}")

    def sync_event(self, event: Event):
        """Sync an event to filesystem based on event type"""
        try:
            if event.event_type == EventType.SESSION_CONNECTED:
                # Already handled in on_session_connected
                pass

            elif event.event_type == EventType.SESSION_DISCONNECTED:
                # Already handled in on_session_disconnected
                pass

            elif event.event_type == EventType.WORK_CLAIMED:
                work_id = event.payload.get("work_id", "unknown")
                description = event.payload.get("work_description", work_id)
                self.on_work_claimed(event.session_id, work_id, description)

            elif event.event_type == EventType.WORK_COMPLETED:
                work_id = event.payload.get("work_id", "unknown")
                self.on_work_completed(event.session_id, work_id)

            elif event.event_type == EventType.STATUS_UPDATE:
                status = event.payload.get("status", "active")
                current_work = event.payload.get("current_work")
                self.on_status_update(event.session_id, status, current_work)

            elif event.event_type == EventType.MESSAGE_BROADCAST:
                # Create message file in broadcast directory
                self.save_message_broadcast(event)

        except Exception as e:
            logger.error(f"Error syncing event {event.event_id}: {e}")

    def save_message_broadcast(self, event: Event):
        """Save broadcast message to filesystem"""
        try:
            broadcast_dir = self.messages_dir / "broadcast"
            broadcast_dir.mkdir(exist_ok=True, parents=True)

            timestamp = event.timestamp.strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}-{event.session_id}.json"
            filepath = broadcast_dir / filename

            message_data = {
                "from": event.session_id,
                "to": "broadcast",
                "timestamp": event.timestamp.isoformat(),
                "subject": event.payload.get("subject", ""),
                "message": event.payload.get("message", ""),
                "priority": event.payload.get("priority", "normal")
            }

            with open(filepath, 'w') as f:
                json.dump(message_data, f, indent=2)

            logger.debug(f"Broadcast message saved: {filename}")

        except Exception as e:
            logger.error(f"Error saving broadcast message: {e}")
