#!/usr/bin/env python3
"""
NEXUS Client Library - Connect Claude Code sessions to NEXUS event bus

Usage:
    from nexus_client import NexusClient

    async def main():
        client = NexusClient("session-5")

        # Subscribe to events
        await client.subscribe(["work.*", "help.*"])

        # Listen for events
        async for event in client.listen():
            print(f"Event: {event['event_type']}")
            print(f"From: {event['session_id']}")
            print(f"Payload: {event['payload']}")

    asyncio.run(main())
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
import websockets
from datetime import datetime

logger = logging.getLogger(__name__)


class NexusClient:
    """Client library for connecting to NEXUS event bus"""

    def __init__(
        self,
        session_id: str,
        nexus_url: str = "ws://localhost:8450",
        auto_reconnect: bool = True
    ):
        self.session_id = session_id
        self.nexus_url = f"{nexus_url}/ws/session/{session_id}"
        self.auto_reconnect = auto_reconnect

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscribed_topics: List[str] = []
        self.connected = False

    async def connect(self):
        """Connect to NEXUS event bus"""
        try:
            self.websocket = await websockets.connect(self.nexus_url)
            self.connected = True
            logger.info(f"✅ Connected to NEXUS: {self.session_id}")

            # Re-subscribe to topics if reconnecting
            if self.subscribed_topics:
                await self.subscribe(self.subscribed_topics)

        except Exception as e:
            logger.error(f"Failed to connect to NEXUS: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from NEXUS"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info(f"Disconnected from NEXUS")

    async def subscribe(self, topics: List[str]):
        """Subscribe to event topics"""
        if not self.websocket:
            await self.connect()

        message = {
            "action": "subscribe",
            "topics": topics
        }

        await self.websocket.send(json.dumps(message))
        self.subscribed_topics.extend(topics)

        logger.info(f"Subscribed to: {topics}")

    async def unsubscribe(self, topics: List[str]):
        """Unsubscribe from event topics"""
        if not self.websocket:
            return

        message = {
            "action": "unsubscribe",
            "topics": topics
        }

        await self.websocket.send(json.dumps(message))

        for topic in topics:
            if topic in self.subscribed_topics:
                self.subscribed_topics.remove(topic)

        logger.info(f"Unsubscribed from: {topics}")

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        """Publish an event"""
        if not self.websocket:
            await self.connect()

        message = {
            "action": "publish",
            "event_type": event_type,
            "payload": payload
        }

        await self.websocket.send(json.dumps(message))

        logger.debug(f"Published event: {event_type}")

    async def listen(self) -> AsyncIterator[Dict[str, Any]]:
        """Listen for incoming events (async generator)"""
        if not self.websocket:
            await self.connect()

        while True:
            try:
                message = await self.websocket.recv()
                event = json.loads(message)
                yield event

            except websockets.ConnectionClosed:
                logger.warning("Connection closed")
                self.connected = False

                if self.auto_reconnect:
                    logger.info("Attempting to reconnect...")
                    await asyncio.sleep(2)
                    await self.connect()
                else:
                    break

            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break

    async def request_help(
        self,
        task: str,
        capabilities_needed: List[str],
        priority: str = "normal",
        context: Optional[str] = None
    ):
        """Broadcast a help request to all sessions"""
        await self.publish("help.needed", {
            "task": task,
            "capabilities_needed": capabilities_needed,
            "priority": priority,
            "context": context
        })

    async def claim_work(self, work_id: str, description: str):
        """Claim a work item"""
        await self.publish("work.claimed", {
            "work_id": work_id,
            "work_description": description
        })

    async def complete_work(self, work_id: str):
        """Mark work as completed"""
        await self.publish("work.completed", {
            "work_id": work_id
        })

    async def update_status(self, status: str, current_work: Optional[str] = None):
        """Update session status"""
        payload = {"status": status}
        if current_work:
            payload["current_work"] = current_work

        await self.publish("status.update", payload)

    async def broadcast_message(self, subject: str, message: str, priority: str = "normal"):
        """Send a broadcast message to all sessions"""
        await self.publish("message.broadcast", {
            "subject": subject,
            "message": message,
            "priority": priority
        })


# ==================== EXAMPLE USAGE ====================

async def example_usage():
    """Example of using NEXUS client"""

    # Create client
    client = NexusClient("session-5")

    # Connect
    await client.connect()

    # Subscribe to topics
    await client.subscribe([
        "work.*",        # All work events
        "help.*",        # All help requests
        "message.*"      # All messages
    ])

    # Update status
    await client.update_status("active", "Building NEXUS client")

    # Request help
    await client.request_help(
        task="Need Python expert for debugging",
        capabilities_needed=["python", "debugging"],
        priority="high"
    )

    # Listen for events
    print("Listening for events...")
    async for event in client.listen():
        event_type = event.get("event_type")
        session_id = event.get("session_id")
        payload = event.get("payload", {})

        print(f"\n📨 Event: {event_type}")
        print(f"   From: {session_id}")
        print(f"   Payload: {payload}")

        # Handle specific event types
        if event_type == "help.needed":
            task = payload.get("task")
            print(f"   Help needed: {task}")

        elif event_type == "work.claimed":
            work_id = payload.get("work_id")
            print(f"   Work claimed: {work_id}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
