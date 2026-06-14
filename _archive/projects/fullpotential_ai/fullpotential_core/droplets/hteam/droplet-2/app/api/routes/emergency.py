from fastapi import APIRouter, Depends
from typing import Dict, Any
from ...utils.auth import verify_jwt_token
from ...utils.logging import get_logger

router = APIRouter(tags=["UDC Emergency"])
log = get_logger(__name__)


@router.post("/emergency-stop")
async def emergency_stop(
    token_data: Dict[str, Any] = Depends(verify_jwt_token)
):
    """Immediate stop without cleanup (emergency only)"""
    
    log.critical(f"Emergency stop requested by droplet {token_data.get('droplet_id')}")
    
    # In production: actually perform emergency stop
    # For demo: just return acknowledgment
    
    return {
        "emergency_stop": True,
        "initiated_by": token_data.get("droplet_id"),
        "timestamp": "2025-11-17T23:45:00Z"
    }