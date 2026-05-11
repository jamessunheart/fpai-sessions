"""
UDC /send endpoint
Sends messages to other droplets
"""

import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.models.udc import SendMessageRequest
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event, record_action
from app.utils.helpers import get_trace_id
from app.services.jwt_service import fetch_registry_jwt_token

router = APIRouter()


@router.post("/send")
async def send_message(
    req: SendMessageRequest,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    UDC Compliant: Send messages to other droplets
    Looks up target droplet and forwards message
    """
    trace_id = get_trace_id(request)
    
    try:
        # Get JWT token for authentication
        token = await fetch_registry_jwt_token()
        if not token:
            raise HTTPException(503, "Cannot authenticate with Registry")
        
        # Lookup target droplet from Registry
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to resolve target as droplet ID or name
            registry_response = await client.get(
                f"{settings.registry_url}/registry/droplet/{req.target}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if registry_response.status_code != 200:
                raise HTTPException(404, f"Target droplet '{req.target}' not found")
            
            target_info = registry_response.json()
            target_endpoint = target_info.get("endpoint")
            
            if not target_endpoint:
                raise HTTPException(500, f"No endpoint found for droplet '{req.target}'")
        
        # Construct UDC message
        message = {
            "trace_id": trace_id,
            "source": settings.droplet_id,
            "target": target_info.get("id", req.target),
            "message_type": req.message_type,
            "payload": req.payload,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send message to target droplet
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{target_endpoint}/message",
                json=message,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code in [200, 201]:
                log.info(
                    "message_sent",
                    trace_id=trace_id,
                    target=req.target,
                    message_type=req.message_type
                )
                record_action(f"send_message_to_{req.target}", trace_id)
                log_event("message_sent", {
                    "target": req.target,
                    "message_type": req.message_type
                }, trace_id)
                
                return {
                    "sent": True,
                    "trace_id": trace_id,
                    "target": req.target,
                    "status": "delivered"
                }
            else:
                raise HTTPException(
                    response.status_code,
                    f"Failed to deliver message: {response.text}"
                )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "message_send_error",
            trace_id=trace_id,
            error=str(e)
        )
        raise HTTPException(500, f"Failed to send message: {str(e)}")
