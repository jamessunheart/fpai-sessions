"""
Helper Utilities
Common utility functions used across the application
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
import psutil
import structlog

log = structlog.get_logger()


# ============================================================================
# TRACE ID GENERATION
# ============================================================================

def generate_trace_id() -> UUID:
    """Generate a new UUID4 trace ID"""
    return uuid4()


def trace_id_to_str(trace_id: UUID) -> str:
    """Convert UUID trace ID to string"""
    return str(trace_id)


def str_to_trace_id(trace_id_str: str) -> UUID:
    """Convert string to UUID trace ID"""
    try:
        return UUID(trace_id_str)
    except (ValueError, AttributeError):
        log.warning("invalid_trace_id", trace_id_str=trace_id_str)
        return generate_trace_id()


# ============================================================================
# SYSTEM METRICS
# ============================================================================

def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system resource usage
    
    Returns:
        Dict with CPU, memory, and disk usage
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(memory.used / (1024 * 1024), 2),
            "memory_percent": round(memory.percent, 2),
            "disk_percent": round(disk.percent, 2),
            "available_memory_mb": round(memory.available / (1024 * 1024), 2)
        }
    except Exception as e:
        log.error("system_metrics_failed", error=str(e))
        return {
            "cpu_percent": 0.0,
            "memory_mb": 0,
            "memory_percent": 0.0,
            "disk_percent": 0.0
        }


def get_process_metrics() -> Dict[str, Any]:
    """
    Get metrics for the current process
    
    Returns:
        Dict with process-specific metrics
    """
    try:
        process = psutil.Process()
        
        with process.oneshot():
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            num_threads = process.num_threads()
            create_time = process.create_time()
        
        uptime_seconds = int(datetime.now().timestamp() - create_time)
        
        return {
            "cpu_percent": round(cpu_percent, 2),
            "memory_mb": round(memory_info.rss / (1024 * 1024), 2),
            "num_threads": num_threads,
            "uptime_seconds": uptime_seconds
        }
    except Exception as e:
        log.error("process_metrics_failed", error=str(e))
        return {
            "cpu_percent": 0.0,
            "memory_mb": 0,
            "num_threads": 0,
            "uptime_seconds": 0
        }


# ============================================================================
# TIME UTILITIES
# ============================================================================

def seconds_ago(dt: datetime) -> float:
    """
    Calculate seconds elapsed since given datetime
    
    Args:
        dt: Datetime to compare against
    
    Returns:
        Seconds elapsed (float)
    """
    if dt is None:
        return float('inf')
    
    now = datetime.utcnow()
    if dt.tzinfo is not None:
        # Remove timezone info for comparison
        dt = dt.replace(tzinfo=None)
    
    delta = now - dt
    return delta.total_seconds()


def is_expired(dt: datetime, timeout_seconds: int) -> bool:
    """
    Check if datetime has expired based on timeout
    
    Args:
        dt: Datetime to check
        timeout_seconds: Timeout in seconds
    
    Returns:
        True if expired, False otherwise
    """
    return seconds_ago(dt) > timeout_seconds


def format_duration(seconds: float) -> str:
    """
    Format seconds into human-readable duration
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (e.g., "2h 30m", "45s", "3d 2h")
    """
    if seconds < 0:
        return "0s"
    
    days, seconds = divmod(int(seconds), 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts[:2])  # Return only first two components


# ============================================================================
# DATA VALIDATION
# ============================================================================

def validate_priority(priority: int) -> int:
    """
    Validate and clamp priority value
    
    Args:
        priority: Priority value to validate
    
    Returns:
        Validated priority (1-10)
    """
    return max(1, min(10, priority))


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to max length
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    
    return s[:max_length - len(suffix)] + suffix


def sanitize_task_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize task payload to remove potentially dangerous data
    
    Args:
        payload: Task payload dictionary
    
    Returns:
        Sanitized payload
    """
    # Remove any keys that might contain code execution
    dangerous_keys = {'exec', 'eval', 'compile', '__import__'}
    
    sanitized = {}
    for key, value in payload.items():
        if key.lower() not in dangerous_keys:
            if isinstance(value, dict):
                sanitized[key] = sanitize_task_payload(value)
            else:
                sanitized[key] = value
    
    return sanitized


# ============================================================================
# STATUS HELPERS
# ============================================================================

def is_terminal_status(status: str) -> bool:
    """
    Check if task status is terminal (no further transitions)
    
    Args:
        status: Task status string
    
    Returns:
        True if terminal status
    """
    terminal_statuses = {'completed', 'failed', 'cancelled'}
    return status in terminal_statuses


def is_active_status(status: str) -> bool:
    """
    Check if task status is active (in progress)
    
    Args:
        status: Task status string
    
    Returns:
        True if active status
    """
    active_statuses = {'pending', 'assigned', 'in_progress'}
    return status in active_statuses


# ============================================================================
# PAGINATION
# ============================================================================

def paginate_params(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    max_limit: int = 500,
    default_limit: int = 50
) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters
    
    Args:
        limit: Requested limit
        offset: Requested offset
        max_limit: Maximum allowed limit
        default_limit: Default limit if none provided
    
    Returns:
        Tuple of (validated_limit, validated_offset)
    """
    if limit is None:
        limit = default_limit
    else:
        limit = max(1, min(limit, max_limit))
    
    if offset is None:
        offset = 0
    else:
        offset = max(0, offset)
    
    return limit, offset


# ============================================================================
# JSON HELPERS
# ============================================================================

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely load JSON string, returning default on error
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
    
    Returns:
        Parsed JSON or default value
    """
    import json
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        log.warning("json_parse_failed", error=str(e), json_str=json_str[:100])
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely dump object to JSON string
    
    Args:
        obj: Object to serialize
        default: Default value if serialization fails
    
    Returns:
        JSON string or default value
    """
    import json
    
    try:
        return json.dumps(obj)
    except (TypeError, ValueError) as e:
        log.warning("json_dump_failed", error=str(e))
        return default


# ============================================================================
# ERROR FORMATTING
# ============================================================================

def format_error_response(
    error: Exception,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Format exception into error response dictionary
    
    Args:
        error: Exception object
        include_traceback: Include full traceback (development only)
    
    Returns:
        Error response dict
    """
    import traceback
    
    response = {
        "error": True,
        "error_type": type(error).__name__,
        "message": str(error)
    }
    
    if include_traceback:
        response["traceback"] = traceback.format_exc()
    
    return response


# ============================================================================
# CAPABILITY MATCHING
# ============================================================================

def capability_matches(
    required: Optional[str],
    available: list[str]
) -> bool:
    """
    Check if required capability is in available capabilities
    
    Args:
        required: Required capability string
        available: List of available capabilities
    
    Returns:
        True if capability is available or not required
    """
    if required is None or required == "":
        return True
    
    return required in available


# ============================================================================
# HEALTH CHECK
# ============================================================================

def create_health_response(
    droplet_id: int,
    name: str,
    steward: str,
    endpoint: str,
    status: str = "active",
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized UDC health response
    
    Args:
        droplet_id: Droplet ID
        name: Droplet name
        steward: Droplet steward
        endpoint: Droplet endpoint URL
        status: Current status
        message: Optional status message
    
    Returns:
        UDC-compliant health response dict
    """
    response = {
        "id": droplet_id,
        "name": name,
        "steward": steward,
        "status": status,
        "endpoint": endpoint,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if message:
        response["message"] = message
    
    return response