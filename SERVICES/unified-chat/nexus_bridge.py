#!/usr/bin/env python3
"""
NEXUS Bridge for Unified Chat
Connects unified-chat to NEXUS event bus for real-time session coordination
"""
import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEXUS_URL = "ws://localhost:8450/ws/session/unified-chat"
UNIFIED_CHAT_URL = "ws://localhost:8100"  # Assuming unified-chat has WebSocket


async def connect_to_nexus():
    """Connect unified-chat to NEXUS event bus"""
    logger.info("🔗 Connecting Unified Chat to NEXUS Event Bus...")

    try:
        async with websockets.connect(NEXUS_URL) as ws:
            logger.info("✅ Connected to NEXUS!")

            # Subscribe to all session events
            await ws.send(json.dumps({
                "action": "subscribe",
                "topics": ["session.*", "work.*", "help.*", "message.*"]
            }))

            logger.info("📡 Subscribed to all session events")
            logger.info("🎧 Listening for NEXUS events to relay to chat...")

            # Listen for events from NEXUS
            async for message in ws:
                try:
                    event = json.loads(message)

                    # Log the event
                    logger.info(f"📨 Event: {event.get('event_type')} from {event.get('session_id')}")

                    # Forward to unified-chat (this would need actual unified-chat integration)
                    # For now, just log what we'd forward

                    if event.get('event_type') == 'session.connected':
                        logger.info(f"   → Session {event['session_id']} connected")

                    elif event.get('event_type') == 'work.claimed':
                        work = event.get('payload', {}).get('work_id', 'unknown')
                        logger.info(f"   → Work claimed: {work}")

                    elif event.get('event_type') == 'help.needed':
                        task = event.get('payload', {}).get('task', 'unknown')
                        logger.info(f"   → Help needed: {task}")

                    elif event.get('event_type') == 'message.broadcast':
                        subject = event.get('payload', {}).get('subject', 'unknown')
                        logger.info(f"   → Broadcast: {subject}")

                except Exception as e:
                    logger.error(f"Error processing event: {e}")

    except Exception as e:
        logger.error(f"Failed to connect to NEXUS: {e}")


async def broadcast_chat_events_to_nexus():
    """
    Future: Listen to unified-chat and broadcast important events to NEXUS
    This enables chat messages to become NEXUS events
    """
    pass


async def main():
    """Run the bridge"""
    logger.info("🌉 NEXUS Bridge for Unified Chat")
    logger.info("=" * 60)
    logger.info("Purpose: Connect unified-chat to NEXUS event bus")
    logger.info("Effect: Chat messages become real-time session coordination events")
    logger.info("=" * 60)
    logger.info("")

    # For now, just connect to NEXUS and log events
    # Full bidirectional integration requires unified-chat API modifications
    await connect_to_nexus()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bridge stopped")
