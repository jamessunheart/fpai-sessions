"""Client for Credentials Manager integration"""

import httpx
from typing import List, Optional, Dict, Any

from .config import settings


class CredentialsClient:
    """Interface to Credentials Manager"""

    def __init__(self):
        """Initialize client"""
        self.base_url = settings.credentials_manager_url
        self.token = settings.credentials_manager_token

    async def grant_access(
        self,
        helper_name: str,
        credential_ids: List[int],
        expires_hours: int = 24
    ) -> Optional[str]:
        """
        Grant helper access to credentials.

        Returns access token or None if failed.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/tokens",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "helper_name": helper_name,
                        "credential_ids": credential_ids,
                        "scope": "read_only",
                        "expires_hours": expires_hours
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("token")
                else:
                    print(f"Failed to grant access: {response.status_code}")
                    return None

        except Exception as e:
            print(f"Credentials Manager error: {e}")
            return None

    async def revoke_access(self, token_id: int) -> bool:
        """Revoke helper access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/tokens/{token_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10.0
                )

                return response.status_code == 200

        except Exception as e:
            print(f"Revoke error: {e}")
            return False

    async def get_credential(self, credential_id: int) -> Optional[Dict[str, Any]]:
        """Get credential details (for validation)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/credentials/{credential_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=5.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return None

        except Exception as e:
            print(f"Get credential error: {e}")
            return None


# Global instance
credentials_client = CredentialsClient()
