import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional
from ..utils.logging import get_logger
from ..config import get_config

log = get_logger(__name__)

class AuthManager:
    def __init__(self):
        self.config = get_config()
        self.registry_url = "https://drop18.fullpotential.ai"
        self.registry_key = "a5447df6e4fe34df8c4d0c671ad98ce78de9e55cf152e5d07e5bf221769e31dc"
        self.jwt_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.is_registered = False
        self._refresh_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start auth manager with auto-refresh"""
        await self.get_token()
        await self.register_droplet()
        self._refresh_task = asyncio.create_task(self._auto_refresh())
        log.info("Auth manager started with auto-refresh")
        
    async def stop(self):
        """Stop auth manager"""
        if self._refresh_task:
            self._refresh_task.cancel()
            
    async def get_valid_token(self) -> str:
        """Get current valid token, refresh if needed"""
        if not self.jwt_token or self._token_expired():
            await self.get_token()
        return self.jwt_token
        
    def _token_expired(self) -> bool:
        """Check if token is expired or expires soon (5min buffer)"""
        if not self.token_expires_at:
            return True
        return datetime.utcnow() + timedelta(minutes=5) >= self.token_expires_at
        
    async def get_token(self):
        """Get JWT token from Registry"""
        try:
            log.info(f"Requesting JWT token for droplet ID: {self.config.droplet.id}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.registry_url}/auth/token",
                    params={"droplet_id": self.config.droplet.id},
                    headers={"X-Registry-Key": self.registry_key},
                    timeout=10.0
                )
                
            log.info(f"Token request response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                log.info(f"Token response data: {data}")
                
                # Handle token response format
                if "token" in data:
                    self.jwt_token = data["token"]
                    # Default to 24 hours since expires_in is not provided
                    expires_in = 86400  # 24 hours
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    log.info(f"✅ JWT token obtained, expires in {expires_in}s")
                    log.info(f"Token algorithm: {data.get('algorithm', 'unknown')}")
                else:
                    log.error(f"No token in response: {data}")
            else:
                log.error(f"Failed to get token: {response.status_code} - {response.text}")
                
        except Exception as e:
            log.error(f"Token request failed: {e}")
            
    async def register_droplet(self):
        """Register droplet with Registry"""
        try:
            token = await self.get_valid_token()
            if not token:
                log.error("No valid token available for registration")
                return
                
            registration_data = {
                "id": self.config.droplet.registry_id,
                "droplet_id": self.config.droplet.registry_id,
                "host": self.config.droplet.url,
                "name": self.config.droplet.name,
                "role": "airtable-connector",
                "env": "prod",
                "version": self.config.droplet.version,
                "steward": self.config.droplet.steward,
                "endpoint": f"https://{self.config.droplet.url}" if not self.config.droplet.url.startswith('http') else self.config.droplet.url,
                "capabilities": [
                    "airtable-integration",
                    "sprint-management",
                    "proof-submissions",
                    "cell-tracking",
                    "udc-v1.0",
                    "jwt-authentication"
                ],
                "status": "active",
                "metadata": {
                    "version": self.config.droplet.version,
                    "name": self.config.droplet.name,
                    "steward": self.config.droplet.steward,
                    "udc_version": self.config.droplet.udc_version
                }
            }
            
            log.info(f"Registering droplet with data: {registration_data}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.registry_url}/registry/register",
                    json=registration_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Registry-Key": self.registry_key
                    },
                    timeout=10.0
                )
                
            log.info(f"Registration response: {response.status_code}")
            
            if response.status_code == 200:
                self.is_registered = True
                response_data = response.json()
                log.info(f"✅ Droplet registered successfully: {response_data}")
            else:
                log.error(f"❌ Registration failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            log.error(f"Registration failed: {e}")
            
    async def send_heartbeat(self):
        """Send heartbeat to Registry"""
        try:
            token = await self.get_valid_token()
            if not token:
                log.warning("No valid token for heartbeat")
                return
                
            import psutil
            heartbeat_data = {
                "id": self.config.droplet.registry_id,
                "droplet_id": self.config.droplet.registry_id,
                "status": "active",
                "metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_mb": psutil.virtual_memory().used // 1024 // 1024
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.registry_url}/registry/heartbeat",
                    json=heartbeat_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Registry-Key": self.registry_key
                    },
                    timeout=5.0
                )
                
            if response.status_code == 200:
                log.info("💓 Heartbeat sent successfully")
            else:
                log.warning(f"❌ Heartbeat failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            log.warning(f"Heartbeat failed: {e}")
            
    async def _auto_refresh(self):
        """Background task for token refresh and heartbeats"""
        heartbeat_counter = 0
        
        while True:
            try:
                # Check token every 30 seconds
                if self._token_expired():
                    log.info("Token expired, refreshing...")
                    await self.get_token()
                    
                # Send heartbeat every 60 seconds (every 2nd cycle)
                heartbeat_counter += 1
                if heartbeat_counter >= 2:
                    await self.send_heartbeat()
                    heartbeat_counter = 0
                
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                log.info("Auto-refresh task cancelled")
                break
            except Exception as e:
                log.error(f"Auto-refresh error: {e}")
                await asyncio.sleep(30)

# Global instance
auth_manager = AuthManager()