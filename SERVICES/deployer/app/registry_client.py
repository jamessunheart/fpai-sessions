"""Registry API client for service registration"""

import httpx
from typing import Optional, Dict, Any
from datetime import datetime

from .config import settings


class RegistryClient:
    """Client for interacting with Registry API"""

    async def register_service(
        self,
        service_name: str,
        service_port: int,
        droplet_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Register service with Registry.

        Returns registration response or None if failed.
        """
        endpoint = f"http://{settings.server_host}:{service_port}"

        payload = {
            "name": service_name,
            "endpoint": endpoint,
            "steward": "deployer-automation",
            "metadata": {
                "deployment_method": settings.deployment_method,
                "registered_at": datetime.now().isoformat(),
                "port": service_port,
                "server": settings.server_host,
                "deployed_by": "deployer-service"
            }
        }

        # Add droplet ID if provided
        if droplet_id:
            payload["id"] = droplet_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.registry_url}/droplets",
                    json=payload,
                    timeout=10.0
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    print(f"✅ Service registered with Registry")
                    print(f"   Droplet ID: {data.get('droplet', {}).get('id')}")
                    print(f"   Name: {service_name}")
                    print(f"   Endpoint: {endpoint}")
                    return data

                elif response.status_code == 409:
                    # Service already exists, try to update
                    print(f"⚠️  Service already registered, updating...")
                    return await self.update_service(service_name, service_port)

                else:
                    print(f"❌ Registration failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return None

        except Exception as e:
            print(f"❌ Registry registration error: {e}")
            return None

    async def update_service(
        self,
        service_name: str,
        service_port: int
    ) -> Optional[Dict[str, Any]]:
        """Update existing service registration"""
        endpoint = f"http://{settings.server_host}:{service_port}"

        try:
            # First, get the droplet by name to find its ID
            async with httpx.AsyncClient() as client:
                get_response = await client.get(
                    f"{settings.registry_url}/droplets/name/{service_name}",
                    timeout=5.0
                )

                if get_response.status_code != 200:
                    print(f"❌ Could not find service: {service_name}")
                    return None

                droplet_data = get_response.json()
                droplet_id = droplet_data.get("droplet", {}).get("id")

                if not droplet_id:
                    print(f"❌ No droplet ID found for {service_name}")
                    return None

                # Update the droplet
                update_payload = {
                    "endpoint": endpoint,
                    "status": "active",
                    "metadata": {
                        "deployment_method": settings.deployment_method,
                        "updated_at": datetime.now().isoformat(),
                        "port": service_port,
                        "server": settings.server_host,
                        "deployed_by": "deployer-service"
                    }
                }

                update_response = await client.patch(
                    f"{settings.registry_url}/droplets/{droplet_id}",
                    json=update_payload,
                    timeout=10.0
                )

                if update_response.status_code == 200:
                    print(f"✅ Service updated in Registry")
                    return update_response.json()
                else:
                    print(f"❌ Update failed: {update_response.status_code}")
                    return None

        except Exception as e:
            print(f"❌ Registry update error: {e}")
            return None

    async def check_service_health(self, service_port: int) -> bool:
        """Check if deployed service is healthy"""
        health_url = f"http://{settings.server_host}:{service_port}/health"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(health_url, timeout=5.0)
                return response.status_code == 200

        except:
            return False

    async def verify_registration(self, service_name: str) -> bool:
        """Verify service is registered in Registry"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.registry_url}/droplets/name/{service_name}",
                    timeout=5.0
                )
                return response.status_code == 200

        except:
            return False
