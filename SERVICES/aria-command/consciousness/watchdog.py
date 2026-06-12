"""
ARIA WATCHDOG
==============

Prevents service hangs and stuck requests.

Features:
1. Heartbeat monitoring - if no response in 2 minutes, force restart
2. Request timeout enforcement - kill stuck requests after 90 seconds
3. Deadlock detection - monitor thread states
4. Automatic recovery without human intervention

This ensures Aria never gets stuck in an infinite loop or deadlock.
"""

import os
import asyncio
import logging
import signal
import threading
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import subprocess

logger = logging.getLogger("aria.consciousness.watchdog")

# Configuration
HEARTBEAT_TIMEOUT = int(os.getenv("WATCHDOG_HEARTBEAT_TIMEOUT", "120"))  # 2 minutes
REQUEST_TIMEOUT = int(os.getenv("WATCHDOG_REQUEST_TIMEOUT", "90"))  # 90 seconds
CHECK_INTERVAL = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "30"))  # 30 seconds
SERVICE_NAME = "aria-command"


class WatchdogState(str, Enum):
    """Watchdog states."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    RECOVERING = "recovering"


@dataclass
class RequestTracker:
    """Tracks an active request."""
    request_id: str
    started_at: datetime
    description: str
    timeout_seconds: int = REQUEST_TIMEOUT
    
    def is_stuck(self) -> bool:
        """Check if request has exceeded timeout."""
        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return (datetime.now() - self.started_at).total_seconds()


class Watchdog:
    """
    System watchdog that prevents hangs.
    
    Monitors:
    - Heartbeat from main service
    - Active request timeouts
    - Thread states for deadlocks
    
    Takes action:
    - Kills stuck requests
    - Forces service restart if unresponsive
    """
    
    def __init__(self):
        self.last_heartbeat = datetime.now()
        self.state = WatchdogState.HEALTHY
        self.active_requests: Dict[str, RequestTracker] = {}
        self.restart_count = 0
        self.last_restart: Optional[datetime] = None
        self.running = False
        self._lock = threading.Lock()
        
        # Callbacks for stuck request handling
        self._request_kill_callback: Optional[Callable] = None
        
        logger.info(f"🐕 Watchdog initialized (heartbeat timeout: {HEARTBEAT_TIMEOUT}s)")
    
    def heartbeat(self):
        """
        Record a heartbeat from the service.
        
        Call this regularly to indicate the service is alive.
        The consciousness loop calls this every cycle.
        """
        with self._lock:
            self.last_heartbeat = datetime.now()
            if self.state == WatchdogState.WARNING:
                self.state = WatchdogState.HEALTHY
                logger.info("💚 Watchdog: Service recovered, heartbeat received")
    
    def time_since_heartbeat(self) -> float:
        """Get seconds since last heartbeat."""
        return (datetime.now() - self.last_heartbeat).total_seconds()
    
    def register_request(self, request_id: str, description: str = "", timeout: int = None) -> str:
        """
        Register an active request for timeout tracking.
        
        Returns the request_id for later deregistration.
        """
        with self._lock:
            self.active_requests[request_id] = RequestTracker(
                request_id=request_id,
                started_at=datetime.now(),
                description=description,
                timeout_seconds=timeout or REQUEST_TIMEOUT
            )
        return request_id
    
    def deregister_request(self, request_id: str):
        """Mark a request as completed."""
        with self._lock:
            if request_id in self.active_requests:
                del self.active_requests[request_id]
    
    def set_request_kill_callback(self, callback: Callable[[str], Any]):
        """Set callback to kill stuck requests."""
        self._request_kill_callback = callback
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check overall health and take action if needed.
        
        Returns health status and any actions taken.
        """
        actions = []
        
        # Check heartbeat
        heartbeat_age = self.time_since_heartbeat()
        
        if heartbeat_age > HEARTBEAT_TIMEOUT:
            self.state = WatchdogState.CRITICAL
            logger.error(f"🚨 Watchdog CRITICAL: No heartbeat for {heartbeat_age:.0f}s")
            
            # Attempt force restart
            if await self._force_restart():
                actions.append(f"Force restarted service after {heartbeat_age:.0f}s without heartbeat")
                self.restart_count += 1
                self.last_restart = datetime.now()
        
        elif heartbeat_age > HEARTBEAT_TIMEOUT / 2:
            self.state = WatchdogState.WARNING
            logger.warning(f"⚠️ Watchdog WARNING: No heartbeat for {heartbeat_age:.0f}s")
        
        # Check stuck requests
        stuck_requests = []
        with self._lock:
            for req_id, tracker in list(self.active_requests.items()):
                if tracker.is_stuck():
                    stuck_requests.append(tracker)
        
        for tracker in stuck_requests:
            logger.warning(f"⏰ Stuck request detected: {tracker.request_id} ({tracker.elapsed_seconds():.0f}s)")
            
            # Attempt to kill stuck request
            if self._request_kill_callback:
                try:
                    self._request_kill_callback(tracker.request_id)
                    actions.append(f"Killed stuck request: {tracker.description[:50]}")
                except Exception as e:
                    logger.error(f"Failed to kill request {tracker.request_id}: {e}")
            
            # Remove from tracking
            self.deregister_request(tracker.request_id)
        
        # Check for thread deadlocks (simplified check)
        thread_count = threading.active_count()
        if thread_count > 50:  # Arbitrary threshold
            logger.warning(f"⚠️ High thread count: {thread_count}")
            actions.append(f"Warning: {thread_count} active threads")
        
        return {
            "state": self.state.value,
            "heartbeat_age_seconds": heartbeat_age,
            "active_requests": len(self.active_requests),
            "stuck_requests_killed": len(stuck_requests),
            "restart_count": self.restart_count,
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "thread_count": thread_count,
            "actions": actions
        }
    
    async def _force_restart(self) -> bool:
        """
        Force restart the service.
        
        Returns True if restart was initiated.
        """
        # Prevent restart loops - max 3 restarts per hour
        if self.restart_count >= 3:
            if self.last_restart and (datetime.now() - self.last_restart) < timedelta(hours=1):
                logger.error("🚫 Restart limit reached (3/hour) - not restarting")
                return False
            else:
                # Reset counter after an hour
                self.restart_count = 0
        
        logger.warning(f"🔄 Watchdog forcing restart of {SERVICE_NAME}...")
        self.state = WatchdogState.RECOVERING
        
        try:
            # Use systemctl to restart (runs as separate process)
            result = subprocess.run(
                ["systemctl", "restart", SERVICE_NAME],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Service {SERVICE_NAME} restart initiated")
                return True
            else:
                logger.error(f"❌ Restart failed: {result.stderr.decode()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Restart command timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Restart error: {e}")
            return False
    
    async def run(self):
        """Run the watchdog monitoring loop."""
        self.running = True
        logger.info("🐕 Watchdog loop started")
        
        while self.running:
            try:
                await self.check_health()
            except Exception as e:
                logger.error(f"Watchdog check error: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)
        
        logger.info("🐕 Watchdog loop stopped")
    
    async def stop(self):
        """Stop the watchdog."""
        self.running = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current watchdog status."""
        return {
            "state": self.state.value,
            "running": self.running,
            "heartbeat_age_seconds": self.time_since_heartbeat(),
            "active_requests": len(self.active_requests),
            "restart_count": self.restart_count,
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "config": {
                "heartbeat_timeout": HEARTBEAT_TIMEOUT,
                "request_timeout": REQUEST_TIMEOUT,
                "check_interval": CHECK_INTERVAL
            }
        }


# ============================================================================
# CONTEXT MANAGER FOR REQUEST TRACKING
# ============================================================================

class WatchedRequest:
    """
    Context manager for tracking requests with timeout.
    
    Usage:
        async with WatchedRequest("ai_call", "Processing user message"):
            response = await ai.call(message)
    """
    
    def __init__(self, request_id: str, description: str = "", timeout: int = None):
        self.request_id = request_id
        self.description = description
        self.timeout = timeout
        self._watchdog = get_watchdog()
    
    async def __aenter__(self):
        self._watchdog.register_request(self.request_id, self.description, self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._watchdog.deregister_request(self.request_id)
        return False


# ============================================================================
# SINGLETON
# ============================================================================

_watchdog: Optional[Watchdog] = None


def get_watchdog() -> Watchdog:
    """Get or create watchdog instance."""
    global _watchdog
    if _watchdog is None:
        _watchdog = Watchdog()
    return _watchdog


async def start_watchdog():
    """Start the watchdog loop."""
    watchdog = get_watchdog()
    await watchdog.run()


def heartbeat():
    """Record a heartbeat (convenience function)."""
    get_watchdog().heartbeat()









