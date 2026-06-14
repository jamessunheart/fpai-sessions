"""
UDC Request/Response Middleware
Automatic wrapping/unwrapping of UDC envelopes for all endpoints
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json
import structlog
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.config import settings
from app.utils.udc_helpers import validate_udc_envelope, udc_error

log = structlog.get_logger()


class UDCMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle UDC envelope wrapping/unwrapping
    
    - For POST/PATCH/DELETE: Expects UDC-wrapped request, unwraps payload
    - For all responses: Wraps response data in UDC envelope
    - Skips UDC wrapping for:
      - /health, /capabilities, /state, /dependencies (public UDC endpoints)
      - /docs, /redoc, /openapi.json (Swagger)
      - WebSocket connections
    """
    
    # Endpoints that should NOT be wrapped (already UDC compliant or public)
    SKIP_WRAPPING = {
        "/health",
        "/capabilities", 
        "/state",
        "/dependencies",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/management/version",  # Already wrapped in endpoint
    }
    
    # Endpoints that need REQUEST unwrapping (POST/PATCH/DELETE)
    UNWRAP_REQUEST_METHODS = {"POST", "PATCH", "DELETE", "PUT"}
    
    async def dispatch(self, request: Request, call_next):
        """Process request and response with UDC wrapping"""
        
        # Skip WebSocket and static paths
        if request.url.path.startswith("/ws/") or request.url.path in self.SKIP_WRAPPING:
            return await call_next(request)
        
        # Check if this is a mutating method that needs unwrapping
        needs_unwrap = request.method in self.UNWRAP_REQUEST_METHODS
        
        trace_id = None
        source = None
        target = None
        
        # UNWRAP REQUEST if needed
        if needs_unwrap and request.method != "GET":
            try:
                # Read request body
                body = await request.body()
                
                if body:
                    request_data = json.loads(body)
                    
                    # Validate UDC envelope
                    is_valid, error_msg = validate_udc_envelope(request_data)
                    
                    if not is_valid:
                        log.warning(
                            "invalid_udc_request",
                            path=request.url.path,
                            error=error_msg
                        )
                        return JSONResponse(
                            status_code=400,
                            content=udc_error(
                                error_code="INVALID_REQUEST",
                                error_message=f"Invalid UDC envelope: {error_msg}",
                                source=f"droplet-{settings.droplet_id}",
                                target="client"
                            )
                        )
                    
                    # Extract trace_id and routing info
                    trace_id = request_data.get("trace_id")
                    source = request_data.get("source")
                    target = request_data.get("target")
                    
                    # Verify target matches this droplet
                    expected_targets = [
                        settings.droplet_id,
                        f"droplet-{settings.droplet_id}",
                        str(settings.droplet_id),
                        "orchestrator"
                    ]
                    
                    if target not in expected_targets:
                        log.warning(
                            "udc_target_mismatch",
                            expected=expected_targets,
                            received=target
                        )
                        return JSONResponse(
                            status_code=400,
                            content=udc_error(
                                error_code="INVALID_REQUEST",
                                error_message=f"Message target '{target}' does not match this droplet",
                                source=f"droplet-{settings.droplet_id}",
                                target=source,
                                trace_id=trace_id
                            )
                        )
                    
                    # Extract payload and inject into request
                    payload = request_data.get("payload", {})
                    
                    # Create new request with unwrapped payload
                    async def receive():
                        return {
                            "type": "http.request",
                            "body": json.dumps(payload).encode(),
                            "more_body": False
                        }
                    
                    request._receive = receive
                    
                    # Store UDC metadata in request state for use in endpoints
                    request.state.udc_trace_id = trace_id
                    request.state.udc_source = source
                    request.state.udc_target = target
                    
                    log.debug(
                        "udc_request_unwrapped",
                        path=request.url.path,
                        trace_id=trace_id,
                        source=source
                    )
                    
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=400,
                    content=udc_error(
                        error_code="INVALID_REQUEST",
                        error_message="Invalid JSON in request body",
                        source=f"droplet-{settings.droplet_id}",
                        target="client"
                    )
                )
            except Exception as e:
                log.error("udc_unwrap_failed", error=str(e))
                return JSONResponse(
                    status_code=500,
                    content=udc_error(
                        error_code="INTERNAL_ERROR",
                        error_message=f"Failed to process UDC request: {str(e)}",
                        source=f"droplet-{settings.droplet_id}",
                        target="client"
                    )
                )
        
        # Call the actual endpoint
        response = await call_next(request)
        
        # WRAP RESPONSE (for non-skipped endpoints)
        if request.url.path not in self.SKIP_WRAPPING and response.status_code < 500:
            try:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Parse response JSON
                if response_body:
                    response_data = json.loads(response_body)
                    
                    # Check if already wrapped (some endpoints do this manually)
                    if "udc_version" in response_data:
                        # Already wrapped, return as-is
                        return Response(
                            content=response_body,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type="application/json"
                        )
                    
                    # Wrap in UDC envelope
                    wrapped = {
                        "udc_version": "1.0",
                        "trace_id": trace_id or getattr(request.state, 'udc_trace_id', None) or str(uuid.uuid4()),
                        "source": f"droplet-{settings.droplet_id}",
                        "target": source or getattr(request.state, 'udc_source', None) or "client",
                        "message_type": "response",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "payload": response_data
                    }
                    
                    log.debug(
                        "udc_response_wrapped",
                        path=request.url.path,
                        trace_id=wrapped["trace_id"]
                    )
                    
                    return JSONResponse(
                        content=wrapped,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
                
            except json.JSONDecodeError:
                # Non-JSON response, return as-is
                pass
            except Exception as e:
                log.error("udc_wrap_failed", error=str(e))
        
        return response


# Helper function to extract UDC metadata from request
def get_udc_metadata(request: Request) -> dict:
    """
    Extract UDC metadata from request state
    
    Usage in endpoints:
        metadata = get_udc_metadata(request)
        trace_id = metadata.get('trace_id')
    """
    return {
        "trace_id": getattr(request.state, 'udc_trace_id', None),
        "source": getattr(request.state, 'udc_source', None),
        "target": getattr(request.state, 'udc_target', None)
    }


# Usage instructions for the middleware:
"""
USAGE INSTRUCTIONS:
===================

1. Add to main.py BEFORE the CORS middleware:

    from app.middleware.udc_middleware import UDCMiddleware
    
    app.add_middleware(UDCMiddleware)
    app.add_middleware(CORSMiddleware, ...)


2. Update endpoints to remove manual UDC wrapping:

   BEFORE:
   -------
   @router.post("/tasks")
   async def create_task(task: TaskCreate):
       result = await create_task_in_db(task)
       return udc_wrap(payload=result, source=..., target=...)
   
   AFTER:
   ------
   @router.post("/tasks")
   async def create_task(task: TaskCreate, request: Request):
       metadata = get_udc_metadata(request)
       result = await create_task_in_db(task)
       return result  # Middleware wraps automatically


3. For incoming POST/PATCH/DELETE requests:

   CLIENT SENDS:
   {
       "udc_version": "1.0",
       "trace_id": "uuid-here",
       "source": "droplet-5",
       "target": "droplet-10",
       "message_type": "command",
       "timestamp": "2025-11-14T10:30:00Z",
       "payload": {
           "task_type": "verify",
           "title": "Verify Droplet #14",
           ...
       }
   }
   
   ENDPOINT RECEIVES (unwrapped):
   {
       "task_type": "verify",
       "title": "Verify Droplet #14",
       ...
   }
   
   ENDPOINT RETURNS:
   {
       "task_id": 123,
       "status": "pending",
       ...
   }
   
   CLIENT RECEIVES (wrapped):
   {
       "udc_version": "1.0",
       "trace_id": "uuid-here",
       "source": "droplet-10",
       "target": "droplet-5",
       "message_type": "response",
       "timestamp": "2025-11-14T10:30:01Z",
       "payload": {
           "task_id": 123,
           "status": "pending",
           ...
       }
   }


4. Endpoints that handle their own UDC wrapping:
   - Add path to SKIP_WRAPPING set in middleware
   - /message endpoint (already handles full UDC)
   - /management endpoints (already wrapped)


5. GET requests:
   - No unwrapping needed (query params only)
   - Response automatically wrapped
   - Use get_udc_metadata(request) to get trace_id if needed
"""