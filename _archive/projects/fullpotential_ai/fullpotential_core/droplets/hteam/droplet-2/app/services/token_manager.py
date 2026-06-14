import jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path

class TokenManager:
    def __init__(self, droplet_id: int = 42):
        self.droplet_id = droplet_id
        self.private_key = self._load_private_key()
    
    def _load_private_key(self) -> str:
        key_path = Path(__file__).parent / "private_key.pem"
        return key_path.read_text()
    
    def generate_token(self) -> str:
        payload = {
            'droplet_id': self.droplet_id,
            'iat': int(datetime.now(timezone.utc).timestamp()),
            'exp': int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())
        }
        return jwt.encode(payload, self.private_key, algorithm='RS256')

from ..config import settings
token_manager = TokenManager(droplet_id=settings.droplet_id)
