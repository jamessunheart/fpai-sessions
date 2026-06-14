from fastapi.testclient import TestClient
from app.main import app
import pytest
from unittest.mock import patch

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    # The API returns "active" not "healthy" as per UDC compliance in app/main.py
    assert response.json()["status"] == "active"

def test_create_proxy_mock():
    # We mock the NginxManager methods to avoid actual file writes during unit tests
    # Correct method name is write_config, not create_config
    with patch("app.main.nginx_manager.write_config", return_value=(True, None)) as mock_create:
        # Correct methods are test_config and reload
        with patch("app.main.nginx_manager.test_config", return_value=(True, "ok")) as mock_test:
            with patch("app.main.nginx_manager.reload", return_value=(True, "ok")) as mock_reload:
                payload = {
                    "domain": "test.example.com",
                    "upstream_host": "localhost",
                    "upstream_port": 9000,
                    "require_healthy": False,
                    "enable_ssl": False
                }
                response = client.put("/proxies/test-droplet", json=payload)
                assert response.status_code == 200
                data = response.json()
                assert data["droplet_name"] == "test-droplet"
                assert data["domain"] == "test.example.com"

