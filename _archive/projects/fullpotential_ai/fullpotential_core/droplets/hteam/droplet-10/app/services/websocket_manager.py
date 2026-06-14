"""
WebSocket Manager - UDC COMPLIANT with Ping Support
Real-time updates with UDC envelope wrapping
"""
from fastapi import WebSocket
from typing import Set
import json
import asyncio
import structlog

log = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts UDC-compliant messages.
    """
    
    def __init__(self):
        self.task_connections: Set[WebSocket] = set()
        self.droplet_connections: Set[WebSocket] = set()
    
    async def connect_task_channel(self, websocket: WebSocket):
        """Add connection to task updates channel"""
        await websocket.accept()
        self.task_connections.add(websocket)
        log.info("websocket_task_connected", total_connections=len(self.task_connections))
    
    async def connect_droplet_channel(self, websocket: WebSocket):
        """Add connection to droplet updates channel"""
        await websocket.accept()
        self.droplet_connections.add(websocket)
        log.info("websocket_droplet_connected", total_connections=len(self.droplet_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection from all channels"""
        if websocket in self.task_connections:
            self.task_connections.remove(websocket)
            log.info("websocket_task_disconnected", remaining=len(self.task_connections))
        if websocket in self.droplet_connections:
            self.droplet_connections.remove(websocket)
            log.info("websocket_droplet_disconnected", remaining=len(self.droplet_connections))
    
    async def _broadcast_to_channel(self, connections: Set[WebSocket], message: dict):
        """
        Broadcast UDC message to all connections in a channel.
        
        Args:
            connections: Set of WebSocket connections
            message: UDC-compliant message envelope (already wrapped)
        """
        if not connections:
            return
        
        # Validate message is UDC compliant
        required_fields = ["udc_version", "trace_id", "source", "target", "message_type", "timestamp", "payload"]
        if not all(field in message for field in required_fields):
            log.error("websocket_invalid_message", message=message, missing=[f for f in required_fields if f not in message])
            return
        
        message_json = json.dumps(message, default=str)
        dead_connections = set()
        
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                log.error("websocket_send_failed", error=str(e))
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)
    
    async def broadcast_task_created(self, udc_message: dict):
        """
        Broadcast task creation event.
        
        Args:
            udc_message: UDC-wrapped message from udc_wrap()
        """
        await self._broadcast_to_channel(self.task_connections, udc_message)
    
    async def broadcast_task_updated(self, udc_message: dict):
        """
        Broadcast task update event.
        
        Args:
            udc_message: UDC-wrapped message from udc_wrap()
        """
        await self._broadcast_to_channel(self.task_connections, udc_message)
    
    async def broadcast_task_assigned(self, udc_message: dict):
        """
        Broadcast task assignment event.
        
        Args:
            udc_message: UDC-wrapped message from udc_wrap()
        """
        await self._broadcast_to_channel(self.task_connections, udc_message)
    
    async def broadcast_task_completed(self, udc_message: dict):
        """
        Broadcast task completion event.
        
        Args:
            udc_message: UDC-wrapped message from udc_wrap()
        """
        await self._broadcast_to_channel(self.task_connections, udc_message)
    
    async def broadcast_task_failed(self, udc_message: dict):
        """
        Broadcast task failure event.
        
        Args:
            udc_message: UDC-wrapped message from udc_wrap()
        """
        await self._broadcast_to_channel(self.task_connections, udc_message)
    
    async def broadcast_droplet_registered(self, udc_message: dict):
        """
        Broadcast droplet registration event.
        
        Args:
            udc_message: UDC-wrapped message from udc_wrap()
        """
        await self._broadcast_to_channel(self.droplet_connections, udc_message)
    
    async def broadcast_droplet_health_changed(self, droplet_id: int, old_status: str, new_status: str):
        """
        Broadcast droplet health change event.
        
        Note: This method creates the UDC envelope internally for backward compatibility.
        Prefer passing pre-wrapped messages to other broadcast methods.
        """
        from app.utils.udc_helpers import udc_wrap
        from app.config import settings
        from datetime import datetime
        
        message = udc_wrap(
            payload={
                "event": "droplet_health_changed",
                "droplet_id": droplet_id,
                "old_status": old_status,
                "new_status": new_status,
                "changed_at": datetime.utcnow().isoformat()
            },
            source=f"droplet-{settings.droplet_id}",
            target="broadcast",
            message_type="event"
        )
        
        await self._broadcast_to_channel(self.droplet_connections, message)
    
    async def broadcast_droplet_heartbeat_missed(self, droplet_id: int, last_seen: str):
        """
        Broadcast droplet heartbeat missed event.
        
        Note: This method creates the UDC envelope internally for backward compatibility.
        """
        from app.utils.udc_helpers import udc_wrap
        from app.config import settings
        from datetime import datetime
        
        message = udc_wrap(
            payload={
                "event": "droplet_heartbeat_missed",
                "droplet_id": droplet_id,
                "last_seen": last_seen,
                "marked_inactive_at": datetime.utcnow().isoformat()
            },
            source=f"droplet-{settings.droplet_id}",
            target="broadcast",
            message_type="event"
        )
        
        await self._broadcast_to_channel(self.droplet_connections, message)
    
    async def send_ping(self):
        """
        Send keepalive ping to all connections.
        Should be called periodically (every 30-60 seconds).
        """
        from app.utils.udc_helpers import udc_wrap
        from app.config import settings
        
        ping_message = udc_wrap(
            payload={"event": "ping"},
            source=f"droplet-{settings.droplet_id}",
            target="broadcast",
            message_type="event"
        )
        
        await self._broadcast_to_channel(self.task_connections, ping_message)
        await self._broadcast_to_channel(self.droplet_connections, ping_message)
    
    async def ping_all_connections(self):
        """
        Alias for send_ping() - called by scheduler.
        Send keepalive ping to all WebSocket connections.
        """
        try:
            await self.send_ping()
            log.debug(
                "websocket_ping_sent",
                task_connections=len(self.task_connections),
                droplet_connections=len(self.droplet_connections)
            )
        except Exception as e:
            log.error("websocket_ping_failed", error=str(e))
    
    def get_connection_count(self) -> dict:
        """Get current connection statistics"""
        return {
            "task_connections": len(self.task_connections),
            "droplet_connections": len(self.droplet_connections),
            "total_connections": len(self.task_connections) + len(self.droplet_connections)
        }


# Global instance
websocket_manager = WebSocketManager()


async def start_ping_loop():
    """
    Background task to send periodic pings.
    Should be started on application startup.
    
    Note: This is now handled by APScheduler in main.py
    This function is kept for backward compatibility.
    """
    while True:
        await asyncio.sleep(30)  # Ping every 30 seconds
        try:
            await websocket_manager.send_ping()
        except Exception as e:
            log.error("ping_loop_failed", error=str(e))