"""Tests for Registry client caching and retry logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import httpx
import json
from datetime import datetime, timedelta
import asyncio

from app.registry_client import RegistryClient, call_droplet_with_retry
from app.models import Droplet


class TestRegistryCache:
    """Tests for Registry caching mechanism."""

    @pytest.fixture
    def registry_client(self, tmp_path):
        """Create RegistryClient with temp cache dir."""
        client = RegistryClient(base_url="http://localhost:8000", cache_dir=tmp_path)
        return client

    def test_cache_starts_empty(self, registry_client):
        """Cache starts with no droplets."""
        assert registry_client.droplets_cache is None
        assert registry_client.cache_timestamp is None

    def test_get_cache_age_returns_large_when_no_cache(self, registry_client):
        """Cache age returns large value when no cache."""
        age = registry_client._get_cache_age()
        assert age > 100000

    def test_get_cache_status_unavailable_when_no_cache(self, registry_client):
        """Cache status is unavailable when no cache."""
        status = registry_client._get_cache_status()
        assert status == "unavailable"

    def test_cache_status_active_when_fresh(self, registry_client, mock_droplets):
        """Cache status is active when fresh."""
        registry_client.droplets_cache = mock_droplets
        registry_client.cache_timestamp = datetime.utcnow()

        status = registry_client._get_cache_status()
        assert status == "active"

    def test_cache_status_stale_when_expired(self, registry_client, mock_droplets):
        """Cache status is stale when expired."""
        registry_client.droplets_cache = mock_droplets
        registry_client.cache_timestamp = datetime.utcnow() - timedelta(minutes=10)

        status = registry_client._get_cache_status()
        assert status == "stale"

    @patch("builtins.open", new_callable=mock_open)
    def test_save_cache_to_disk_writes_json(self, mock_file, registry_client, mock_droplets):
        """Save cache writes droplets to disk as JSON."""
        registry_client._save_cache_to_disk(mock_droplets)

        mock_file.assert_called_once()
        handle = mock_file()
        written_data = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed = json.loads(written_data)
        assert len(parsed) == len(mock_droplets)

    def test_load_cache_from_disk_returns_none_if_missing(self, registry_client):
        """Load cache returns None if file doesn't exist."""
        result = registry_client._load_cache_from_disk()
        assert result is None

    def test_find_droplet_returns_none_when_no_cache(self, registry_client):
        """Find droplet returns None when no cache."""
        result = registry_client.find_droplet("registry")
        assert result is None

    def test_find_droplet_finds_by_name(self, registry_client, mock_droplets):
        """Find droplet finds droplet by name."""
        registry_client.droplets_cache = mock_droplets

        result = registry_client.find_droplet("registry")
        assert result is not None
        assert result.name == "registry"

    def test_find_droplet_case_insensitive(self, registry_client, mock_droplets):
        """Find droplet is case insensitive."""
        registry_client.droplets_cache = mock_droplets

        result = registry_client.find_droplet("REGISTRY")
        assert result is not None
        assert result.name == "registry"


