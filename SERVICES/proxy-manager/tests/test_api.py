import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
import shutil

client = TestClient(app)

# Enable test mode to bypass real NGINX calls
settings.TEST_MODE = True

@pytest.fixture(autouse=True)
def cleanup_mock_dir():
    yield
    # Cleanup after tests
    # shutil.rmtree(settings.NGINX_CONFIG_PATH, ignore_errors=True)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

def test_create_route():
    response = client.post("/api/v1/routes", json={
        "domain": "test.example.com",
        "upstream_url": "http://localhost:9000"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "test.example.com"
    assert data["status"] == "active"

def test_list_routes():
    # Create one first
    client.post("/api/v1/routes", json={
        "domain": "list.example.com",
        "upstream_url": "http://localhost:9001"
    })
    response = client.get("/api/v1/routes")
    assert response.status_code == 200
    assert len(response.json()) > 0

