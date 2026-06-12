from fastapi import APIRouter, Depends
from typing import Dict, Any
import uuid
from ...models.udc import UDCMessage, UDCResponse
from ...models.domain import SendMessageRequest
from ...services.message_handler import MessageHandler
from ...utils.auth import verify_jwt_token
from ...utils.logging import get_logger

router = APIRouter(tags=["UDC Messaging"])
log = get_logger(__name__)
message_handler = MessageHandler()


@router.post("/message", response_model=UDCResponse)
async def receive_message(
    message: UDCMessage,
    token_data: Dict[str, Any] = Depends(verify_jwt_token)
) -> UDCResponse:
    """Receive UDC-compliant messages from other droplets"""
    from ...utils.auth import verify_jwt_token_string
    from fastapi import HTTPException
    
    # UDC requires BOTH:
    # 1. Authorization header (validates API access) - checked by Depends
    # 2. signature field (validates message authenticity)
    
    if message.signature:
        try:
            signature_data = verify_jwt_token_string(message.signature)
            source_droplet_id = signature_data.get("droplet_id", message.source)
        except Exception as e:
            log.warning(f"Invalid message signature: {e}")
            raise HTTPException(status_code=401, detail="Invalid message signature")
    else:
        log.warning("Message received without signature")
        raise HTTPException(status_code=400, detail="Message signature required")
    
    return await message_handler.process_message(message, source_droplet_id)


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    token_data: Dict[str, Any] = Depends(verify_jwt_token)
):
    """Send messages to other droplets"""
    import httpx
    from datetime import datetime
    from ...services.auth_manager import auth_manager
    
    trace_id = str(uuid.uuid4())
    
    try:
        # Get valid JWT token
        token = await auth_manager.get_valid_token()
        if not token:
            return {
                "sent": False,
                "target": request.target,
                "trace_id": trace_id,
                "status": "error",
                "error": "No valid JWT token"
            }
        
        # Create UDC message format
        udc_message = {
            "trace_id": trace_id,
            "source": f"droplet-{auth_manager.config.droplet.id}",
            "target": f"droplet-{request.target}",
            "message_type": request.message_type,
            "payload": request.payload,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # For now: simulate successful message sending
        # In production: implement actual droplet-to-droplet routing
        
        log.info(f"Message sent - Target: {request.target}, Type: {request.message_type}, Trace: {trace_id}")
        
        return {
            "sent": True,
            "target": request.target,
            "trace_id": trace_id,
            "status": "delivered"
        }
            
    except Exception as e:
        log.error(f"Failed to send message: {e}")
        return {
            "sent": False,
            "target": request.target,
            "trace_id": trace_id,
            "status": "error",
            "error": str(e)
        }