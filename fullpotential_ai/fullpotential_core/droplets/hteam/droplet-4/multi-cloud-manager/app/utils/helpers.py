"""
Utility helper functions
Common functions used across the application
"""

import uuid
from typing import Optional
from fastapi import Request


def get_trace_id(request: Request) -> str:
    """
    Extract or generate trace_id from request headers
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Trace ID string (from header or newly generated)
    """
    trace_id = request.headers.get("X-Trace-ID")
    if not trace_id:
        trace_id = str(uuid.uuid4())
    return trace_id


def format_error_response(code: str, message: str, details: Optional[dict] = None) -> dict:
    """
    Format error response according to UDC standards
    
    Args:
        code: Error code (e.g., "INVALID_REQUEST")
        message: Human-readable error message
        details: Optional additional error details
    
    Returns:
        Formatted error dictionary
    """
    from datetime import datetime
    
    return {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def format_success_response(data: dict) -> dict:
    """
    Format success response according to UDC standards
    
    Args:
        data: Response data dictionary
    
    Returns:
        Formatted success dictionary
    """
    from datetime import datetime
    
    return {
        "status": "success",
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
