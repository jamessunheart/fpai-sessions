#!/usr/bin/env python3
"""
ARIA PROACTIVE DAEMON RUNNER
============================

Runs the proactive intelligence system that makes Aria
curious and helpful.

Usage:
    python run_proactive.py

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram bot token
    TELEGRAM_CHAT_ID: Chat ID to send notifications to
    PROACTIVE_POLL_INTERVAL: Seconds between sensing cycles (default: 60)
    DIGEST_HOUR: Hour to send daily digest (default: 8)
"""

import os
import sys
import asyncio
import logging
import signal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("aria.proactive.runner")


async def main():
    """Main entry point."""
    from core.proactive import get_daemon
    
    daemon = get_daemon()
    
    # Handle shutdown gracefully
    loop = asyncio.get_event_loop()
    
    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(daemon.stop())
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Start the daemon
    logger.info("=" * 50)
    logger.info("ARIA PROACTIVE DAEMON")
    logger.info("=" * 50)
    logger.info("")
    logger.info("Making Aria curious, helpful, and proactive!")
    logger.info("")
    logger.info("Features:")
    logger.info("  - Trading signals from WhaleTrack Magnet")
    logger.info("  - Infrastructure monitoring")
    logger.info("  - Builder queue tracking")
    logger.info("  - Revenue metrics")
    logger.info("  - Curiosity engine for pattern discovery")
    logger.info("  - Morning briefing at 8am")
    logger.info("")
    logger.info("Notifications:")
    logger.info("  - Urgent: Telegram immediately")
    logger.info("  - Routine: Dashboard digest")
    logger.info("")
    
    telegram_configured = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    if telegram_configured:
        logger.info("✅ Telegram notifications enabled")
    else:
        logger.warning("⚠️ Telegram not configured (set TELEGRAM_BOT_TOKEN)")
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("")
    
    await daemon.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Daemon crashed: {e}")
        sys.exit(1)


