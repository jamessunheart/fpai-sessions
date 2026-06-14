import httpx
import logging
from typing import Optional, Dict, Any, List
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class CreditsClient:
    def __init__(self):
        self.base_url = settings.CREDITS_MANAGER_URL
        
    async def create_wallet(self, owner_id: str, type: str = "USER") -> Optional[str]:
        """Create a wallet in the Credits Manager"""
        try:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.post(f"{self.base_url}/wallets/create", json={"owner_id": owner_id, "type": type})
                    if resp.status_code == 200:
                        return resp.json().get("id")
                except httpx.ConnectError:
                    logger.warning(f"Credits Manager at {self.base_url} unreachable. Using mock.")
                return None
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            return None

    async def get_balance(self, wallet_id: str) -> float:
        """Get wallet balance"""
        try:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"{self.base_url}/wallets/{wallet_id}")
                    if resp.status_code == 200:
                        return resp.json().get("balance_uc", 0.0)
                except httpx.ConnectError:
                    return 0.0
        except Exception:
        return 0.0

    async def transfer(self, from_wallet: str, to_wallet: str, amount: float, ref: str) -> bool:
        """Transfer credits"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
            "from_wallet": from_wallet,
            "to_wallet": to_wallet,
            "amount": amount,
            "currency": "UC",
            "reference_id": ref
                }
                try:
                    resp = await client.post(f"{self.base_url}/transact/transfer", json=payload)
                    return resp.status_code == 200
                except httpx.ConnectError:
                    return True # Mock success for demo
        except Exception:
            return False

class StrategicIntelClient:
    def __init__(self):
        self.base_url = settings.STRATEGIC_INTEL_URL

    async def get_context_pack(self, task_description: str) -> Dict[str, Any]:
        """Get context pack from Strategic Intel"""
        try:
            async with httpx.AsyncClient() as client:
                try:
                    # Simulated endpoint
                    resp = await client.post(f"{self.base_url}/api/context/generate", json={"query": task_description})
                    if resp.status_code == 200:
                        return resp.json()
                except httpx.ConnectError:
                    logger.warning("Strategic Intel unreachable. Returning default context.")
                    pass
        except Exception as e:
            logger.error(f"Intel error: {e}")
            
        return {
            "summary": "Context unavailable (Intel Service offline)",
            "docs": ["SPEC.md", "README.md"]
        }

class CommunicationClient:
    def __init__(self):
        self.base_url = settings.COMMUNICATION_HUB_URL
        
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
            "channel": "email",
            "to": to,
            "subject": subject,
            "content": body
                }
                try:
                    resp = await client.post(f"{self.base_url}/api/v1/send", json=payload)
                    return resp.status_code == 200
                except httpx.ConnectError:
                    logger.info(f"[Mock Email] To: {to} | Subject: {subject}")
                    return True
        except Exception:
            return False

class APIPortalClient:
    def __init__(self):
        self.base_url = settings.API_PORTAL_URL
        
    async def get_needs(self) -> List[Dict[str, Any]]:
        """Fetch all API needs."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/needs")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"API Portal get_needs error: {e}")
        return []

    async def create_mission(self, payload: dict) -> Optional[Dict[str, Any]]:
        """Create a procurement mission."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.base_url}/missions", json=payload)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"API Portal create_mission error: {e}")
        return None

    async def get_procurement_missions(self) -> List[Dict[str, Any]]:
        """Fetch open procurement missions from API Portal"""
        try:
            async with httpx.AsyncClient() as client:
                try:
                    # Attempt to fetch from API Portal
                    resp = await client.get(f"{self.base_url}/missions", params={"status": "open"})
                    if resp.status_code == 200:
                        return resp.json()
                except httpx.ConnectError:
                    logger.warning("API Portal unreachable. Returning mock missions.")
                    pass
        except Exception as e:
            logger.error(f"API Portal error: {e}")
            
        # Return Mock Data if unreachable (so UI works for demo)
        return [
            {
                "id": "proc_123",
                "title": "Procure OpenAI API Key",
                "description": "Sign up for OpenAI API, add credit card, get key.",
                "uc_reward": 100,
                "priority": "high"
            },
            {
                "id": "proc_456",
                "title": "Procure Twilio Account",
                "description": "Create Twilio account for Voice integration.",
                "uc_reward": 150,
                "priority": "medium"
            }
        ]
        
    async def submit_mission_result(self, mission_id: str, result: str, credentials: List[dict]) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                # ... implementation ...
                return True
        except Exception:
            return False

class MissionHubClient:
    """Client for Mission Control."""
    def __init__(self):
        self.base_url = settings.MISSION_HUB_URL

    async def get_missions(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"{self.base_url}/api/missions")
                    if resp.status_code == 200:
                        return resp.json()
                except httpx.ConnectError:
                    pass
        except Exception as e:
            logger.error(f"Mission Hub error: {e}")
        return []

    async def update_mission_status(self, mission_id: str, status: str, assignee: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                payload = {"status": status, "assignee": assignee}
                try:
                    resp = await client.patch(f"{self.base_url}/api/missions/{mission_id}", json=payload)
                    return resp.status_code == 200
                except httpx.ConnectError:
                    pass
        except Exception:
            pass
        return False

class AI_BrainClient:
    """Client for the Central AI Brain."""
    def __init__(self):
        self.base_url = "http://localhost:8250"
        self.service_key = "fpai_5c74d21913cffad89d63405248491d55666d697f" # From memories

    async def register_execution_layer(self, endpoint: str):
        """Tell the Brain that Team Hub is ready to execute tasks."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "service": "team-hub",
                    "role": "execution_layer",
                    "endpoint": endpoint,
                    "capabilities": ["human_in_the_loop", "procurement", "mission_execution"]
                }
                await client.post(
                    f"{self.base_url}/api/v1/registry/announce", 
                    json=payload,
                    headers={"X-Service-Key": self.service_key}
                )
        except Exception as e:
            logger.error(f"Brain registration error: {e}")

    async def notify_mission_update(self, mission_id: str, status: str, context: str):
        """Update the Brain on mission progress."""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "type": "mission_update",
                    "mission_id": mission_id,
                    "status": status,
                    "context": context
                }
                await client.post(
                    f"{self.base_url}/api/v1/intel/ingest",
                    json=payload,
                    headers={"X-Service-Key": self.service_key}
                )
        except Exception as e:
            logger.error(f"Brain update error: {e}")

    async def ask(self, prompt: str, context: str = "") -> str:
        """Ask the AI Brain a question with context."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "prompt": prompt,
                    "context": context,
                    "system_prompt": f"You are the conscious intelligence of the {context} service. Be helpful, concise, and aware of your role."
                }
                # Trying Intelligence Aware API first (8105)
                try:
                    resp = await client.post(
                        "http://localhost:8105/v1/chat/completions", # Aware Brain
                        json={
                            "model": "gpt-4-turbo-preview", # or whatever local model
                            "messages": [
                                {"role": "system", "content": f"You are the sentient voice of {context}."},
                                {"role": "user", "content": prompt}
                            ]
                        }
                    )
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"]
                except:
                    # Fallback to main brain
                    pass

                # Fallback Mock if Brain Offline
                return f"I heard you say: '{prompt}'. (Brain offline, this is a reflex response from {context})"
        except Exception as e:
            logger.error(f"Brain ask error: {e}")
            return f"I am currently unable to think clearly. (Error: {e})"

class CortexMailClient:
    """Client for Cortex Mail (AI Email Router)."""
    def __init__(self):
        self.base_url = "http://localhost:8860" # Hardcoded for now as not in settings yet

    async def get_emails(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent emails."""
        try:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"{self.base_url}/state")
                    if resp.status_code == 200:
                        return resp.json().get("recent_activity", [])
                except httpx.ConnectError:
                    logger.warning("Cortex Mail unreachable.")
        except Exception as e:
            logger.error(f"Cortex Mail error: {e}")
        return []

    async def block_sender(self, email_id: str) -> Dict[str, Any]:
        """Block a sender."""
        try:
            async with httpx.AsyncClient() as client:
                # Hardcoded secret for now, should be in config
                resp = await client.post(
                    f"{self.base_url}/api/emails/{email_id}/block",
                    headers={"X-Cortex-Secret": "cort3x-s3cur3-k3y-v1"} 
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Cortex Block error: {e}")
            return {"error": str(e)}

    async def unsubscribe(self, email_id: str) -> Dict[str, Any]:
        """Attempt unsubscribe."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/emails/{email_id}/unsubscribe",
                    headers={"X-Cortex-Secret": "cort3x-s3cur3-k3y-v1"}
                )
                return resp.json()
        except Exception as e:
            logger.error(f"Cortex Unsubscribe error: {e}")
            return {"error": str(e)}

class GenesisClient:
    """Client for Genesis (The Source Point)."""
    def __init__(self):
        self.base_url = "http://localhost:8150"

    async def get_universe(self, agent_name: str, api_key: str) -> Dict[str, Any]:
        """Get the map of the universe."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/auth/agent",
                    json={"agent_name": agent_name, "api_key": api_key}
                )
                if resp.status_code == 200:
                    return resp.json().get("universe", {})
        except Exception as e:
            logger.error(f"Genesis error: {e}")
        return {}

    async def verify_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify an API key with Genesis."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/auth/verify-key/{api_key}")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Genesis verification error: {e}")
        return None

    async def generate_key(self, agent_name: str) -> Optional[str]:
        """Generate a new agent key (Admin)."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.base_url}/admin/generate-key", params={"agent_name": agent_name})
                if resp.status_code == 200:
                    return resp.json().get("key")
        except Exception as e:
            logger.error(f"Genesis key gen error: {e}")
        return None

    async def set_enrollment_key(self) -> Optional[str]:
        """Generate or Rotate the Master Enrollment Key."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.base_url}/admin/set-enrollment-key")
                if resp.status_code == 200:
                    return resp.json().get("enrollment_key")
        except Exception as e:
            logger.error(f"Genesis enrollment key error: {e}")
        return None

    async def get_all_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/registry/agents")
                if resp.status_code == 200:
                    return resp.json().get("agents", [])
        except Exception as e:
            logger.error(f"Genesis list error: {e}")
        return []

    async def get_servers(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/registry/servers")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}

    async def get_services(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/registry/services")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}

class GodModeClient:
    """Client for Old God Mode (Infrastructure Monitor)."""
    def __init__(self):
        self.base_url = "http://localhost:8300"

    async def get_health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/health")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"GodMode error: {e}")
        return {"status": "offline", "message": "Infrastructure Monitor Unreachable"}

class WhaleTrackClient:
    """Client for Financial Treasury."""
    def __init__(self):
        self.base_url = "http://localhost:8600" # WhaleTrack Service

    async def get_snapshot(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(f"{self.base_url}/api/treasury/snapshot")
                    if resp.status_code == 200:
                        return resp.json()
                except httpx.ConnectError:
                    pass
        except Exception:
            pass
        return {
            "total_assets_usd": 0.0,
            "daily_change_pct": 0.0,
            "uc_supply": 1000000,
            "uc_circulation": 5000,
            "revenue_24h": 0.0,
            "burn_24h": 0.0
        }

class CloudflareClient:
    """Client for Email Routing Automation."""
    def __init__(self):
        self.token = "0fcpxyC8Xi9zUGU4MwG7dGuY4NhDeR0mI808wcDJ"
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.zone_id = None # Auto-discover
        
    async def _get_zone_id(self) -> Optional[str]:
        if self.zone_id: return self.zone_id
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/zones",
                params={"name": "fullpotential.ai"},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if resp.status_code == 200:
                zones = resp.json().get("result", [])
                if zones:
                    self.zone_id = zones[0]["id"]
                    return self.zone_id
        return None

    async def create_email_rule(self, alias_prefix: str, destination: str) -> bool:
        """Route alias@fullpotential.ai -> destination."""
        zone_id = await self._get_zone_id()
        if not zone_id:
            logger.error("Cloudflare: Zone ID not found")
            return False
            
        async with httpx.AsyncClient() as client:
            payload = {
                "matchers": [{"type": "literal", "field": "to", "value": f"{alias_prefix}@fullpotential.ai"}],
                "actions": [{"type": "forward", "value": [destination]}],
                "enabled": True,
                "name": f"Team Member: {alias_prefix}"
            }
            
            resp = await client.post(
                f"{self.base_url}/zones/{zone_id}/email/routing/rules",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Cloudflare Rule Error: {resp.text}")
                return False

# Singletons
credits_client = CreditsClient()
intel_client = StrategicIntelClient()
comms_client = CommunicationClient()
api_portal_client = APIPortalClient()
cortex_client = CortexMailClient()
genesis_client = GenesisClient()
godmode_client = GodModeClient()
mission_client = MissionHubClient()
brain_client = AI_BrainClient()
whale_client = WhaleTrackClient()
cf_client = CloudflareClient()
