import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import httpx

from .config import settings
from .models import Droplet
from .metrics import metrics

log = logging.getLogger(__name__)


class RegistryClient:
    """
    Client for talking to the Registry droplet and caching droplet metadata.
    """

    def __init__(self, base_url: str, timeout: float = 5.0, cache_dir: Optional[Path] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self._droplets: Dict[str, Droplet] = {}
        self.last_sync_time: Optional[datetime] = None
        self.last_sync_error: Optional[str] = None

        # Cache file support
        if cache_dir is None:
            cache_dir = Path(settings.registry_cache_dir)
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / "orchestrator_droplets.json"

        # Persistent HTTP client with connection pooling
        # limits: max 100 connections total, max 20 per host
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._client_limits = limits

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self._client_limits,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client and release connections."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            log.debug("HTTP client closed")

    @property
    def droplets(self) -> List[Droplet]:
        return list(self._droplets.values())

    @property
    def droplets_cache(self) -> Optional[List[Droplet]]:
        """Compatibility property for tests."""
        return list(self._droplets.values()) if self._droplets else None

    @droplets_cache.setter
    def droplets_cache(self, value: Optional[List[Droplet]]) -> None:
        """Compatibility setter for tests."""
        if value is None:
            self._droplets = {}
        else:
            self._droplets = {d.name: d for d in value}

    @property
    def cache_timestamp(self) -> Optional[datetime]:
        """Compatibility property for tests."""
        return self.last_sync_time

    @cache_timestamp.setter
    def cache_timestamp(self, value: Optional[datetime]) -> None:
        """Compatibility setter for tests."""
        self.last_sync_time = value

    def get_droplet_by_name(self, name: str) -> Optional[Droplet]:
        return self._droplets.get(name)

    def find_droplet(self, name: str) -> Optional[Droplet]:
        """Find droplet by name (case-insensitive). Compatibility method for tests."""
        name_lower = name.lower()
        for droplet_name, droplet in self._droplets.items():
            if droplet_name.lower() == name_lower:
                return droplet
        return None

    async def sync_droplets(self) -> Optional[List[Droplet]]:
        """
        Fetch droplet list from Registry and refresh cache.

        On success:
          - updates self._droplets
          - clears self.last_sync_error
          - sets last_sync_time

        On timeout / connection error:
          - keeps existing cache
          - sets last_sync_error to a non-empty string
          - returns None
        """
        import time

        url = f"{self.base_url}/droplets"
        log.info(f"Syncing droplets from Registry at {url}")

        sync_start = time.time()

        try:
            client = await self._get_client()
            resp = await client.get(url)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            sync_duration_ms = (time.time() - sync_start) * 1000
            self.last_sync_error = f"{type(e).__name__}: {e}"
            log.warning(f"Registry sync failed: {self.last_sync_error}")

            # Record failed sync
            metrics.record_registry_sync(
                success=False,
                duration_ms=sync_duration_ms,
                cache_age_seconds=int(self._get_cache_age()),
                cache_status=self._get_cache_status(),
            )
            return None
        except Exception as e:
            sync_duration_ms = (time.time() - sync_start) * 1000
            self.last_sync_error = f"UnexpectedError: {e}"
            log.error(f"Registry sync unexpected error: {self.last_sync_error}")

            # Record failed sync
            metrics.record_registry_sync(
                success=False,
                duration_ms=sync_duration_ms,
                cache_age_seconds=int(self._get_cache_age()),
                cache_status=self._get_cache_status(),
            )
            return None

        if resp.status_code != 200:
            sync_duration_ms = (time.time() - sync_start) * 1000
            self.last_sync_error = f"HTTP {resp.status_code}"
            log.warning(
                f"Registry sync returned non-200 status: {self.last_sync_error}"
            )

            # Record failed sync
            metrics.record_registry_sync(
                success=False,
                duration_ms=sync_duration_ms,
                cache_age_seconds=int(self._get_cache_age()),
                cache_status=self._get_cache_status(),
            )
            return None

        data = resp.json()
        droplet_items = data.get("droplets", data)

        new_cache: Dict[str, Droplet] = {}
        for item in droplet_items:
            try:
                droplet = Droplet(**item)
                new_cache[droplet.name] = droplet
            except Exception as e:
                log.warning(f"Skipping invalid droplet entry {item!r}: {e}")

        self._droplets = new_cache
        self.last_sync_time = datetime.utcnow()
        self.last_sync_error = None

        sync_duration_ms = (time.time() - sync_start) * 1000

        log.info(
            f"Registry sync complete: {len(self._droplets)} droplets cached "
            f"at {self.last_sync_time.isoformat()}Z"
        )

        # Save cache to disk
        self._save_cache_to_disk(self.droplets)

        # Record successful sync
        metrics.record_registry_sync(
            success=True,
            duration_ms=sync_duration_ms,
            cache_age_seconds=int(self._get_cache_age()),
            cache_status=self._get_cache_status(),
        )

        return self.droplets

    def _get_cache_age(self) -> float:
        """Get age of cache in seconds."""
        if self.last_sync_time is None:
            return 999999.0
        return (datetime.utcnow() - self.last_sync_time).total_seconds()

    def _get_cache_status(self) -> str:
        """Get cache status: 'unavailable', 'active', or 'stale'."""
        if not self._droplets or self.last_sync_time is None:
            return "unavailable"

        age = self._get_cache_age()
        cache_ttl = settings.registry_cache_expiry

        if age > cache_ttl:
            return "stale"
        return "active"

    def _save_cache_to_disk(self, droplets: List[Droplet]) -> None:
        """Save droplet cache to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            cache_data = [d.model_dump() for d in droplets]

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

            log.debug(f"Saved {len(droplets)} droplets to cache file")
        except Exception as e:
            log.warning(f"Failed to save cache to disk: {e}")

    def _load_cache_from_disk(self) -> Optional[List[Droplet]]:
        """Load droplet cache from disk."""
        try:
            if not self.cache_file.exists():
                log.debug("No cache file found")
                return None

            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            droplets = [Droplet(**d) for d in cache_data]
            self._droplets = {d.name: d for d in droplets}

            log.info(f"Loaded {len(droplets)} droplets from cache file")
            return droplets
        except Exception as e:
            log.warning(f"Failed to load cache from disk: {e}")
            return None

    async def get_droplets(self) -> Tuple[List[Droplet], str, str]:
        """Get droplets with cache status.

        Returns:
            Tuple of (droplets, cache_status, served_from)
            - cache_status: 'unavailable', 'active', or 'stale'
            - served_from: 'registry', 'cache', or 'none'
        """
        cache_status = self._get_cache_status()

        # If cache is fresh, return it
        if cache_status == "active":
            return self.droplets, cache_status, "cache"

        # Try to sync from registry
        sync_result = await self.sync_droplets()

        if sync_result is not None:
            # Successful sync
            return self.droplets, "active", "registry"

        # Sync failed, return stale cache if available
        if self._droplets:
            return self.droplets, "stale", "cache"

        # No cache available
        return [], "unavailable", "none"

    async def send_message(
        self,
        target: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: str = "normal",
        retry_count: int = 3
    ) -> Tuple[bool, str, Optional[str]]:
        """Send a message to another droplet via Registry's /send endpoint.

        Args:
            target: Name of the target droplet
            message_type: Type of message (status, event, command, query)
            payload: Message payload
            priority: Message priority (high, normal, low)
            retry_count: Number of retries

        Returns:
            Tuple of (success, result, trace_id)
        """
        url = f"{self.base_url}/send"

        send_payload = {
            "target": target,
            "message_type": message_type,
            "payload": payload,
            "priority": priority,
            "retry_count": retry_count
        }

        try:
            client = await self._get_client()
            resp = await client.post(url, json=send_payload, timeout=10.0)

            if resp.status_code == 200:
                data = resp.json()
                return data.get("sent", False), data.get("result", "unknown"), data.get("trace_id")
            else:
                log.warning(f"Registry /send returned {resp.status_code}")
                return False, "error", None

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            log.error(f"Failed to send message via Registry: {e}")
            return False, "error", None
        except Exception as e:
            log.error(f"Unexpected error sending message: {e}")
            return False, "error", None


async def call_droplet_with_retry(
    url: str,
    method: str,
    *,
    json: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    client: Optional[httpx.AsyncClient] = None,
) -> Tuple[int, Optional[Any], int, Optional[str]]:
    """
    Call a droplet endpoint with retry + exponential backoff.

    Args:
        url: Target URL
        method: HTTP method
        json: JSON payload (deprecated, use payload instead)
        payload: JSON payload
        params: Query parameters
        headers: HTTP headers
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        backoff_base: Base delay for exponential backoff

    Returns:
      (status_code, body, retries, error)
      - retries: number of retry attempts (0 if success on first try)

    On total failure:
      - status_code = 0
      - body = None
      - retries = max_retries
      - error = non-empty string
    """
    if timeout is None:
        timeout = getattr(settings, "request_timeout", 5.0)

    # Support both 'json' and 'payload' parameters for compatibility
    if payload is not None:
        json = payload

    retries = 0
    error: Optional[str] = None

    # Use provided client or create temporary one
    use_provided_client = client is not None
    if not use_provided_client:
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)
        client = httpx.AsyncClient(timeout=timeout, limits=limits)

    try:
        # We intentionally sleep after each failed attempt, including the last,
        # so with max_retries=3 and base=1, total sleep ~= 1 + 2 + 4 = 7s
        for attempt in range(max_retries):
            try:
                resp = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )

                # Check if we should retry based on status code
                # Retry on 5xx server errors, don't retry on 2xx/3xx/4xx
                if resp.status_code < 500:
                    # Success or client error - don't retry
                    retries = attempt
                    body: Optional[Any]
                    try:
                        body = resp.json()
                    except ValueError:
                        body = resp.text or None

                    return resp.status_code, body, retries, None

                # 5xx error - treat like a retriable error
                retries = attempt + 1
                error = f"HTTP {resp.status_code}: Server error"

                # If this was the last allowed attempt, break and return failure
                if attempt == max_retries - 1:
                    break

                # Exponential backoff before retry
                delay = backoff_base * (2 ** attempt)
                await asyncio.sleep(delay)

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                retries = attempt + 1
                error = f"{type(e).__name__}: {e}"

                # If this was the last allowed attempt, break and return failure
                if attempt == max_retries - 1:
                    break

                # Exponential backoff: 1s, 2s, 4s for attempts 1,2,3
                delay = backoff_base * (2 ** attempt)
                await asyncio.sleep(delay)

            except Exception as e:
                # Any other unexpected error: fail immediately
                retries = attempt + 1
                error = f"UnexpectedError: {e}"
                break

        # Total failure
        return 0, None, retries, error
    finally:
        # Close client if we created it
        if not use_provided_client:
            await client.aclose()


# Global client instance used by the orchestrator
registry_client = RegistryClient(
    base_url=settings.registry_url,
    timeout=getattr(settings, "registry_timeout", 5.0),
)
