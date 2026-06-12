import httpx
import asyncio
from typing import Dict, Any, List
from ..config import settings
from ..utils.logging import get_logger

log = get_logger(__name__)


class RegistryService:
    """Service for Registry communication"""
    
    def __init__(self):
        self.base_url = settings.registry_url
    
    async def register_droplet(self) -> Dict[str, Any]:
        """Register this droplet with Registry"""
        registration_data = {
            "id": settings.droplet_id,
            "name": settings.droplet_name,
            "steward": settings.droplet_steward,
            "endpoint": settings.droplet_url,
            "capabilities": [
                "udc_compliance",
                "health_monitoring", 
                "message_handling"
            ],
            "version": "1.0.0",
            "status": "active"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/register",
                    json=registration_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    log.info(f"Droplet registered - ID: {settings.droplet_id}, Name: {settings.droplet_name}")
                    return response.json()
                else:
                    log.error(f"Registration failed - Status: {response.status_code}, Response: {response.text}")
                    raise Exception(f"Registration failed: {response.status_code}")
                    
        except Exception as e:
            log.error(f"Registry unreachable: {str(e)}")
            # Retry with exponential backoff
            await asyncio.sleep(5)
            return await self.register_droplet()
    
    async def get_all_droplets(self) -> List[Dict[str, Any]]:
        """Fetch list of all registered droplets"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/droplets")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            log.error(f"Failed to fetch droplets: {str(e)}")
            return []
    
    async def get_droplet_by_id(self, droplet_id: int) -> Dict[str, Any]:
        """Get specific droplet info"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/droplet/{droplet_id}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            log.error(f"Failed to fetch droplet {droplet_id}: {str(e)}")
            raise