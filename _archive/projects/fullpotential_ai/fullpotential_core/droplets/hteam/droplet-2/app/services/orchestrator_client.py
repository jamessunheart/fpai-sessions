import httpx
import uuid
from datetime import datetime, timezone
from .token_manager import token_manager

class OrchestratorClient:
    def __init__(self):
        import os
        self.orchestrator_url = "https://drop10.fullpotential.ai"
        self.droplet_id = int(os.getenv('DROPLET_ID', 42))
        self.name = os.getenv('DROPLET_NAME', 'droplet0')
        self.endpoint = os.getenv('DROPLET_ENDPOINT', 'http://localhost:8002')
        self.steward = os.getenv('DROPLET_STEWARD', 'Haythem')
        self.capabilities = ["udc_compliance", "health_monitoring", "message_handling"]
    
    async def register(self):
        token = token_manager.generate_token()
        
        # Direct payload format (not UDC envelope)
        payload = {
            "droplet_id": self.droplet_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "version": "1.0.0",
            "status": "active"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.orchestrator_url}/droplets/register",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                if response.status_code in [200, 201]:
                    print(f"[OK] Registered with Orchestrator: {self.name}")
                    return response.json()
                else:
                    print(f"[FAIL] Registration failed: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                print(f"[ERROR] Registration error: {e}")
                return None

orchestrator_client = OrchestratorClient()
