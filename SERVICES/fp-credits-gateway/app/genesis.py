"""
Genesis Protocol Client
Handles service registration ("Enrollment") and credential retrieval ("Vault").
Supports Swarm Secret recovery.
"""
import os
import json
import httpx
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("genesis-client")

class GenesisClient:
    def __init__(
        self, 
        service_name: str, 
        enrollment_key: str = "enroll-1c77b8ce63c4", 
        swarm_secret: str = "fpai-swarm-genesis-permanent-link-v1",
        genesis_url: str = "http://198.54.123.234:8150",
        vault_url: str = "https://fullpotential.ai/api/vault/retrieve",
        data_dir: str = "./data"
    ):
        self.service_name = service_name
        self.enrollment_key = enrollment_key
        self.swarm_secret = swarm_secret
        self.genesis_url = genesis_url.rstrip("/")
        self.vault_url = vault_url
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.identity_file = self.data_dir / "agent_identity.json"
        
        self.agent_token: Optional[str] = None
        self.agent_id: Optional[str] = None
        self.credentials: Dict[str, str] = {}
        
        # Load existing identity
        self.load_identity()

    def load_identity(self):
        if self.identity_file.exists():
            try:
                with open(self.identity_file, 'r') as f:
                    data = json.load(f)
                    self.agent_token = data.get("agent_token")
                    self.agent_id = data.get("agent_id")
                    self.credentials = data.get("credentials", {})
                logger.info(f"Loaded identity for {self.service_name} (ID: {self.agent_id})")
            except Exception as e:
                logger.error(f"Failed to load identity: {e}")

    def save_identity(self):
        data = {
            "agent_token": self.agent_token,
            "agent_id": self.agent_id,
            "credentials": self.credentials,
            "service_name": self.service_name
        }
        try:
            with open(self.identity_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save identity: {e}")

    async def enroll(self, force_recovery: bool = False) -> bool:
        """Register service with Genesis. Uses Swarm Secret if recovery needed."""
        if self.agent_token and not force_recovery:
            logger.info("Already enrolled.")
            return True
            
        key_to_use = self.swarm_secret if force_recovery else self.enrollment_key
        mode = "Recovery" if force_recovery else "Standard"
        logger.info(f"Enrolling {self.service_name} ({mode} Mode)...")
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.genesis_url}/auth/enroll",
                    json={
                        "agent_name": self.service_name,
                        "key": key_to_use
                    },
                    timeout=10.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    self.agent_token = data.get("personal_key")
                    self.agent_id = data.get("agent_name")
                    self.save_identity()
                    logger.info(f"Enrollment successful! Token received.")
                    return True
                elif response.status_code == 403 and not force_recovery:
                    logger.warning("Enrollment key rejected. Attempting Swarm Secret recovery...")
                    return await self.enroll(force_recovery=True)
                else:
                    logger.error(f"Enrollment failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Enrollment error: {e}")
            return False

    async def retrieve_credentials(self) -> bool:
        """Retrieve API keys from Vault. Handles automatic recovery."""
        if not self.agent_token:
            logger.warning("Cannot retrieve credentials: No agent token. Enroll first.")
            return await self.enroll()
            
        logger.info("Retrieving credentials from Vault...")
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    self.vault_url,
                    headers={"Authorization": f"Bearer {self.agent_token}"},
                    json={"service": self.service_name},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    new_creds = data.get("credentials", {})
                    self.credentials.update(new_creds)
                    self.save_identity()
                    logger.info(f"Retrieved {len(new_creds)} credentials.")
                    return True
                elif response.status_code in (401, 403):
                    logger.warning("Agent token rejected. Initiating Swarm Recovery...")
                    if await self.enroll(force_recovery=True):
                        return await self.retrieve_credentials() # Retry
                    return False
                else:
                    logger.error(f"Vault access failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Vault error: {e}")
            return False

    def get_credential(self, key: str, default: str = None) -> str:
        return self.credentials.get(key, default)
