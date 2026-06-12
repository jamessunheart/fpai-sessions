"""
Pytest Configuration and Fixtures
Per CODE_STANDARDS.md - testing setup
"""

import pytest
import os
from typing import AsyncGenerator
from httpx import AsyncClient

# Set test environment variables
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["DROPLET_SECRET"] = "test-secret"
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client fixture for testing.
    
    Usage:
        async def test_something(client):
            response = await client.get("/endpoint")
            assert response.status_code == 200
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_chat_request():
    """Sample chat request payload"""
    return {
        "message": "show me all registered items",
        "session_id": "test-session-123",
        "metadata": {"user_id": "test_user"}
    }


@pytest.fixture
def sample_process_request():
    """Sample process request from Voice Droplet"""
    return {
        "trace_id": "test-trace-id-123",
        "source": "18",
        "target": "12",
        "message_type": "command",
        "payload": {
            "message": "I want to register a new service",
            "metadata": {"user_id": "voice_user_1"}
        },
        "timestamp": "2025-11-12T10:00:00Z",
        "route_back": "18"
    }


@pytest.fixture
def sample_udc_message():
    """Sample UDC message"""
    return {
        "trace_id": "test-trace-id-456",
        "source": "1",
        "target": "12",
        "message_type": "query",
        "payload": {"action": "test"},
        "timestamp": "2025-11-12T10:00:00Z"
    }


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear all sessions before each test"""
    from app.services.memory import SESSION_MANAGER
    
    # Clear before test
    session_ids = SESSION_MANAGER.list_sessions()
    for session_id in session_ids:
        SESSION_MANAGER.clear_session(session_id)
    
    yield
    
    # Clear after test
    session_ids = SESSION_MANAGER.list_sessions()
    for session_id in session_ids:
        SESSION_MANAGER.clear_session(session_id)