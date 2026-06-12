"""
Registry Client Service
Integration with Registry droplet (#3) for authentication and droplet discovery
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import httpx
import structlog

from app.config import settings

log = structlog.get_logger()


# ============================================================================
# REGISTRY CLIENT
# ============================================================================

class RegistryClient:
    """Client for Registry droplet integration"""
    
    def __init__(self):
        self.registry_url = settings.registry_url
        self.droplets_cache: List[Dict] = []
        self.cache_timestamp: Optional[datetime] = None
        self.cache_ttl = timedelta(seconds=settings.registry_sync_interval)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.registry_timeout,
                follow_redirects=True
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # ========================================================================
    # DROPLET DIRECTORY
    # ========================================================================
    
    async def get_droplets(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get droplet directory from Registry with caching
        
        Args:
            force_refresh: Force refresh from Registry (ignore cache)
        
        Returns:
            List of droplet info dicts
        """
        # Return cache if valid
        if not force_refresh and self._is_cache_valid():
            log.debug("registry_using_cached_directory", cache_age_seconds=self._cache_age())
            return self.droplets_cache
        
        # Fetch from Registry
        try:
            client = await self._get_client()
            response = await client.get(f"{self.registry_url}/droplets")
            response.raise_for_status()
            
            self.droplets_cache = response.json()
            self.cache_timestamp = datetime.utcnow()
            
            log.info(
                "registry_sync_completed",
                droplet_count=len(self.droplets_cache),
                registry_url=self.registry_url
            )
            
            return self.droplets_cache
            
        except httpx.TimeoutException:
            log.warning(
                "registry_timeout",
                using_cache=bool(self.droplets_cache),
                cache_age_seconds=self._cache_age()
            )
            return self.droplets_cache  # Return stale cache
            
        except httpx.HTTPStatusError as e:
            log.error(
                "registry_http_error",
                status_code=e.response.status_code,
                using_cache=bool(self.droplets_cache)
            )
            return self.droplets_cache  # Return stale cache
            
        except Exception as e:
            log.error(
                "registry_sync_failed",
                error=str(e),
                using_cache=bool(self.droplets_cache)
            )
            return self.droplets_cache  # Return stale cache
    
    async def get_droplet_by_id(self, droplet_id: int) -> Optional[Dict]:
        """
        Get specific droplet from Registry
        
        Args:
            droplet_id: Droplet ID to fetch
        
        Returns:
            Droplet info dict or None if not found
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.registry_url}/droplets/{droplet_id}")
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                log.warning("droplet_not_found_in_registry", droplet_id=droplet_id)
                return None
            log.error("registry_http_error", status_code=e.response.status_code)
            return None
            
        except Exception as e:
            log.error("registry_fetch_failed", droplet_id=droplet_id, error=str(e))
            return None
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    async def check_registry_health(self) -> bool:
        """
        Check if Registry is healthy
        
        Returns:
            True if Registry is accessible, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(f"{self.registry_url}/health")
            response.raise_for_status()
            
            health_data = response.json()
            status = health_data.get("status", "unknown")
            
            is_healthy = status == "active"
            
            log.info(
                "registry_health_checked",
                status=status,
                healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            log.error("registry_health_check_failed", error=str(e))
            return False
    
    # ========================================================================
    # REGISTRATION
    # ========================================================================
    
    async def register_self(self) -> bool:
        """
        Register Orchestrator with Registry
        
        Returns:
            True if registration successful
        """
        try:
            client = await self._get_client()
            
            registration_data = {
                "droplet_id": settings.droplet_id,
                "name": settings.droplet_name,
                "steward": settings.droplet_steward,
                "endpoint": settings.droplet_endpoint,
                "capabilities": [
                    "task_routing",
                    "droplet_discovery",
                    "health_monitoring",
                    "workflow_management"
                ]
            }
            from app.utils.udc_helpers import udc_wrap
            registration_data = udc_wrap(
                payload={
                    registration_data
                },
                source=f"droplet-{settings.droplet_id}",
                target="droplet-2",
                message_type="registration"
            )
            response = await client.post(
                f"{self.registry_url}/registry/register",
                json=registration_data
            )
            response.raise_for_status()
            
            log.info(
                "registered_with_registry",
                droplet_id=settings.droplet_id,
                registry_url=self.registry_url
            )
            
            return True
            
        except Exception as e:
            log.error("registry_registration_failed", error=str(e))
            return False
    
    async def send_heartbeat(self) -> bool:
        """
        Send heartbeat to Registry
        
        Returns:
            True if heartbeat acknowledged
        """
        try:
            from app.utils.helpers import get_process_metrics
            
            client = await self._get_client()
            metrics = get_process_metrics()
            from app.utils.udc_helpers import udc_wrap
            heartbeat =  {
                    "status": "active",
                    "metrics": metrics
                }
            heartbeat = udc_wrap(
                payload={
                    heartbeat
                },
                source=f"droplet-{settings.droplet_id}",
                target="droplet-2",
                message_type="registration"
            )
            response = await client.post(
                f"{self.registry_url}/registry/heartbeat",
                json=heartbeat
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            log.warning("registry_heartbeat_failed", error=str(e))
            return False
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def _is_cache_valid(self) -> bool:
        """Check if droplet cache is still valid"""
        if not self.cache_timestamp:
            return False
        
        age = datetime.utcnow() - self.cache_timestamp
        return age < self.cache_ttl
    
    def _cache_age(self) -> Optional[float]:
        """Get cache age in seconds"""
        if not self.cache_timestamp:
            return None
        
        age = datetime.utcnow() - self.cache_timestamp
        return age.total_seconds()
    
    def clear_cache(self) -> None:
        """Clear droplet directory cache"""
        self.droplets_cache = []
        self.cache_timestamp = None
        log.info("registry_cache_cleared")


# ============================================================================
# GLOBAL REGISTRY CLIENT INSTANCE
# ============================================================================

registry_client = RegistryClient()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def sync_droplets_from_registry() -> int:
    """
    Sync droplet directory from Registry to local database
    Called periodically by scheduler
    
    Returns:
        Number of droplets synced
    """
    try:
        # Get droplets from Registry
        registry_droplets = await registry_client.get_droplets(force_refresh=True)
        
        if not registry_droplets:
            log.warning("no_droplets_received_from_registry")
            return 0
        
        from app.database import db
        import json
        
        synced_count = 0
        
        for droplet_data in registry_droplets:
            try:
                # Skip self (Orchestrator)
                if droplet_data.get('id') == settings.droplet_id:
                    continue
                
                # Upsert droplet in local database
                await db.execute(
                    """
                    INSERT INTO droplets 
                    (droplet_id, name, steward, endpoint, capabilities, status, registered_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (droplet_id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        steward = EXCLUDED.steward,
                        endpoint = EXCLUDED.endpoint,
                        capabilities = EXCLUDED.capabilities,
                        updated_at = NOW()
                    """,
                    droplet_data.get('id'),
                    droplet_data.get('name'),
                    droplet_data.get('steward'),
                    droplet_data.get('endpoint'),
                    json.dumps(droplet_data.get('capabilities', [])),
                    droplet_data.get('status', 'active')
                )
                
                synced_count += 1
                
            except Exception as e:
                log.error(
                    "droplet_sync_failed",
                    droplet_id=droplet_data.get('id'),
                    error=str(e)
                )
        
        log.info(
            "registry_sync_completed",
            total_droplets=len(registry_droplets),
            synced_count=synced_count
        )
        
        return synced_count
        
    except Exception as e:
        log.error("registry_sync_failed", error=str(e))
        return 0


async def get_registry_status() -> Dict:
    """
    Get Registry connection status
    
    Returns:
        Status dict with connection info
    """
    is_healthy = await registry_client.check_registry_health()
    
    return {
        "connected": is_healthy,
        "registry_url": settings.registry_url,
        "cache_valid": registry_client._is_cache_valid(),
        "cache_age_seconds": registry_client._cache_age(),
        "cached_droplets": len(registry_client.droplets_cache)
    }