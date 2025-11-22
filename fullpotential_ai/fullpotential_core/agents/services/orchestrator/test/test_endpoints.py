"""Tests for Orchestrator API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import json


class TestHealthEndpoint:
    """Tests for /orchestrator/health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint returns 200 OK."""
        response = client.get("/orchestrator/health")
        assert response.status_code == 200

    def test_health_returns_correct_format(self, client):
        """Health endpoint returns expected JSON format."""
        response = client.get("/orchestrator/health")
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert data["status"] in ["active", "inactive", "error"]  # UDC compliant status values
        assert data["service"] == "orchestrator"
        assert "dependencies" in data  # Enhanced health check


class TestInfoEndpoint:
    """Tests for /orchestrator/info endpoint."""

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.registry_client._get_cache_age")
    def test_info_returns_orchestrator_metadata(self, mock_cache_age, mock_get_droplets, client, mock_droplets):
        """Info endpoint returns Orchestrator metadata."""
        from datetime import datetime
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        mock_cache_age.return_value = 0
        # Set cache_timestamp on the actual instance
        from app.main import registry_client
        registry_client.cache_timestamp = datetime.utcnow()

        response = client.get("/orchestrator/info")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 2
        assert data["name"] == "orchestrator"
        assert data["version"] == "1.1.0"
        assert "registry_url" in data
        assert "cache_status" in data


class TestDropletsEndpoint:
    """Tests for /orchestrator/droplets endpoint."""

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    def test_droplets_returns_list(self, mock_get_droplets, client, mock_droplets):
        """Droplets endpoint returns list of droplets."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")

        response = client.get("/orchestrator/droplets")
        assert response.status_code == 200
        data = response.json()

        assert "droplets" in data
        assert len(data["droplets"]) == 3
        assert data["cache_status"] == "active"
        assert data["served_from"] == "registry"

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    def test_droplets_returns_503_when_unavailable(self, mock_get_droplets, client):
        """Droplets endpoint returns 503 when no droplets available."""
        mock_get_droplets.return_value = ([], "unavailable", "none")

        response = client.get("/orchestrator/droplets")
        assert response.status_code == 503

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    def test_droplets_uses_cache_when_registry_down(self, mock_get_droplets, client, mock_droplets):
        """Droplets endpoint uses cache when Registry unavailable."""
        mock_get_droplets.return_value = (mock_droplets, "stale", "cache")

        response = client.get("/orchestrator/droplets")
        assert response.status_code == 200
        data = response.json()

        assert len(data["droplets"]) == 3
        assert data["cache_status"] == "stale"
        assert data["served_from"] == "cache"

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.metrics.update_droplet_status")
    def test_droplets_updates_metrics(self, mock_update_metrics, mock_get_droplets, client, mock_droplets):
        """Droplets endpoint updates metrics."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")

        client.get("/orchestrator/droplets")
        mock_update_metrics.assert_called_once()


class TestTaskSubmission:
    """Tests for /orchestrator/tasks POST endpoint."""

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.call_droplet_with_retry", new_callable=AsyncMock)
    def test_submit_task_success(
        self, mock_call, mock_get_droplets, client, mock_droplets, mock_task_request
    ):
        """Task submission succeeds with valid droplet."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        mock_call.return_value = (200, {"status": "ok"}, 0, None)

        response = client.post("/orchestrator/tasks", json=mock_task_request)
        assert response.status_code == 200
        data = response.json()

        assert "task_id" in data
        assert data["status"] == "success"
        assert data["response_status"] == 200
        assert data["retry_count"] == 0

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    def test_submit_task_droplet_not_found(self, mock_get_droplets, client, mock_droplets):
        """Task submission fails when droplet not found."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")

        invalid_request = {
            "droplet_name": "nonexistent",
            "method": "GET",
            "path": "/test",
        }

        response = client.post("/orchestrator/tasks", json=invalid_request)
        assert response.status_code == 400
        data = response.json()

        # Check error response format (FastAPI wraps in 'detail')
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "DROPLET_NOT_FOUND"
        assert "nonexistent" in data["detail"]["error"]["message"]

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.call_droplet_with_retry", new_callable=AsyncMock)
    def test_submit_task_with_retry(
        self, mock_call, mock_get_droplets, client, mock_droplets, mock_task_request
    ):
        """Task submission handles retries correctly."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        # Simulate 2 retries then success
        mock_call.return_value = (200, {"status": "ok"}, 2, None)

        response = client.post("/orchestrator/tasks", json=mock_task_request)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["retry_count"] == 2

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.call_droplet_with_retry", new_callable=AsyncMock)
    def test_submit_task_timeout(
        self, mock_call, mock_get_droplets, client, mock_droplets, mock_task_request
    ):
        """Task submission handles timeout correctly."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        mock_call.return_value = (0, None, 3, "Timeout error")

        response = client.post("/orchestrator/tasks", json=mock_task_request)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "timeout"
        assert data["retry_count"] == 3

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.call_droplet_with_retry", new_callable=AsyncMock)
    def test_submit_task_records_in_store(
        self, mock_call, mock_get_droplets, client, mock_droplets, mock_task_request
    ):
        """Task submission records task in store."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        mock_call.return_value = (200, {"status": "ok"}, 0, None)

        response = client.post("/orchestrator/tasks", json=mock_task_request)
        task_id = response.json()["task_id"]

        # Retrieve task
        get_response = client.get(f"/orchestrator/tasks/{task_id}")
        assert get_response.status_code == 200

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    def test_submit_task_no_droplets_available(self, mock_get_droplets, client, mock_task_request):
        """Task submission fails when no droplets available."""
        mock_get_droplets.return_value = ([], "unavailable", "none")

        response = client.post("/orchestrator/tasks", json=mock_task_request)
        assert response.status_code == 400


