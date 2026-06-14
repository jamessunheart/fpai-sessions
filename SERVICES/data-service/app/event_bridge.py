"""
Event Bridge
=============
Connects the Data Daemon to the Nexus Event Bus for real-time event-driven collection.
Replaces polling with reactive event streams.

"React to reality, don't poll for it."
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("event_bridge")

# Nexus Event Bus WebSocket endpoint
NEXUS_WS_URL = "ws://localhost:8070/ws/session/data-daemon"

# WhaleTrack real-time alerts
WHALETRACK_WS_URL = "ws://localhost:8600/ws/alerts"


class EventBridge:
    """
    Bridge between Data Daemon and event sources.
    Enables real-time, event-driven data collection.
    """
    
    def __init__(self, daemon: Any = None):
        self.daemon = daemon
        self.nexus_ws = None
        self.whaletrack_ws = None
        self.connected = False
        self.event_count = 0
        self.subscribed_topics = ["market.*", "whale.*", "news.*", "data.*"]
        
    async def connect(self) -> bool:
        """Connect to Nexus Event Bus"""
        try:
            import websockets
            
            self.nexus_ws = await websockets.connect(
                NEXUS_WS_URL,
                ping_interval=30,
                ping_timeout=10
            )
            
            # Subscribe to relevant topics
            await self.nexus_ws.send(json.dumps({
                "action": "subscribe",
                "topics": self.subscribed_topics
            }))
            
            self.connected = True
            logger.info(f"📡 Connected to Nexus Event Bus, subscribed to {self.subscribed_topics}")
            return True
            
        except ImportError:
            logger.warning("websockets package not installed, event bridge disabled")
            return False
        except Exception as e:
            logger.warning(f"Could not connect to Nexus Event Bus: {e}")
            return False
    
    async def connect_whaletrack(self) -> bool:
        """Connect to WhaleTrack real-time alerts"""
        try:
            import websockets
            
            self.whaletrack_ws = await websockets.connect(
                WHALETRACK_WS_URL,
                ping_interval=30,
                ping_timeout=10
            )
            
            logger.info("🐋 Connected to WhaleTrack real-time alerts")
            return True
            
        except Exception as e:
            logger.debug(f"WhaleTrack WebSocket not available: {e}")
            return False
    
    async def listen(self):
        """
        Listen for events from Nexus and trigger collection.
        Runs as a background task alongside polling.
        """
        if not self.nexus_ws:
            logger.warning("Not connected to Nexus, cannot listen for events")
            return
            
        try:
            async for message in self.nexus_ws:
                try:
                    event = json.loads(message)
                    await self._handle_event(event)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from Nexus: {message[:100]}")
                except Exception as e:
                    logger.error(f"Error handling event: {e}")
                    
        except Exception as e:
            logger.error(f"Nexus connection lost: {e}")
            self.connected = False
            # Attempt reconnection
            await asyncio.sleep(5)
            await self.connect()
    
    async def listen_whaletrack(self):
        """Listen for real-time whale alerts"""
        if not self.whaletrack_ws:
            return
            
        try:
            async for message in self.whaletrack_ws:
                try:
                    alert = json.loads(message)
                    await self._handle_whale_alert(alert)
                except Exception as e:
                    logger.error(f"Error handling whale alert: {e}")
                    
        except Exception as e:
            logger.debug(f"WhaleTrack WebSocket closed: {e}")
    
    async def _handle_event(self, event: dict):
        """Process incoming events and trigger appropriate collectors"""
        event_type = event.get("type", event.get("event_type", "unknown"))
        self.event_count += 1
        
        logger.debug(f"📨 Received event: {event_type}")
        
        # Map event types to data sources
        if event_type.startswith("market."):
            await self._trigger_collection("whaletrack")
        elif event_type.startswith("whale."):
            await self._trigger_collection("whaletrack")
        elif event_type.startswith("news."):
            await self._trigger_collection("hackernews")
        elif event_type.startswith("tech."):
            await self._trigger_collection("github")
        elif event_type.startswith("research."):
            await self._trigger_collection("arxiv")
        elif event_type == "data.refresh_all":
            # Full refresh triggered by external system
            if self.daemon:
                await self.daemon.run_cycle()
    
    async def _handle_whale_alert(self, alert: dict):
        """Process whale alerts in real-time"""
        alert_type = alert.get("type", "unknown")
        
        logger.info(f"🐋 Real-time whale alert: {alert_type}")
        
        # Immediately collect whale data on significant alerts
        if alert_type in ["liquidation", "large_trade", "whale_movement"]:
            await self._trigger_collection("whaletrack")
            
            # Emit to other services
            await self.emit("whale.alert", {
                "type": alert_type,
                "data": alert,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    async def _trigger_collection(self, source: str):
        """Trigger collection from a specific source"""
        if self.daemon and hasattr(self.daemon, 'sense_source'):
            await self.daemon.sense_source(source)
        else:
            logger.debug(f"Would collect from {source} (daemon not attached)")
    
    async def emit(self, event_type: str, data: dict):
        """Emit an event to the Nexus Event Bus"""
        if not self.nexus_ws or not self.connected:
            return
            
        try:
            await self.nexus_ws.send(json.dumps({
                "action": "publish",
                "event_type": event_type,
                "payload": data
            }))
            logger.debug(f"📤 Emitted event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    async def emit_data_collected(self, item: dict):
        """Emit notification that new data was collected"""
        await self.emit("data.collected", {
            "source": item.get("source"),
            "category": item.get("category"),
            "title": item.get("title", "")[:100],
            "relevance": item.get("relevance_score", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def emit_pattern_detected(self, pattern: dict):
        """Emit notification of detected pattern"""
        await self.emit("data.pattern", {
            "type": pattern.get("type"),
            "description": pattern.get("description"),
            "significance": pattern.get("significance", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def emit_prediction_made(self, prediction: dict):
        """Emit notification of new prediction"""
        await self.emit("data.prediction", {
            "id": prediction.get("id"),
            "metric": prediction.get("target_metric"),
            "direction": prediction.get("predicted_direction"),
            "confidence": prediction.get("confidence"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def close(self):
        """Close all connections"""
        if self.nexus_ws:
            await self.nexus_ws.close()
        if self.whaletrack_ws:
            await self.whaletrack_ws.close()
        self.connected = False
        logger.info("📡 Event bridge disconnected")
    
    def get_stats(self) -> dict:
        """Get event bridge statistics"""
        return {
            "connected": self.connected,
            "event_count": self.event_count,
            "subscribed_topics": self.subscribed_topics
        }


# Singleton for easy import
event_bridge = EventBridge()








