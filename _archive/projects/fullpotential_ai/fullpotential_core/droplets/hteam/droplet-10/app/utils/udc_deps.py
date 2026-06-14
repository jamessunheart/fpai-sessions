"""
UDC Request Handler - Dependency-based Solution
This actually works because it uses raw Request instead of Pydantic models

Place in: app/utils/udc_deps.py
"""
from fastapi import Request, HTTPException
from typing import Dict, Any
import json
import structlog

from app.config import settings
from app.utils.udc_helpers import validate_udc_envelope

log = structlog.get_logger()


async def parse_udc_request(request: Request) -> Dict[str, Any]:
    """
    Parse and unwrap UDC envelope from request body.
    Returns the unwrapped payload as a dict.
    
    Usage in endpoint:
        @router.post("/tasks")
        async def create_task(request: Request):
            payload = await parse_udc_request(request)
            task = TaskCreate(**payload)  # Manual validation
            ...
    """
    if request.method not in ["POST", "PATCH", "DELETE", "PUT"]:
        return {}
    
    try:
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")
        
        data = json.loads(body)
        
        # Check if UDC wrapped
        if "udc_version" in data and "payload" in data:
            # Validate envelope
            is_valid, error_msg = validate_udc_envelope(data)
            if not is_valid:
                log.warning("invalid_udc_envelope", error=error_msg)
                raise HTTPException(status_code=400, detail=f"Invalid UDC envelope: {error_msg}")
            
            # Store metadata
            request.state.udc_trace_id = data.get("trace_id")
            request.state.udc_source = data.get("source")
            request.state.udc_target = data.get("target")
            request.state.udc_wrapped = True
            
            log.debug("udc_unwrapped", trace_id=data.get("trace_id"), source=data.get("source"))
            
            # Return unwrapped payload
            return data.get("payload", {})
        else:
            # Not UDC wrapped - backward compat
            request.state.udc_wrapped = False
            return data
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except HTTPException:
        raise
    except Exception as e:
        log.error("udc_parse_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")


def get_udc_metadata(request: Request) -> Dict[str, Any]:
    """Extract UDC metadata from request state"""
    return {
        "trace_id": getattr(request.state, 'udc_trace_id', None),
        "source": getattr(request.state, 'udc_source', None),
        "target": getattr(request.state, 'udc_target', None),
        "wrapped": getattr(request.state, 'udc_wrapped', False)
    }


def wrap_udc_response(data: Any, request: Request) -> Dict[str, Any]:
    """Wrap response in UDC envelope"""
    from app.utils.udc_helpers import udc_wrap
    
    udc = get_udc_metadata(request)
    return udc_wrap(
        payload=data,
        source=f"droplet-{settings.droplet_id}",
        target=udc.get('source') or "client",
        message_type="response",
        trace_id=udc.get('trace_id')
    )


# ============================================================================
# USAGE IN ENDPOINTS
# ============================================================================

"""
EXAMPLE: Create Task Endpoint

from app.utils.udc_deps import parse_udc_request, wrap_udc_response, get_udc_metadata
from app.models.domain import TaskCreate

@router.post("/tasks", status_code=201)
async def create_task(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    # Parse UDC request
    payload = await parse_udc_request(request)
    
    # Manually validate with Pydantic
    try:
        task = TaskCreate(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    
    # Get UDC metadata
    udc = get_udc_metadata(request)
    
    # Your business logic
    result = await create_task_in_db(task)
    
    # Wrap response
    return wrap_udc_response(
        {"task_id": result['id'], "status": "pending"},
        request
    )
"""