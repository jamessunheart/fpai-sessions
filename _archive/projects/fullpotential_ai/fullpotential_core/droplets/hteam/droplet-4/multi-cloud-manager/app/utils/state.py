"""
Application state management
Tracks requests, errors, connections, etc.
"""

from datetime import datetime
from collections import deque

# Request tracking
request_count = 0
error_count = 0
start_time = datetime.utcnow()

# Message queue and connections
message_queue = []
connected_droplets = set()

# Configuration state
is_shutting_down = False
shutdown_reason = None


def increment_requests():
    """Increment request counter"""
    global request_count
    request_count += 1


def increment_errors():
    """Increment error counter"""
    global error_count
    error_count += 1


def add_connected_droplet(droplet_id: str):
    """Add a droplet to connected set"""
    connected_droplets.add(droplet_id)


def remove_connected_droplet(droplet_id: str):
    """Remove a droplet from connected set"""
    connected_droplets.discard(droplet_id)


def get_uptime_seconds() -> int:
    """Get uptime in seconds"""
    return int((datetime.utcnow() - start_time).total_seconds())


def set_shutdown_state(reason: str):
    """Set shutdown state"""
    global is_shutting_down, shutdown_reason
    is_shutting_down = True
    shutdown_reason = reason


def reset_shutdown_state():
    """Reset shutdown state"""
    global is_shutting_down, shutdown_reason
    is_shutting_down = False
    shutdown_reason = None
