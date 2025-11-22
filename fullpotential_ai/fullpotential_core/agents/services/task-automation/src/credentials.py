"""
Task Automation Framework - Credentials Integration
Integrates with the central credential vault service
"""

import os
import requests
from typing import Optional, Dict


class CredentialVault:
    """Client for the credential vault service"""

    def __init__(self, vault_url: Optional[str] = None):
        self.vault_url = vault_url or os.environ.get(
            "CREDENTIAL_VAULT_URL",
            "http://198.54.123.234:8025"
        )

    def store_credential(
        self,
        service: str,
        credential_type: str,
        value: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store a credential in the vault

        Args:
            service: Service name (e.g., "sendgrid")
            credential_type: Type of credential (e.g., "api_key", "password")
            value: The credential value
            metadata: Optional metadata dict

        Returns:
            True if successful
        """
        try:
            response = requests.post(
                f"{self.vault_url}/credentials",
                json={
                    "service": service,
                    "credential_type": credential_type,
                    "value": value,
                    "metadata": metadata or {}
                },
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to store credential: {e}")
            return False

    def get_credential(
        self,
        service: str,
        credential_type: str
    ) -> Optional[str]:
        """
        Retrieve a credential from the vault

        Args:
            service: Service name
            credential_type: Type of credential

        Returns:
            The credential value or None if not found
        """
        try:
            response = requests.get(
                f"{self.vault_url}/credentials/{service}/{credential_type}",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("value")
            return None
        except Exception as e:
            print(f"Failed to retrieve credential: {e}")
            return None

    def list_credentials(self, service: Optional[str] = None) -> list:
        """
        List all credentials, optionally filtered by service

        Args:
            service: Optional service name filter

        Returns:
            List of credential entries
        """
        try:
            url = f"{self.vault_url}/credentials"
            if service:
                url += f"?service={service}"

            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Failed to list credentials: {e}")
            return []

    def delete_credential(
        self,
        service: str,
        credential_type: str
    ) -> bool:
        """
        Delete a credential from the vault

        Args:
            service: Service name
            credential_type: Type of credential

        Returns:
            True if successful
        """
        try:
            response = requests.delete(
                f"{self.vault_url}/credentials/{service}/{credential_type}",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to delete credential: {e}")
            return False

    def health_check(self) -> bool:
        """Check if vault service is available"""
        try:
            response = requests.get(
                f"{self.vault_url}/health",
                timeout=2
            )
            return response.status_code == 200
        except Exception:
            return False
