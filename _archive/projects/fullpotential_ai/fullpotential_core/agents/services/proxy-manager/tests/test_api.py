"""Tests for Proxy Manager API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_nginx_manager():
    """Mock NGINX manager."""
    with patch("app.main.nginx_manager") as mock:
        mock.write_config.return_value = (True, None)
        mock.test_config.return_value = (True, "test ok")
        mock.reload.return_value = (True, "reload ok")
        mock.delete_config.return_value = (True, None)
        mock.list_configs.return_value = []
        mock.is_nginx_available.return_value = True
        mock.is_config_dir_writable.return_value = True
        mock.last_reload_status = True
        mock.last_reload_timestamp = None
        yield mock


@pytest.fixture
def mock_ssl_manager():
    """Mock SSL manager."""
    with patch("app.main.ssl_manager") as mock:
        mock.check_certificate_exists.return_value = False
        mock.is_certbot_available.return_value = True
        mock.last_operation_status = "success"
        mock.issue_certificate.return_value = (
            True,
            "Success",
            {"expiry": "2024-12-31", "issuer": "Let's Encrypt"},
        )
        yield mock


@pytest.fixture
def mock_health_check():
    """Mock upstream health check."""
    async def mock_check(host, port):
        return True, "healthy"

    with patch("app.main.check_upstream_health", side_effect=mock_check):
        yield


def test_health_endpoint(client, mock_nginx_manager, mock_ssl_manager):
    """Test health endpoint."""
    response = client.get("/proxy-manager/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["nginx"]["present"] is True
    assert data["ssl"]["certbot_present"] is True


def test_create_proxy_success(
    client, mock_nginx_manager, mock_ssl_manager, mock_health_check
):
    """Test creating a proxy successfully."""
    request_data = {
        "domain": "test.example.com",
        "upstream_host": "localhost",
        "upstream_port": 8001,
        "require_healthy": True,
        "enable_ssl": False,
    }

    response = client.put("/proxies/test-service", json=request_data)

    assert response.status_code == 200
    data = response.json()

    assert data["droplet_name"] == "test-service"
    assert data["domain"] == "test.example.com"
    assert data["upstream"] == "http://localhost:8001"
    assert data["status"] == "active"


def test_create_proxy_unhealthy_upstream(client, mock_nginx_manager, mock_ssl_manager):
    """Test creating a proxy with unhealthy upstream."""
    async def mock_unhealthy_check(host, port):
        return False, "timeout"

    with patch("app.main.check_upstream_health", side_effect=mock_unhealthy_check):
        request_data = {
            "domain": "test.example.com",
            "upstream_host": "localhost",
            "upstream_port": 8001,
            "require_healthy": True,
            "enable_ssl": False,
        }

        response = client.put("/proxies/test-service", json=request_data)

        assert response.status_code == 422
        assert "UPSTREAM_UNHEALTHY" in response.text


def test_create_proxy_nginx_test_fails(
    client, mock_nginx_manager, mock_ssl_manager, mock_health_check
):
    """Test creating a proxy when NGINX test fails."""
    mock_nginx_manager.test_config.return_value = (False, "config error")

    request_data = {
        "domain": "test.example.com",
        "upstream_host": "localhost",
        "upstream_port": 8001,
        "require_healthy": False,
        "enable_ssl": False,
    }

    response = client.put("/proxies/test-service", json=request_data)

    assert response.status_code == 500
    assert "NGINX_TEST_FAILED" in response.text


def test_delete_proxy_success(client, mock_nginx_manager):
    """Test deleting a proxy successfully."""
    # Setup - add proxy to list
    mock_nginx_manager.list_configs.return_value = ["test-service"]

    response = client.delete("/proxies/test-service")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "deleted"
    assert data["droplet_name"] == "test-service"


def test_delete_proxy_not_found(client, mock_nginx_manager):
    """Test deleting a non-existent proxy."""
    mock_nginx_manager.list_configs.return_value = []

    response = client.delete("/proxies/nonexistent")

    assert response.status_code == 404
    assert "PROXY_NOT_FOUND" in response.text


def test_list_proxies(client, mock_nginx_manager):
    """Test listing all proxies."""
    mock_nginx_manager.list_configs.return_value = []

    response = client.get("/proxies")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)


def test_get_proxy_not_found(client, mock_nginx_manager):
    """Test getting a non-existent proxy."""
    mock_nginx_manager.list_configs.return_value = []

    response = client.get("/proxies/nonexistent")

    assert response.status_code == 404


def test_issue_ssl_certificate_success(
    client, mock_nginx_manager, mock_ssl_manager, mock_health_check
):
    """Test issuing SSL certificate successfully."""
    # First create a proxy
    request_data = {
        "domain": "test.example.com",
        "upstream_host": "localhost",
        "upstream_port": 8001,
        "require_healthy": False,
        "enable_ssl": False,
    }

    client.put("/proxies/test-service", json=request_data)

    # Then issue SSL
    ssl_request = {"email": "test@example.com", "force_renew": False}

    response = client.post("/proxies/test-service/ssl", json=ssl_request)

    assert response.status_code == 200
    data = response.json()

    assert data["domain"] == "test.example.com"
    assert data["status"] == "active"


def test_issue_ssl_certificate_proxy_not_found(client, mock_ssl_manager):
    """Test issuing SSL for non-existent proxy."""
    ssl_request = {"email": "test@example.com"}

    response = client.post("/proxies/nonexistent/ssl", json=ssl_request)

    assert response.status_code == 404


def test_sync_from_registry_not_configured(client):
    """Test sync from registry when not configured."""
    with patch("app.main.registry_client") as mock_registry:
        mock_registry.is_configured.return_value = False

        response = client.get("/proxy-manager/sync-from-registry")

        assert response.status_code == 503
        assert "REGISTRY_NOT_CONFIGURED" in response.text
