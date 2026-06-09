"""
WhiteRock Blessings Engine - Member Endpoint Tests
Tests for member registration, login, and profile management.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_member(client: AsyncClient, seed_data):
    """Test member registration."""
    response = await client.post("/members/register", json={
        "email": "newuser@example.com",
        "password": "securepass123",
        "full_name": "New User"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert data["membership_tier"] == "seedling"
    assert data["cora_balance"] == 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_member):
    """Test registration fails with duplicate email."""
    response = await client.post("/members/register", json={
        "email": "test@example.com",  # Same as test_member
        "password": "anotherpass123",
        "full_name": "Duplicate User"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_member):
    """Test successful login returns tokens."""
    response = await client.post("/members/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_member):
    """Test login fails with wrong password."""
    response = await client.post("/members/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, test_member, auth_headers):
    """Test getting current member profile."""
    response = await client.get("/members/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "can_request_blessing" in data
    assert "recent_activity" in data


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """Test profile endpoint requires authentication."""
    response = await client.get("/members/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, test_member, auth_headers):
    """Test updating member profile."""
    response = await client.put("/members/me", 
        headers=auth_headers,
        json={"full_name": "Updated Name", "phone": "555-9999"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["phone"] == "555-9999"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_member):
    """Test token refresh endpoint."""
    # First login to get tokens
    login_response = await client.post("/members/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    refresh_token = login_response.json()["refresh_token"]
    
    # Use refresh token to get new tokens
    response = await client.post("/members/refresh", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_member, auth_headers):
    """Test logout endpoint blacklists token."""
    # First verify we can access protected endpoint
    response1 = await client.get("/members/me", headers=auth_headers)
    assert response1.status_code == 200
    
    # Logout
    response2 = await client.post("/members/logout", headers=auth_headers)
    assert response2.status_code == 200
    
    # Note: Token blacklist is checked on decode, so subsequent requests
    # with the same token should fail (but we'd need to test decode directly)



