from pydantic import BaseModel

class TokenRequest(BaseModel):
    """Schema for requesting a JWT token."""
    droplet_id: int
    secret_key: str
    # Note: In a real system, you'd verify a secret/key here,
    # but for simplicity, we'll use the ID.
    # secret_key: str