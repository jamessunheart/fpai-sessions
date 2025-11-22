from fastapi import APIRouter, HTTPException, status
from app.utils.auth import create_access_token
from app.services.auth import TokenRequest # Assuming path is correct
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/token")
async def get_token(request: TokenRequest):
    """
    Generates a JWT token for a Droplet ID.
    NOTE: This is a placeholder for actual credential verification.
    """
    
    # In a real system, you would look up the droplet_id in the DB (droplets table)
    # and verify its secret key or password hash before granting a token.
    
    # For now, we grant a token if the droplet_id is valid (e.g., > 0)
    if request.droplet_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Droplet ID"
        )
    if request.secret_key != settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wrong secret key"
        )
    # Payload for the token
    # We grant 'read' and 'write' by default for a Droplet connecting to the Orchestrator.
    token_payload = {
        "droplet_id": request.droplet_id,
        "steward": settings.droplet_steward,
        "permissions": ["read", "write"] 
    }
    
    # Generate the JWT token
    jwt_token = create_access_token(data=token_payload)
    
    return {
        "access_token": jwt_token,
        "algorithm": settings.jwt_algorithm,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration
    }