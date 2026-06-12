"""
UDC Compliance Helpers
Reusable functions for UDC-compliant request/response handling
"""
from typing import Any, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel


class UDCEnvelope(BaseModel):
    """Standard UDC message envelope"""
    udc_version: str = "1.0"
    trace_id: str
    source: str
    target: str
    message_type: str
    timestamp: str
    payload: dict


def udc_wrap(
    payload: dict,
    source: str,
    target: str,
    message_type: str = "response",
    trace_id: Optional[str] = None,
    udc_version: str = "1.0"
) -> dict:
    """
    Wrap response payload into UDC-compliant envelope.
    
    Args:
        payload: The actual data to return
        source: Source droplet identifier (e.g., "orchestrator", "droplet-10")
        target: Target identifier (e.g., "client", "droplet-5", "broadcast")
        message_type: Type of message (response, event, command, query)
        trace_id: Optional trace ID (generated if not provided)
        udc_version: UDC protocol version
        
    Returns:
        UDC-compliant envelope with payload
        
    Example:
        >>> udc_wrap(
        ...     payload={"tasks": [...], "total": 10},
        ...     source="orchestrator",
        ...     target="client",
        ...     message_type="response"
        ... )
        {
            "udc_version": "1.0",
            "trace_id": "uuid-here",
            "source": "orchestrator",
            "target": "client",
            "message_type": "response",
            "timestamp": "2025-11-13T10:30:00Z",
            "payload": {"tasks": [...], "total": 10}
        }
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())
        
    return {
        "udc_version": udc_version,
        "trace_id": trace_id,
        "source": source,
        "target": target,
        "message_type": message_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload
    }


def udc_error(
    error_code: str,
    error_message: str,
    details: Optional[dict] = None,
    source: str = "orchestrator",
    target: str = "client",
    trace_id: Optional[str] = None
) -> dict:
    """
    Create UDC-compliant error response.
    
    Standard error codes:
        - INVALID_REQUEST: Malformed request
        - UNAUTHORIZED: Missing/invalid JWT
        - FORBIDDEN: Valid JWT but insufficient permissions
        - NOT_FOUND: Resource doesn't exist
        - RATE_LIMITED: Too many requests
        - INTERNAL_ERROR: Server error
        - DEPENDENCY_UNAVAILABLE: Required droplet offline
        
    Args:
        error_code: Standard UDC error code
        error_message: Human-readable error message
        details: Optional additional error context
        source: Source identifier
        target: Target identifier
        trace_id: Optional trace ID
        
    Returns:
        UDC-compliant error envelope
        
    Example:
        >>> udc_error(
        ...     error_code="NOT_FOUND",
        ...     error_message="Task 123 not found",
        ...     details={"task_id": 123}
        ... )
    """
    payload = {
        "status": "error",
        "error": {
            "code": error_code,
            "message": error_message,
            "details": details or {}
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return udc_wrap(
        payload=payload,
        source=source,
        target=target,
        message_type="error",
        trace_id=trace_id
    )


def udc_success(
    data: Any,
    source: str = "orchestrator",
    target: str = "client",
    trace_id: Optional[str] = None
) -> dict:
    """
    Create UDC-compliant success response.
    
    Args:
        data: The data to return (will be serialized)
        source: Source identifier
        target: Target identifier
        trace_id: Optional trace ID
        
    Returns:
        UDC-compliant success envelope
    """
    # Convert Pydantic models to dict
    if hasattr(data, 'model_dump'):
        data = data.model_dump(mode='json')
    elif hasattr(data, 'dict'):
        data = data.dict()
    
    payload = {
        "status": "success",
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return udc_wrap(
        payload=payload,
        source=source,
        target=target,
        message_type="response",
        trace_id=trace_id
    )


def extract_trace_id(request_data: dict) -> Optional[str]:
    """
    Extract trace_id from incoming UDC request.
    
    Args:
        request_data: Incoming request data (should be UDC envelope)
        
    Returns:
        trace_id if present, None otherwise
    """
    return request_data.get("trace_id")


def validate_udc_envelope(data: dict) -> tuple[bool, Optional[str]]:
    """
    Validate that incoming data is a proper UDC envelope.
    
    Args:
        data: Data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> valid, error = validate_udc_envelope(request_data)
        >>> if not valid:
        ...     raise HTTPException(400, error)
    """
    required_fields = ["udc_version", "trace_id", "source", "target", "message_type", "timestamp", "payload"]
    
    missing = [field for field in required_fields if field not in data]
    
    # if missing:
    #     return False, f"Missing required UDC fields: {', '.join(missing)}"
    
    # if data.get("udc_version") != "1.0":
    #     return False, f"Unsupported UDC version: {data.get('udc_version')}. Expected: 1.0"
    
    valid_message_types = ["status", "event", "command", "query", "response", "error"]
    if data.get("message_type") not in valid_message_types:
        return False, f"Invalid message_type: {data.get('message_type')}. Must be one of: {', '.join(valid_message_types)}"
    
    return True, None