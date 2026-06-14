"""Pytest fixtures for Orchestrator tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.models import Droplet


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_registry_response():
    """Mock Registry response with droplets."""
    return {
        "droplets": [
            {
                "id": 1,
                "name": "registry",
                "url": "http://localhost:8000",
                "version": "1.0.0",
            },
            {
                "id": 2,
                "name": "orchestrator",
                "url": "http://localhost:8001",
                "version": "1.1.0",
            },
            {
                "id": 3,
                "name": "dashboard",
                "url": "http://localhost:8002",
                "version": "1.0.0",
            },
        ]
    }


@pytest.fixture
def mock_droplets(mock_registry_response):
    """List of Droplet objects."""
    return [Droplet(**d) for d in mock_registry_response["droplets"]]


@pytest.fixture
def mock_task_request():
    """Valid task request payload."""
    return {
        "droplet_name": "registry",
        "method": "GET",
        "path": "/health",
        "payload": None,
        "meta": {"test": "data"},
    }


@pytest.fixture
def mock_successful_response():
    """Mock successful droplet response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    return mock_response


@pytest.fixture
def mock_error_response():
    """Mock error droplet response."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {"error": "Internal error"}
    return mock_response
