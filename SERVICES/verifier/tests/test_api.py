import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

@pytest.mark.asyncio
@patch("app.services.scanner.httpx.AsyncClient.get")
async def test_verify_service(mock_get):
    # Mock responses for health and capabilities
    mock_health = AsyncMock()
    mock_health.status_code = 200
    
    mock_caps = AsyncMock()
    mock_caps.status_code = 200
    mock_caps.json.return_value = {"capabilities": ["test"]}

    # Side effect for consecutive calls
    mock_get.side_effect = [mock_health, mock_caps]
    
    response = client.post("/api/v1/verify/localhost:8000")
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 100
    assert len(data["results"]) == 2

