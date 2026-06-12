#!/usr/bin/env python3
"""
SERVER WATCHDOG - Proactive monitoring with phone/Telegram alerts
"""
import asyncio
import httpx
import logging
import os
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("aria.watchdog")

# Configuration
JAMES_CHAT_ID = 1759822075
JAMES_PHONE = os.getenv("JAMES_PHONE", "+19252397291")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Servers to monitor
SERVERS = {
    "primary": {
        "name": "Primary (Trading/Website)",
        "ip": "198.54.123.234",
        "checks": [
            {"url": "http://198.54.123.234:8601/health", "name": "WhaleTrack"},
        ]
    },
    "secondary": {
        "name": "Secondary (AI Services)",
        "ip": "162.0.208.88",
        "checks": [
            {"url": "http://162.0.208.88:8750/health", "name": "Aria Command"},
        ]
    }
}

# State tracking
server_status = {
    "primary": {"healthy": True, "failures": 0, "alerted": False, "last_alert": None},
    "secondary": {"healthy": True, "failures": 0, "alerted": False, "last_alert": None},
}

FAILURE_THRESHOLD = 3  # Alert after 3 consecutive failures (3 minutes)
CHECK_INTERVAL = 60    # Check every 60 seconds


async def send_telegram(message: str, urgent: bool = False):
    """Send Telegram message."""
    token = TELEGRAM_TOKEN or "8541321124:AAEpkRWpt4jNzVFgAmsJArsHN-QcKGNcoG0"
    prefix = "🚨 CRITICAL: " if urgent else "⚠️ "
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": JAMES_CHAT_ID, "text": prefix + message}
            )
            if response.status_code == 200:
                logger.info(f"Telegram alert sent")
            else:
                logger.error(f"Telegram failed: {response.text}")
        except Exception as e:
            logger.error(f"Failed to send Telegram: {e}")


async def call_james(message: str):
    """Initiate phone call for critical alerts."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "http://localhost:8888/api/call",
                json={"to": JAMES_PHONE, "message": message}
            )
            if response.status_code == 200:
                logger.info(f"Phone call initiated")
            else:
                logger.warning(f"Call API returned: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to call: {e}")


async def check_server(server_key: str) -> bool:
    """Check if a server is healthy."""
    server = SERVERS[server_key]
    
    async with httpx.AsyncClient(timeout=10) as client:
        for check in server["checks"]:
            try:
                response = await client.get(check["url"])
                if response.status_code == 200:
                    return True
            except Exception as e:
                logger.debug(f"Check failed for {check['name']}: {e}")
                continue
    
    return False


async def monitor_loop():
    """Main monitoring loop."""
    logger.info("=" * 50)
    logger.info("  SERVER WATCHDOG STARTED")
    logger.info("=" * 50)
    server_names = list(SERVERS.keys())
    logger.info(f"Monitoring: {server_names}")
    logger.info(f"Check interval: {CHECK_INTERVAL}s, Alert threshold: {FAILURE_THRESHOLD} failures")
    
    check_count = 0
    
    while True:
        check_count += 1
        
        for server_key, server in SERVERS.items():
            status = server_status[server_key]
            
            try:
                healthy = await check_server(server_key)
                
                if healthy:
                    if not status["healthy"]:
                        # Was down, now recovered
                        msg = f"✅ {server['name']} is BACK ONLINE after {status['failures']} failed checks!"
                        await send_telegram(msg)
                        logger.info(f"RECOVERED: {server['name']}")
                    
                    status["healthy"] = True
                    status["failures"] = 0
                    status["alerted"] = False
                    
                    if check_count % 10 == 1:  # Log status every 10 checks
                        logger.info(f"OK: {server['name']}")
                else:
                    status["failures"] += 1
                    status["healthy"] = False
                    logger.warning(f"FAILED: {server['name']} (attempt {status['failures']})")
                    
                    if status["failures"] >= FAILURE_THRESHOLD and not status["alerted"]:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        msg = (
                            f"🚨 {server['name']} is DOWN!\n\n"
                            f"IP: {server['ip']}\n"
                            f"Failed checks: {status['failures']}\n"
                            f"Time: {timestamp}\n\n"
                            f"Check hosting provider or IPMI console."
                        )
                        await send_telegram(msg, urgent=True)
                        
                        # Phone call for primary server
                        if server_key == "primary":
                            await call_james(f"Alert! {server['name']} is down and needs attention.")
                        
                        status["alerted"] = True
                        status["last_alert"] = datetime.now()
                        logger.error(f"ALERT SENT: {server['name']} is down!")
                        
            except Exception as e:
                logger.error(f"Monitor error for {server_key}: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor_loop())


