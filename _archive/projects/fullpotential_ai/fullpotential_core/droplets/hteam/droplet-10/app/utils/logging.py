"""
Structured Logging Configuration
JSON logging with trace IDs using structlog
"""
import logging
import sys
from typing import Any, Dict
import structlog
from structlog.types import EventDict, Processor

from app.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to all log entries"""
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    event_dict["droplet_id"] = settings.droplet_id
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO format timestamp"""
    from datetime import datetime
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Remove sensitive data from logs"""
    sensitive_keys = {
        'password', 'token', 'jwt', 'secret', 'api_key',
        'authorization', 'credential', 'private_key'
    }
    
    def censor_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively censor sensitive keys"""
        censored = {}
        for key, value in d.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                censored[key] = "***REDACTED***"
            elif isinstance(value, dict):
                censored[key] = censor_dict(value)
            elif isinstance(value, str) and len(value) > 100 and 'Bearer' in value:
                # Censor long bearer tokens
                censored[key] = f"{value[:10]}...***REDACTED***"
            else:
                censored[key] = value
        return censored
    
    return censor_dict(event_dict)


def configure_logging() -> None:
    """
    Configure structured logging for the application
    Call this once at application startup
    """
    
    # Determine log level
    log_level = getattr(logging, settings.log_level)
    
    # Configure structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_app_context,
        add_timestamp,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        censor_sensitive_data,
    ]
    
    # Add appropriate final processor based on environment
    if settings.is_production:
        # JSON output for production (machine-readable)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console output for development (human-readable)
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    
    # Log configuration complete
    log = structlog.get_logger()
    log.info(
        "logging_configured",
        log_level=settings.log_level,
        environment=settings.environment,
        json_format=settings.is_production
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with optional name
    
    Usage:
        log = get_logger(__name__)
        log.info("task_created", task_id=123, task_type="verify")
    """
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding contextual data to logs
    
    Usage:
        with LogContext(trace_id=task.trace_id, task_id=task.id):
            log.info("processing_task")  # Will include trace_id and task_id
    """
    
    def __init__(self, **kwargs):
        self.context = kwargs
    
    def __enter__(self):
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.clear_contextvars()


def log_slow_query(query: str, duration: float, threshold: float = None) -> None:
    """
    Log slow database queries
    
    Args:
        query: SQL query string
        duration: Query execution time in seconds
        threshold: Custom threshold (defaults to settings.slow_query_threshold)
    """
    threshold = threshold or settings.slow_query_threshold
    
    if duration >= threshold:
        log = get_logger("database")
        log.warning(
            "slow_query",
            query=query[:200],  # Truncate long queries
            duration_seconds=round(duration, 3),
            threshold_seconds=threshold
        )


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str = None,
    trace_id: str = None
) -> None:
    """
    Log API request details
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        client_ip: Client IP address
        trace_id: Request trace ID
    """
    log = get_logger("api")
    
    log_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2)
    }
    
    if client_ip:
        log_data["client_ip"] = client_ip
    if trace_id:
        log_data["trace_id"] = trace_id
    
    # Determine log level based on status code
    if status_code >= 500:
        log.error("api_request_error", **log_data)
    elif status_code >= 400:
        log.warning("api_request_client_error", **log_data)
    else:
        log.info("api_request", **log_data)


def log_task_event(
    event: str,
    task_id: int,
    trace_id: str,
    **kwargs
) -> None:
    """
    Log task lifecycle events
    
    Args:
        event: Event name (e.g., "task_created", "task_assigned")
        task_id: Task ID
        trace_id: Task trace ID
        **kwargs: Additional context
    """
    log = get_logger("tasks")
    log.info(
        event,
        task_id=task_id,
        trace_id=str(trace_id),
        **kwargs
    )


def log_droplet_event(
    event: str,
    droplet_id: int,
    **kwargs
) -> None:
    """
    Log droplet lifecycle events
    
    Args:
        event: Event name (e.g., "droplet_registered", "droplet_health_changed")
        droplet_id: Droplet ID
        **kwargs: Additional context
    """
    log = get_logger("droplets")
    log.info(
        event,
        droplet_id=droplet_id,
        **kwargs
    )


def log_error(
    error: Exception,
    context: str = None,
    **kwargs
) -> None:
    """
    Log error with full context
    
    Args:
        error: Exception object
        context: Description of what was happening when error occurred
        **kwargs: Additional context
    """
    log = get_logger("errors")
    
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs
    }
    
    if context:
        log_data["context"] = context
    
    log.error("exception_occurred", **log_data, exc_info=True)