class TestTaskListing:
    """Tests for /orchestrator/tasks GET endpoint."""

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.call_droplet_with_retry", new_callable=AsyncMock)
    def test_list_tasks_returns_all(
        self, mock_call, mock_get_droplets, client, mock_droplets, mock_task_request
    ):
        """List tasks returns all submitted tasks."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        mock_call.return_value = (200, {"status": "ok"}, 0, None)

        # Submit 3 tasks
        for _ in range(3):
            client.post("/orchestrator/tasks", json=mock_task_request)

        response = client.get("/orchestrator/tasks")
        assert response.status_code == 200
        data = response.json()

        assert "tasks" in data
        assert len(data["tasks"]) >= 3
        assert data["total"] >= 3

    def test_list_tasks_filters_by_status(self, client):
        """List tasks filters by status parameter."""
        response = client.get("/orchestrator/tasks?status=success")
        assert response.status_code == 200

    def test_list_tasks_filters_by_droplet_name(self, client):
        """List tasks filters by droplet_name parameter."""
        response = client.get("/orchestrator/tasks?droplet_name=registry")
        assert response.status_code == 200

    def test_list_tasks_respects_limit(self, client):
        """List tasks respects limit parameter."""
        response = client.get("/orchestrator/tasks?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) <= 5


class TestTaskRetrieval:
    """Tests for /orchestrator/tasks/{task_id} endpoint."""

    @patch("app.main.registry_client.get_droplets", new_callable=AsyncMock)
    @patch("app.main.call_droplet_with_retry", new_callable=AsyncMock)
    def test_get_task_returns_details(
        self, mock_call, mock_get_droplets, client, mock_droplets, mock_task_request
    ):
        """Get task returns full task details."""
        mock_get_droplets.return_value = (mock_droplets, "active", "registry")
        mock_call.return_value = (200, {"status": "ok"}, 0, None)

        # Submit task
        submit_response = client.post("/orchestrator/tasks", json=mock_task_request)
        task_id = submit_response.json()["task_id"]

        # Retrieve task
        response = client.get(f"/orchestrator/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == task_id
        assert "droplet_name" in data
        assert "status" in data
        assert "created_at" in data

    def test_get_task_returns_404_for_nonexistent(self, client):
        """Get task returns 404 for nonexistent task."""
        response = client.get("/orchestrator/tasks/nonexistent-id")
        assert response.status_code == 404


class TestMetricsEndpoint:
    """Tests for /orchestrator/metrics endpoint."""

    def test_metrics_returns_operational_data(self, client):
        """Metrics endpoint returns operational metrics."""
        response = client.get("/orchestrator/metrics")
        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "tasks" in data
        assert "retry" in data
        assert "registry" in data
        assert "droplets_known" in data