class TestRegistrySync:
    """Tests for Registry synchronization."""

    @pytest.fixture
    def registry_client(self, tmp_path):
        """Create RegistryClient with temp cache dir."""
        client = RegistryClient(base_url="http://localhost:8000", cache_dir=tmp_path)
        return client

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    async def test_sync_droplets_success(
        self, mock_client_class, registry_client, mock_registry_response
    ):
        """Sync droplets succeeds when Registry available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_registry_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await registry_client.sync_droplets()

        assert result is not None
        assert len(result) == 3
        assert registry_client.droplets_cache is not None
        assert registry_client.cache_timestamp is not None
        assert registry_client.last_sync_error is None

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    async def test_sync_droplets_handles_timeout(self, mock_client_class, registry_client):
        """Sync droplets handles timeout gracefully."""
        # Create mock that raises timeout when get() is called
        async def mock_get_with_timeout(*args, **kwargs):
            raise httpx.TimeoutException("Timeout")

        mock_client = MagicMock()
        mock_client.get = mock_get_with_timeout
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.aclose = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        result = await registry_client.sync_droplets()

        assert result is None
        assert registry_client.last_sync_error is not None
        assert "Timeout" in registry_client.last_sync_error

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    async def test_sync_droplets_handles_connection_error(
        self, mock_client_class, registry_client
    ):
        """Sync droplets handles connection error gracefully."""
        async def mock_get_with_connection_error(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        mock_client = MagicMock()
        mock_client.get = mock_get_with_connection_error
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.aclose = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        result = await registry_client.sync_droplets()

        assert result is None
        assert registry_client.last_sync_error is not None
        assert "Connection" in registry_client.last_sync_error

    @pytest.mark.asyncio
    async def test_get_droplets_returns_cache_when_fresh(
        self, registry_client, mock_droplets
    ):
        """Get droplets returns cache when fresh."""
        registry_client.droplets_cache = mock_droplets
        registry_client.cache_timestamp = datetime.utcnow()

        droplets, status, served_from = await registry_client.get_droplets()

        assert len(droplets) == 3
        assert status == "active"
        assert served_from == "cache"

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    async def test_get_droplets_syncs_when_cache_expired(
        self, mock_client_class, registry_client, mock_registry_response, mock_droplets
    ):
        """Get droplets syncs from Registry when cache expired."""
        # Set expired cache
        registry_client.droplets_cache = mock_droplets
        registry_client.cache_timestamp = datetime.utcnow() - timedelta(minutes=10)

        # Mock successful sync
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_registry_response
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client_class.return_value = mock_client

        droplets, status, served_from = await registry_client.get_droplets()

        assert len(droplets) == 3
        assert status == "active"
        assert served_from == "registry"


class TestRetryLogic:
    """Tests for droplet call retry mechanism."""

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    async def test_call_droplet_success_first_try(self, mock_client_class):
        """Call droplet succeeds on first attempt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        status, body, retries, error = await call_droplet_with_retry(
            "http://test.com/endpoint", "GET"
        )

        assert status == 200
        assert body == {"status": "ok"}
        assert retries == 0
        assert error is None

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    @patch("app.registry_client.asyncio.sleep", new_callable=AsyncMock)
    async def test_call_droplet_retries_on_500(self, mock_sleep, mock_client_class):
        """Call droplet retries on 5xx error with exponential backoff."""
        # Returns 500 error on all attempts
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        status, body, retries, error = await call_droplet_with_retry(
            "http://test.com/endpoint", "GET", max_retries=3, backoff_base=1.0
        )

        # Should retry 3 times and fail
        assert status == 0
        assert retries == 3
        assert error is not None
        assert "500" in error
        # Verify exponential backoff: 1s, 2s
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    async def test_call_droplet_no_retry_on_400(self, mock_client_class):
        """Call droplet does not retry on 4xx error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}

        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        status, body, retries, error = await call_droplet_with_retry(
            "http://test.com/endpoint", "GET", max_retries=3
        )

        assert status == 400
        assert retries == 0
        assert error is None

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    @patch("app.registry_client.asyncio.sleep", new_callable=AsyncMock)
    async def test_call_droplet_handles_timeout(self, mock_sleep, mock_client_class):
        """Call droplet handles timeout with retry."""
        async def mock_request_with_timeout(*args, **kwargs):
            raise httpx.TimeoutException("Timeout")

        mock_client = MagicMock()
        mock_client.request = mock_request_with_timeout
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.aclose = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        status, body, retries, error = await call_droplet_with_retry(
            "http://test.com/endpoint", "GET", max_retries=3
        )

        assert status == 0
        assert body is None
        assert retries == 3
        assert error is not None
        assert "Timeout" in error

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    @patch("app.registry_client.asyncio.sleep", new_callable=AsyncMock)
    async def test_call_droplet_exponential_backoff(self, mock_sleep, mock_client_class):
        """Call droplet uses exponential backoff between retries."""
        async def mock_request_with_timeout(*args, **kwargs):
            raise httpx.TimeoutException("Timeout")

        mock_client = MagicMock()
        mock_client.request = mock_request_with_timeout
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.aclose = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        await call_droplet_with_retry(
            "http://test.com/endpoint", "GET", max_retries=3, backoff_base=1.0
        )

        # Verify sleep was called with exponential backoff delays
        # Attempt 0 fails, sleep(1); Attempt 1 fails, sleep(2); Attempt 2 fails, no sleep
        assert mock_sleep.call_count == 2
        calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert calls == [1.0, 2.0]

    @pytest.mark.asyncio
    @patch("app.registry_client.httpx.AsyncClient")
    @patch("app.registry_client.asyncio.sleep", new_callable=AsyncMock)
    async def test_call_droplet_handles_connection_error(self, mock_sleep, mock_client_class):
        """Call droplet handles connection error with retry."""
        async def mock_request_with_connection_error(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        mock_client = MagicMock()
        mock_client.request = mock_request_with_connection_error
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.aclose = AsyncMock(return_value=None)
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client

        status, body, retries, error = await call_droplet_with_retry(
            "http://test.com/endpoint", "GET", max_retries=3
        )

        assert status == 0
        assert body is None
        assert retries == 3
        assert error is not None
        assert "Connection" in error
