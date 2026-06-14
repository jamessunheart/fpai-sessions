"""Registry client for optional integration."""
import logging
from typing import Optional, List
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class RegistryClient:
    """Client for communicating with the Registry droplet."""

    def __init__(self):
        self.registry_url = settings.registry_url
        self.timeout = settings.health_check_timeout_ms / 1000  # Convert to seconds

    def is_configured(self) -> bool:
        """Check if Registry URL is configured."""
        return self.registry_url is not None and self.registry_url != ""

    async def get_droplets(self) -> Optional[List[dict]]:
        """
        Fetch all droplets from the Registry.

        Returns:
            List of droplet dictionaries or None on error
        """
        if not self.is_configured():
            logger.warning("Registry URL not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.registry_url}/droplets")

                if response.status_code == 200:
                    droplets = response.json()
                    logger.info(f"Fetched {len(droplets)} droplets from Registry")
                    return droplets
                else:
                    logger.error(
                        f"Failed to fetch droplets: {response.status_code} - {response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("Registry request timed out")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch droplets from Registry: {str(e)}")
            return None

    async def check_health(self) -> bool:
        """
        Check if Registry is healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self.is_configured():
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.registry_url}/health")
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Registry health check failed: {str(e)}")
            return False
