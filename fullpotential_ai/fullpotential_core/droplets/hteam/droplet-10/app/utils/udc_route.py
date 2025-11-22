"""
UDC Custom Route Class
Automatically handles UDC envelope wrapping/unwrapping

This solves the Pydantic validation issue by processing requests
in the route handler before model binding.

Usage:
    from app.utils.udc_route import UDCRoute
    
    router = APIRouter(route_class=UDCRoute)
"""
from fastapi import Request
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Any
import json
import structlog

from app.config import settings
from app.utils.udc_helpers import validate_udc_envelope, udc_wrap, udc_error

log = structlog.get_logger()


# Endpoints that should NOT have UDC wrapping
SKIP_UDC_WRAPPING = {
    "/health",
    "/capabilities",
    "/state",
    "/dependencies",
    "/message",  # Handles own UDC
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
}


class UDCRoute(APIRoute):
    """
    Custom FastAPI route class that automatically handles UDC envelopes.
    
    - Unwraps incoming POST/PATCH/DELETE requests before Pydantic validation
    - Wraps outgoing responses in UDC envelopes
    - Preserves trace_id throughout request lifecycle
    - Skips wrapping for public/special endpoints
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> JSONResponse:
            # Check if this endpoint should be skipped
            should_skip = request.url.path in SKIP_UDC_WRAPPING or request.url.path.startswith("/ws/")
            
            # STEP 1: UNWRAP REQUEST if needed
            if not should_skip and request.method in ["POST", "PATCH", "DELETE", "PUT"]:
                try:
                    body = await request.body()
                    
                    if body:
                        try:
                            data = json.loads(body)
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
                        
                        # Check if this is a UDC envelope
                        has_udc_envelope = ("udc_version" in data and "payload" in data)
                        
                        if has_udc_envelope:
                            # Validate UDC envelope
                            is_valid, error_msg = validate_udc_envelope(data)
                            if not is_valid:
                                log.warning(
                                    "invalid_udc_envelope",
                                    error=error_msg,
                                    path=request.url.path
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
                            
                            # Verify target
                            target = data.get("target")
                            expected_targets = [
                                settings.droplet_id,
                                f"droplet-{settings.droplet_id}",
                                str(settings.droplet_id),
                                "orchestrator",
                                "droplet-10"  # Explicitly allow orchestrator reference
                            ]
                            
                            if target not in expected_targets:
                                log.warning(
                                    "udc_target_mismatch",
                                    target=target,
                                    expected=expected_targets,
                                    path=request.url.path
                                )
                                return JSONResponse(
                                    status_code=400,
                                    content=udc_error(
                                        error_code="INVALID_REQUEST",
                                        error_message=f"Message target '{target}' does not match this droplet",
                                        source=f"droplet-{settings.droplet_id}",
                                        target=data.get("source", "client"),
                                        trace_id=data.get("trace_id")
                                    )
                                )
                            
                            # Store UDC metadata in request state
                            request.state.udc_trace_id = data.get("trace_id")
                            request.state.udc_source = data.get("source")
                            request.state.udc_target = target
                            request.state.udc_message_type = data.get("message_type")
                            request.state.udc_wrapped = True
                            
                            # Extract payload and replace request body
                            payload = data.get("payload", {})
                            new_body = json.dumps(payload).encode()
                            
                            # Replace the request body receive function
                            async def receive():
                                return {
                                    "type": "http.request",
                                    "body": new_body,
                                    "more_body": False
                                }
                            
                            request._receive = receive
                            
                            log.debug(
                                "udc_envelope_unwrapped",
                                path=request.url.path,
                                trace_id=data.get("trace_id"),
                                source=data.get("source"),
                                payload_size=len(new_body)
                            )
                        else:
                            # Not a UDC envelope - backward compatibility
                            log.debug(
                                "non_udc_request",
                                path=request.url.path,
                                note="Request not in UDC format"
                            )
                            request.state.udc_wrapped = False
                            
                except Exception as e:
                    log.error("udc_unwrap_failed", error=str(e), path=request.url.path)
                    return JSONResponse(
                        status_code=500,
                        content=udc_error(
                            error_code="INTERNAL_ERROR",
                            error_message=f"Failed to process UDC request: {str(e)}",
                            source=f"droplet-{settings.droplet_id}",
                            target="client"
                        )
                    )
            else:
                # GET requests or skipped endpoints
                request.state.udc_wrapped = False
            
            # STEP 2: CALL ORIGINAL HANDLER
            try:
                response = await original_route_handler(request)
            except Exception as e:
                log.error("route_handler_failed", error=str(e), path=request.url.path)
                # Re-raise to let FastAPI's exception handlers deal with it
                raise
            
            # STEP 3: WRAP RESPONSE if needed
            if not should_skip and isinstance(response, JSONResponse):
                try:
                    # Read response body
                    response_body = response.body
                    
                    if response_body:
                        response_data = json.loads(response_body)
                        
                        # Check if already UDC-wrapped
                        if "udc_version" not in response_data:
                            # Get UDC metadata from request
                            trace_id = getattr(request.state, 'udc_trace_id', None)
                            source_droplet = getattr(request.state, 'udc_source', None)
                            
                            # Wrap response in UDC envelope
                            wrapped = udc_wrap(
                                payload=response_data,
                                source=f"droplet-{settings.droplet_id}",
                                target=source_droplet or "client",
                                message_type="response",
                                trace_id=trace_id
                            )
                            
                            log.debug(
                                "udc_response_wrapped",
                                path=request.url.path,
                                trace_id=trace_id,
                                status_code=response.status_code
                            )
                            
                            return JSONResponse(
                                content=wrapped,
                                status_code=response.status_code,
                                headers=dict(response.headers)
                            )
                        
                except Exception as e:
                    log.error("udc_wrap_failed", error=str(e), path=request.url.path)
                    # Return original response if wrapping fails
            
            return response
        
        return custom_route_handler


def get_udc_metadata(request: Request) -> Dict[str, Any]:
    """
    Extract UDC metadata from request state.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(request: Request):
            udc = get_udc_metadata(request)
            trace_id = udc.get('trace_id')
            source = udc.get('source')
    
    Returns:
        dict: UDC metadata including trace_id, source, target, etc.
    """
    return {
        "trace_id": getattr(request.state, 'udc_trace_id', None),
        "source": getattr(request.state, 'udc_source', None),
        "target": getattr(request.state, 'udc_target', None),
        "message_type": getattr(request.state, 'udc_message_type', None),
        "wrapped": getattr(request.state, 'udc_wrapped', False)
    }