"""
UDC /message endpoint
Receives messages from other droplets
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Request

from app.models.udc import UDCMessage, MessageResponse
from app.utils.auth import verify_jwt_token
from app.utils.logging import log, log_event, record_action
from app.utils.state import message_queue, add_connected_droplet
from app.utils.helpers import get_trace_id

router = APIRouter()


@router.post("/message", response_model=MessageResponse)
async def receive_message(
    message: UDCMessage,
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    UDC Compliant: Receive UDC-formatted messages from other droplets
    Processes incoming events, queries, commands, and responses
    """
    trace_id = message.trace_id or get_trace_id(request)
    
    # Log incoming message
    log.info(
        "message_received",
        trace_id=trace_id,
        source=message.source,
        target=message.target,
        message_type=message.message_type
    )
    
    # Track connected droplet
    add_connected_droplet(str(message.source))
    
    # Queue message for processing
    message_queue.append({
        "message": message.dict(),
        "received_at": datetime.utcnow().isoformat(),
        "processed": False
    })
    
    # Record action
    record_action(f"receive_message_from_{message.source}", trace_id)
    
    # Log event
    log_event("message_received", {
        "source": message.source,
        "message_type": message.message_type,
        "payload_keys": list(message.payload.keys())
    }, trace_id)
    
    return {
        "received": True,
        "trace_id": trace_id,
        "processed_at": datetime.utcnow().isoformat(),
        "result": "success"
    }
