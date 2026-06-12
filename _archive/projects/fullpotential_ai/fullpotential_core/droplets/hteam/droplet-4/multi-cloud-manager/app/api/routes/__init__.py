"""
Route exports for easy importing
Centralizes all route modules
"""

# UDC Core Routes
from app.api.routes import health
from app.api.routes import capabilities
from app.api.routes import state_router
from app.api.routes import dependencies
from app.api.routes import message
from app.api.routes import send

# UDC Extended Routes (from combined file)
from app.api.routes.extended import (
    version,
    metrics,
    logs,
    events,
    proof
)

# Control Routes (from combined file)
from app.api.routes.shutdown import (
    shutdown,
    reload_config,
    emergency_stop
)

# Cloud Provider Routes
from app.api.routes import do_routes
from app.api.routes import hetzner_routes
from app.api.routes import vultr_routes
from app.api.routes import multi_routes

__all__ = [
    # UDC Core
    "health",
    "capabilities",
    "state_router",
    "dependencies",
    "message",
    "send",
    # UDC Extended
    "version",
    "metrics",
    "logs",
    "events",
    "proof",
    # Control
    "shutdown",
    "reload_config",
    "emergency_stop",
    # Cloud Providers
    "do_routes",
    "hetzner_routes",
    "vultr_routes",
    "multi_routes",
]
