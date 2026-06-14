"""
WhiteRock Blessings Engine - Structured Logging Configuration
Uses structlog for JSON-formatted logs with context.
"""

import logging
import sys
from typing import Any

import structlog
from app.config import settings


def configure_logging():
    """Configure structured logging for the application."""
    
    # Determine log level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if settings.DEBUG:
        # Development: colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name or "whiterock")


# Convenience logger instance
logger = get_logger()


class LogContext:
    """Context manager for adding log context."""
    
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, *args):
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_request_context(request_id: str, member_id: int = None, path: str = None):
    """Bind request context for logging."""
    context = {"request_id": request_id, "path": path}
    if member_id:
        context["member_id"] = member_id
    structlog.contextvars.bind_contextvars(**context)


def clear_request_context():
    """Clear request context after request completes."""
    structlog.contextvars.clear_contextvars()


# Log level helpers
def log_info(message: str, **kwargs):
    """Log info level message."""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log warning level message."""
    logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    """Log error level message."""
    logger.error(message, **kwargs)


def log_debug(message: str, **kwargs):
    """Log debug level message."""
    logger.debug(message, **kwargs)


# Specific event loggers
def log_member_registered(member_id: int, email: str):
    """Log member registration event."""
    logger.info("member_registered", member_id=member_id, email=email)


def log_login_success(member_id: int, email: str):
    """Log successful login."""
    logger.info("login_success", member_id=member_id, email=email)


def log_login_failure(email: str, reason: str):
    """Log failed login attempt."""
    logger.warning("login_failure", email=email, reason=reason)


def log_tithe_submitted(tithe_id: int, member_id: int, amount_cents: int):
    """Log tithe submission."""
    logger.info("tithe_submitted", tithe_id=tithe_id, member_id=member_id, amount_cents=amount_cents)


def log_blessing_state_change(blessing_id: int, old_state: str, new_state: str, actor_id: int):
    """Log blessing state transition."""
    logger.info(
        "blessing_state_change",
        blessing_id=blessing_id,
        old_state=old_state,
        new_state=new_state,
        actor_id=actor_id
    )


def log_cora_transaction(member_id: int, amount: int, transaction_type: str):
    """Log CORA transaction."""
    logger.info(
        "cora_transaction",
        member_id=member_id,
        amount=amount,
        transaction_type=transaction_type
    )


def log_cora_decay(member_id: int, amount_decayed: int, balance_after: int):
    """Log CORA decay event."""
    logger.info(
        "cora_decay",
        member_id=member_id,
        amount_decayed=amount_decayed,
        balance_after=balance_after
    )


def log_disbursement(blessing_id: int, amount_cents: int, vendor_direct: bool, cash_override: bool = False):
    """Log blessing disbursement."""
    level = "warning" if cash_override else "info"
    getattr(logger, level)(
        "blessing_disbursement",
        blessing_id=blessing_id,
        amount_cents=amount_cents,
        vendor_direct=vendor_direct,
        cash_to_member_override=cash_override
    )


def log_audit_event(action: str, entity_type: str, entity_id: int, severity: str = "info"):
    """Log audit event."""
    getattr(logger, severity)(
        "audit_event",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id
    )

