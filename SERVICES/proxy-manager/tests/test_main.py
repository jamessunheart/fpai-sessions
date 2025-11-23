from fastapi.testclient import TestClient
from app.main import app
import pytest
from unittest.mock import patch

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_proxy_mock():
    # We mock the NginxManager methods to avoid actual file writes during unit tests
    with patch("app.main.nginx_manager.create_config", return_value=True) as mock_create:
        with patch("app.main.nginx_manager.test_and_reload", return_value=True) as mock_reload:
            payload = {
                "droplet_name": "test-droplet",
                "domain": "test.example.com",
                "upstream_host": "localhost",
                "upstream_port": 9000
            }
            response = client.put("/proxies/test-droplet", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["droplet_name"] == "test-droplet"
            assert data["domain"] == "test.example.com"

